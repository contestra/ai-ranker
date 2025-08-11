import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse
import redis
from sqlalchemy import text, select
from app.config import settings
from app.constants import RunStatus, GroundingMode
from app.services.proxy import ProxyPool
from app.services.grounding import retrieve_web, build_context
from app.services.prompt_compose import compose_final_prompt
from app.services.model_registry import ModelRegistry
from app.services.adapters.dummy import DummyAdapter
from app.models import Run, Answer, PromptModel
from app.db import SessionLocal

_redis = redis.Redis.from_url(settings.REDIS_URL)

def _make_idempotency_key(**parts) -> str:
    raw = "|".join(f"{k}={parts[k]}" for k in sorted(parts))
    return hashlib.sha256(raw.encode()).hexdigest()

def _hostname(url: str | None) -> str | None:
    if not url:
        return None
    return (urlparse(url).hostname or "").lower()

def execute_run(payload: dict):
    idem = _make_idempotency_key(
        tenant_id=payload["tenant_id"],
        prompt_id=payload["prompt_id"],
        model_id=payload["model_id"],
        country_code=payload["country_code"],
        language=payload["language"],
        grounding_mode=payload["grounding_mode"],
        scheduled_for_ts=str(payload.get("scheduled_for_ts","")),
    )
    if not _redis.setnx(f"run_dedupe:{idem}", "1"):
        return
    _redis.expire(f"run_dedupe:{idem}", 15 * 60)

    db = SessionLocal()
    run = None
    try:
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": payload["tenant_id"]})
        row = db.execute(
            text("""
                SELECT p.text AS prompt_text, p.language AS prompt_language, p.brand_id,
                       b.name AS brand_name, b.website_url AS website_url
                FROM prompts p
                JOIN brands b ON b.id = p.brand_id
                WHERE p.id = :pid
            """), {"pid": payload["prompt_id"]}
        ).mappings().first()
        if not row:
            return

        prompt_text = (row["prompt_text"] or "").strip()
        brand_name = row["brand_name"] or ""
        website_domain = _hostname(row["website_url"])
        language = payload["language"] or (row["prompt_language"] or "en-US")

        run = Run(
            tenant_id=payload["tenant_id"],
            prompt_id=payload["prompt_id"],
            model_id=payload["model_id"],
            country_code=payload["country_code"],
            language=language,
            grounding_mode=payload["grounding_mode"],
            idempotency_key=idem,
            status=RunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            scheduled_for_ts=payload.get("scheduled_for_ts"),
        )
        db.add(run); db.flush()

        gm = GroundingMode(payload["grounding_mode"])
        policy = {}
        pm = db.scalar(
            select(PromptModel.grounding_policy).where(
                PromptModel.prompt_id == payload["prompt_id"],
                PromptModel.model_id == payload["model_id"],
                PromptModel.deleted_at.is_(None),
            )
        )
        if pm: policy = dict(pm)

        proxy = ProxyPool().get(payload["country_code"])

        grounded_context, citations = None, []
        if gm == GroundingMode.WEB:
            docs_web = retrieve_web(
                query=prompt_text,
                country_code=payload["country_code"],
                max_docs=int(policy.get("max_docs", 8)),
                policy=policy,
                proxy_endpoint=proxy.endpoint if proxy else None,
            )
            if docs_web:
                grounded_context, citations = build_context(docs_web, char_budget=int(policy.get("max_chars", 8000)))
            else:
                # if no results, optionally degrade to NONE
                if policy.get("degrade_if_no_sources", True):
                    gm = GroundingMode.NONE

        run.grounding_policy_snapshot = policy

        final_prompt = compose_final_prompt(
            user_query=prompt_text,
            brand_name=brand_name,
            website_domain=website_domain,
            language=language,
            grounding_mode=gm,
            grounded_context=grounded_context,
        )

        registry = ModelRegistry()
        try:
            adapter = registry.get(payload["model_id"])
        except KeyError:
            adapter = DummyAdapter()

        resp = adapter.generate(
            prompt_text=final_prompt,
            language=language,
            geo_country=payload["country_code"],
            grounded_context=grounded_context,
            grounding_mode=gm.value,
            proxy_endpoint=proxy.endpoint if proxy else None,
        )

        text_out = (resp.text or "").strip()
        preview = text_out[:512]
        import hashlib as _hash
        chash = _hash.sha256(text_out.encode()).hexdigest()
        all_citations = citations or (resp.citations or [])

        run.status = RunStatus.SUCCEEDED
        run.finished_at = datetime.now(timezone.utc)
        run.raw_provider_meta = resp.raw_meta or {}
        run.token_usage = resp.token_usage or {}
        run.grounding_mode = gm

        db.add(Answer(
            run_id=run.id,
            answer_text=text_out,
            preview=preview,
            content_hash=chash,
            full_raw=resp.raw_meta or {},
            citations=all_citations,
            grounding_mode=gm,
            citation_count=len(all_citations),
        ))
        db.add(run); db.commit()

    except Exception:
        try:
            if run:
                run.status = RunStatus.FAILED_PROVIDER
                run.finished_at = datetime.now(timezone.utc)
                db.add(run); db.commit()
        except Exception:
            db.rollback()
        raise
    finally:
        db.close()
