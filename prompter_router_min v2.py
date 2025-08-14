
# prompter_router_min.py
# Minimal FastAPI router for Prompt Templates (dedup + provider-versioned runs)
# Pre-wired to the V7 spec: flattened paths, SQLite-safe JSON, and version service.
from __future__ import annotations

import os, json, inspect, datetime as dt
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

import hashlib

# ---- Local fake LLM for dev: emits response_metadata ----
def _hash8(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:8]

def _fake_llm_response(provider: str, model_id: str, prompt: str) -> dict:
    provider = (provider or '').lower()
    meta = {}
    if provider == 'openai':
        meta['system_fingerprint'] = f"fp_stub_{_hash8('openai:' + model_id)}"
    elif provider == 'google':  # Gemini
        meta['modelVersion'] = f"{model_id}-stub-001"
    elif provider == 'anthropic':
        meta['model'] = model_id
    elif provider == 'azure-openai':
        # Often missing fp in real life; leave metadata empty to exercise fallback
        meta = {}
    # Minimal echo content
    return {
        'content': f"[FAKE {provider or 'unknown'}::{model_id}] " + prompt[:240],
        'response_metadata': meta,
        'usage': {'prompt_tokens': len(prompt)//4, 'completion_tokens': 32, 'total_tokens': len(prompt)//4 + 32},
    }
# ---- Metrics (Prometheus) ----
from prompter_metrics import (
    setup_metrics,
    record_result_insert,
    record_db_unique,
    ensure_version_timer,
    set_redis_up,
)

# ---- Utilities from V7 (import from your codebase) ----
from utils_prompting import (
    calc_config_hash, is_sqlite, infer_provider, extract_fingerprint, as_dict_maybe
)

# ---- ORM models (import from your codebase) ----
# Expect these SQLAlchemy models: Base, PromptTemplate, PromptVersion, PromptResult
from prompter.models import Base, PromptTemplate, PromptVersion, PromptResult

# ---- Version service (no route->route calls) ----
from services.prompt_versions import ensure_version_service

# Optional: idempotency redis (returns Redis or None). It's okay if not present.
try:
    from services.redis_util import get_redis  # type: ignore
except Exception:  # pragma: no cover
    def get_redis(): return None  # type: ignore

# ================= DB wiring =================
DB_URL = os.getenv("DB_URL", "sqlite:///./dev.db")
engine = create_engine(DB_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dev convenience: create tables if not using Alembic (safe on SQLite; no-op on PG if already present)
def _maybe_create_all():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass

# JSON helper (SQLite stores JSON as TEXT)
def jval(db: Session, obj: Any) -> Any:
    return json.dumps(obj) if is_sqlite(db) else obj

# ================= API models =================
class CreateTemplateRequest(BaseModel):
    org_id: Optional[str] = None
    workspace_id: str
    name: str
    provider: Optional[str] = None      # optional; not part of hash
    system_instructions: Optional[str] = None
    user_prompt_template: str
    country_set: List[str] = Field(default_factory=list)
    model_id: str
    inference_params: Any = Field(default_factory=dict)  # dict or Pydantic model
    tools_spec: List[Dict[str, Any]] = Field(default_factory=list)
    response_format: Optional[Dict[str, Any]] = None
    grounding_profile_id: Optional[str] = None
    grounding_snapshot_id: Optional[str] = None
    retrieval_params: Optional[Dict[str, Any]] = None
    created_by: Optional[str] = None

class TemplateOut(BaseModel):
    id: str
    org_id: Optional[str] = None
    workspace_id: str
    name: str
    provider: Optional[str] = None
    model_id: str
    config_hash: str

class CheckDuplicateOut(BaseModel):
    exact_match: bool
    template_id: Optional[str] = None

class EnsureVersionIn(BaseModel):
    org_id: Optional[str] = None
    workspace_id: str
    provider: Optional[str] = None             # openai|google|anthropic|azure-openai
    model_id: Optional[str] = None              # default to template.model_id
    system_instructions: Optional[str] = None
    inference_params: Dict[str, Any] = Field(default_factory=dict)

class EnsureVersionOut(BaseModel):
    version_id: str
    provider: str
    provider_version_key: str
    captured_at: dt.datetime

class RunTemplateRequest(BaseModel):
    rendered_prompt: str
    brand_name: Optional[str] = None
    country: Optional[str] = None
    analysis_scope: Optional[str] = "brand"
    runtime_vars: Dict[str, Any] = Field(default_factory=dict)
    use_grounding: bool = False

class RunTemplateOut(BaseModel):
    result_id: str
    version_id: str
    provider_version_key: str
    system_fingerprint: Optional[str] = None
    created_at: dt.datetime

# ================= FastAPI app/router =================
app = FastAPI(title="Prompter API (minimal)")
setup_metrics(app)
router = APIRouter(prefix="/api/prompt-templates", tags=["prompter"])

@router.post("", response_model=TemplateOut, status_code=201)
def create_template(req: CreateTemplateRequest, db: Session = Depends(get_db)):
    # Accept dict or Pydantic for inference params
    params_raw = req.inference_params or {}
    if hasattr(params_raw, "dict"):
        params_raw = params_raw.dict()

    # Compute canonical hash (aliases NOT included)
    config_hash, canonical = calc_config_hash(
        system_instructions=req.system_instructions,
        user_prompt_template=req.user_prompt_template,
        country_set=req.country_set,
        model_id=req.model_id,
        inference_params=params_raw,
        tools_spec=req.tools_spec,
        response_format=req.response_format,
        grounding_profile_id=req.grounding_profile_id,
        grounding_snapshot_id=req.grounding_snapshot_id,
        retrieval_params=req.retrieval_params,
    )

    row = PromptTemplate(
        org_id=req.org_id,
        workspace_id=req.workspace_id,
        name=req.name,
        provider=req.provider,
        system_instructions=req.system_instructions,
        user_prompt_template=req.user_prompt_template,
        country_set=jval(db, req.country_set),
        model_id=req.model_id,
        inference_params=jval(db, params_raw),
        tools_spec=jval(db, req.tools_spec),
        response_format=jval(db, req.response_format or {}),
        grounding_profile_id=req.grounding_profile_id,
        grounding_snapshot_id=req.grounding_snapshot_id,
        retrieval_params=jval(db, req.retrieval_params or {}),
        config_hash=config_hash,
        config_canonical_json=jval(db, canonical),
        created_by=req.created_by,
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        # metrics: unique-violation on templates
        try:
            record_db_unique("prompt_templates")
        except Exception:
            pass
        # active-only duplicate check
        existing = db.execute(
            select(PromptTemplate).where(
                PromptTemplate.org_id == req.org_id,
                PromptTemplate.workspace_id == req.workspace_id,
                PromptTemplate.config_hash == config_hash,
                PromptTemplate.deleted_at.is_(None),
            )
        ).scalars().first()
        raise HTTPException(
            status_code=409,
            detail={
                "code": "TEMPLATE_EXISTS",
                "template_id": existing.id if existing else None,
                "message": "An identical prompt configuration already exists for this brand."
            },
        )
    return TemplateOut(
        id=row.id, org_id=row.org_id, workspace_id=row.workspace_id, name=row.name,
        provider=row.provider, model_id=row.model_id, config_hash=row.config_hash
    )

@router.post("/check-duplicate", response_model=CheckDuplicateOut)
def check_duplicate(req: CreateTemplateRequest, db: Session = Depends(get_db)):
    params_raw = req.inference_params or {}
    if hasattr(params_raw, "dict"):
        params_raw = params_raw.dict()

    config_hash, _ = calc_config_hash(
        system_instructions=req.system_instructions,
        user_prompt_template=req.user_prompt_template,
        country_set=req.country_set,
        model_id=req.model_id,
        inference_params=params_raw,
        tools_spec=req.tools_spec,
        response_format=req.response_format,
        grounding_profile_id=req.grounding_profile_id,
        grounding_snapshot_id=req.grounding_snapshot_id,
        retrieval_params=req.retrieval_params,
    )
    existing = db.execute(
        select(PromptTemplate).where(
            PromptTemplate.org_id == req.org_id,
            PromptTemplate.workspace_id == req.workspace_id,
            PromptTemplate.config_hash == config_hash,
            PromptTemplate.deleted_at.is_(None),
        )
    ).scalars().first()
    return CheckDuplicateOut(exact_match=bool(existing), template_id=(existing.id if existing else None))

@router.post("/{template_id}/ensure-version", response_model=EnsureVersionOut)
def ensure_version(template_id: str, body: EnsureVersionIn, db: Session = Depends(get_db)):
    tpl = db.get(PromptTemplate, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    canonical = as_dict_maybe(tpl.config_canonical_json)
    provider = body.provider or tpl.provider or infer_provider(tpl.model_id)
    model_id = body.model_id or tpl.model_id
    redis = get_redis()

    from contextlib import ExitStack
with ensure_version_timer(provider):
    info = ensure_version_service(
        db,
        org_id=tpl.org_id, workspace_id=tpl.workspace_id, template_id=tpl.id,
        provider=provider, model_id=model_id,
        system_instructions=body.system_instructions or canonical.get("system_instructions"),
        inference_params=body.inference_params or canonical.get("inference_params", {}),
        redis=redis,
    )
    return EnsureVersionOut(
        version_id=info["version_id"],
        provider=provider,
        provider_version_key=info["provider_version_key"],
        captured_at=info["captured_at"],
    )

@router.post("/{template_id}/run", response_model=RunTemplateOut)
def run_template(template_id: str, req: RunTemplateRequest, db: Session = Depends(get_db)):
    """Minimal example run. Replace the 'response' stub with your LLM adapter call."""
    tpl = db.get(PromptTemplate, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    canonical = as_dict_maybe(tpl.config_canonical_json)
    provider = tpl.provider or infer_provider(tpl.model_id)

    # Fake in-process LLM for dev: echoes and includes response_metadata
    response = _fake_llm_response(provider, tpl.model_id, req.rendered_prompt)

    system_fingerprint, pvk_from_resp = extract_fingerprint(
        response, provider=provider, model_id=tpl.model_id
    )

    redis = get_redis()
    ver = ensure_version_service(
        db,
        org_id=tpl.org_id, workspace_id=tpl.workspace_id, template_id=tpl.id,
        provider=provider, model_id=tpl.model_id,
        system_instructions=canonical.get("system_instructions"),
        inference_params=canonical.get("inference_params", {}),
        redis=redis,
    )
    provider_version_key = ver["provider_version_key"]  # prefer canonical key from service

    full_request = {
        "model": tpl.model_id,
        "params": canonical.get("inference_params", {}),
        "messages": [
            {"role": "system", "content": canonical.get("system_instructions")},
            {"role": "user", "content": req.rendered_prompt},
        ],
        "countries": canonical.get("country_set", []),
    }
    full_response = response

    result = PromptResult(
        org_id=tpl.org_id,
        workspace_id=tpl.workspace_id,
        template_id=tpl.id,
        version_id=ver["version_id"],
        provider_version_key=provider_version_key,
        system_fingerprint=system_fingerprint,
        request=jval(db, full_request),
        response=jval(db, full_response),
        analysis_config=jval(db, {"analysis_scope": req.analysis_scope}),
        created_at=dt.datetime.utcnow(),
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    # metrics: result insert + fingerprint presence
    try:
        record_result_insert(bool(system_fingerprint))
    except Exception:
        pass

    created = result.created_at
    if hasattr(created, "isoformat"):
        created = dt.datetime.fromisoformat(created.isoformat())

    return RunTemplateOut(
        result_id=result.id,
        version_id=ver["version_id"],
        provider_version_key=provider_version_key,
        system_fingerprint=system_fingerprint,
        created_at=created,
    )

@router.get("/health")
def health():
    return {"status": "ok", "db": engine.url.get_backend_name()}


@app.on_event("startup")
def _metrics_redis_health_check():
    try:
        r = get_redis()
        ok = bool(r and (r.ping() if hasattr(r, 'ping') else True))
    except Exception:
        ok = False
    try:
        set_redis_up(ok)
    except Exception:
        pass

app.include_router(router)

if os.getenv("CREATE_ALL_ON_STARTUP", "true").lower() == "true":
    _maybe_create_all()
