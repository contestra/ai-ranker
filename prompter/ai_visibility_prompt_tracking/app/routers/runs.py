from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..deps import get_db, get_idempotency_key, validate_language
from ..schemas import RunRequest, PromptModelConfig
from ..config import settings
from ..workers.queue import rq_default

router = APIRouter(prefix="/runs", tags=["runs"])

@router.post("/prompts/{prompt_id}")
def run_prompt(prompt_id: str, payload: RunRequest, db: Session = Depends(get_db), idem: str | None = Depends(get_idempotency_key)):
    countries = payload.countries or list(settings.ALLOWED_COUNTRIES)
    if len(countries) > 6:
        raise HTTPException(status_code=400, detail="Max 6 countries")
    language = validate_language(payload.language)
    if payload.models:
        model_cfgs = payload.models
    else:
        res = db.execute(text("""
            SELECT model_id, grounding_mode, grounding_policy
            FROM prompt_models
            WHERE prompt_id = :pid AND deleted_at IS NULL
        """), {"pid": prompt_id})
        model_cfgs = [PromptModelConfig(model_id=r.model_id, grounding_mode=r.grounding_mode, grounding_policy=r.grounding_policy) for r in res]
    jobs = 0
    for cc in countries:
        for mc in model_cfgs:
            gm = (payload.grounding_mode or mc.grounding_mode).value if hasattr(payload.grounding_mode, "value") else (payload.grounding_mode or mc.grounding_mode)
            rq_default.enqueue("app.workers.jobs.execute_run", {
                "tenant_id": db.execute(text("SELECT current_setting('app.tenant_id', true)")).scalar(),
                "prompt_id": prompt_id,
                "model_id": str(mc.model_id),
                "country_code": cc,
                "language": language,
                "grounding_mode": gm,
                "scheduled_for_ts": None,
            })
            jobs += 1
    return {"queued_jobs": jobs}

@router.get("")
def list_runs(db: Session = Depends(get_db), status: str | None = None):
    q = "SELECT id, prompt_id, model_id, country_code, language, grounding_mode, status, started_at, finished_at FROM runs WHERE tenant_id = current_setting('app.tenant_id', true)::uuid"
    if status:
        q += " AND status = :s"
        rows = db.execute(text(q), {"s": status}).mappings().all()
    else:
        rows = db.execute(text(q)).mappings().all()
    return {"items": [dict(r) for r in rows]}

@router.get("/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT r.*, a.answer_text, a.citations, a.grounding_mode as answer_grounding_mode, a.citation_count
        FROM runs r LEFT JOIN answers a ON a.run_id = r.id
        WHERE r.id = :id AND r.tenant_id = current_setting('app.tenant_id', true)::uuid
    """), {"id": run_id}).mappings().first()
    if not row: raise HTTPException(status_code=404, detail="Not found")
    return dict(row)

@router.get("/answers/{run_id}")
def get_answer(run_id: str, db: Session = Depends(get_db)):
    row = db.execute(text("SELECT * FROM answers WHERE run_id = :id"), {"id": run_id}).mappings().first()
    if not row: raise HTTPException(status_code=404, detail="Not found")
    return dict(row)
