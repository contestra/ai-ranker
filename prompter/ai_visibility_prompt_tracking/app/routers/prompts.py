from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, update
from ..deps import get_db, validate_language
from .. import schemas, models
from ..config import settings

router = APIRouter(prefix="/prompts", tags=["prompts"])

def normalize(s: str) -> str:
    return " ".join(s.strip().lower().split())

@router.post("", status_code=201)
def create_prompt(payload: schemas.PromptCreate, db: Session = Depends(get_db)):
    (count,) = db.execute(text("SELECT COUNT(*) FROM prompts WHERE tenant_id = current_setting('app.tenant_id', true)::uuid AND deleted_at IS NULL")).one()
    if count >= 200:
        raise HTTPException(status_code=400, detail="Prompt cap (200) reached")
    lang = validate_language(payload.language)
    p = models.Prompt(brand_id=payload.brand_id, text=payload.text, prompt_text_normalized=normalize(payload.text), category=payload.category, language=lang)
    db.add(p); db.flush()
    return {"id": str(p.id)}

@router.patch("/{prompt_id}")
def update_prompt(prompt_id: str, payload: schemas.PromptUpdate, db: Session = Depends(get_db)):
    fields = {}
    if payload.text: fields["text"] = payload.text; fields["prompt_text_normalized"] = normalize(payload.text)
    if payload.category: fields["category"] = payload.category.value
    if payload.language: fields["language"] = validate_language(payload.language)
    if not fields: return {"ok": True}
    db.execute(update(models.Prompt).where(models.Prompt.id == prompt_id).values(**fields))
    db.commit(); return {"ok": True}

@router.delete("/{prompt_id}")
def soft_delete_prompt(prompt_id: str, db: Session = Depends(get_db)):
    db.execute(update(models.Prompt).where(models.Prompt.id==prompt_id, models.Prompt.deleted_at.is_(None)).values(deleted_at=text("now()")))
    db.commit(); return {"ok": True}

@router.post("/{prompt_id}/countries")
def upsert_countries(prompt_id: str, payload: schemas.CountriesUpsert, db: Session = Depends(get_db)):
    if len(payload.countries) > 6:
        raise HTTPException(status_code=400, detail="Max 6 countries")
    for cc in payload.countries:
        if cc not in settings.ALLOWED_COUNTRIES:
            raise HTTPException(status_code=400, detail=f"Invalid country: {cc}")
        db.execute(text("""
            INSERT INTO prompt_countries (id, tenant_id, prompt_id, country_code)
            VALUES (gen_random_uuid(), current_setting('app.tenant_id', true)::uuid, :pid, :cc)
            ON CONFLICT (tenant_id, prompt_id, country_code) WHERE deleted_at IS NULL DO NOTHING
        """), {"pid": prompt_id, "cc": cc})
    db.commit(); return {"ok": True}

@router.post("/{prompt_id}/models")
def upsert_models(prompt_id: str, payload: schemas.PromptModelsUpsert, db: Session = Depends(get_db)):
    for m in payload.models:
        db.execute(text("""
            INSERT INTO prompt_models (id, tenant_id, prompt_id, model_id, grounding_mode, grounding_policy)
            VALUES (gen_random_uuid(), current_setting('app.tenant_id', true)::uuid, :pid, :mid, :gm, :gp::jsonb)
            ON CONFLICT (tenant_id, prompt_id, model_id) WHERE deleted_at IS NULL
            DO UPDATE SET grounding_mode = EXCLUDED.grounding_mode, grounding_policy = EXCLUDED.grounding_policy, updated_at = now()
        """), {"pid": prompt_id, "mid": str(m.model_id), "gm": m.grounding_mode.value, "gp": m.grounding_policy or {}})
    db.commit(); return {"ok": True}
