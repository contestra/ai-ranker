from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..deps import get_db
from .. import schemas, models

router = APIRouter(prefix="/brands", tags=["brands"])

@router.post("", status_code=201)
def create_brand(payload: schemas.BrandCreate, db: Session = Depends(get_db)):
    b = models.Brand(name=payload.name, website_url=payload.website_url)
    db.add(b); db.flush()
    return {"id": str(b.id), "name": b.name}

@router.post("/{brand_id}/variations", status_code=201)
def add_variations(brand_id: str, payload: schemas.BrandVariationUpsert, db: Session = Depends(get_db)):
    def norm(s: str) -> str:
        return " ".join(s.strip().lower().split())
    for v in payload.variations:
        db.add(models.BrandVariation(brand_id=brand_id, value_raw=v, value_normalized=norm(v)))
    db.flush()
    return {"ok": True}

@router.post("/{brand_id}/canonicalization/toggle", status_code=200)
def toggle_canonicalization(brand_id: str, payload: schemas.CanonicalToggle, db: Session = Depends(get_db)):
    for vid in payload.variation_ids:
        db.execute(
            text("""
                INSERT INTO brand_canonicalization_map (tenant_id, variation_id, canonical_brand_id, enabled)
                SELECT current_setting('app.tenant_id', true)::uuid, :vid, :bid, :enabled
            """),
            {"vid": str(vid), "bid": str(payload.canonical_brand_id), "enabled": payload.enabled},
        )
    db.commit()
    return {"ok": True}
