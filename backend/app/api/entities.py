from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import Brand, Entity
from app.core import EntityExtractor

router = APIRouter()

class BrandCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    wikidata_qid: Optional[str] = None
    aliases: List[str] = []
    category: List[str] = []

class BrandResponse(BaseModel):
    id: int
    name: str
    domain: Optional[str]
    wikidata_qid: Optional[str]
    aliases: List[str]
    category: List[str]
    
    class Config:
        from_attributes = True

class EntityResponse(BaseModel):
    id: int
    label: str
    type: Optional[str]
    canonical_id: Optional[int]
    
    class Config:
        from_attributes = True

@router.post("/brands", response_model=BrandResponse)
def create_brand(brand: BrandCreate, db: Session = Depends(get_db)):
    db_brand = Brand(**brand.dict())
    db.add(db_brand)
    db.commit()
    db.refresh(db_brand)
    return db_brand

@router.get("/brands", response_model=List[BrandResponse])
def list_brands(db: Session = Depends(get_db)):
    return db.query(Brand).all()

@router.get("/brands/{brand_id}", response_model=BrandResponse)
def get_brand(brand_id: int, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand

@router.post("/extract/{completion_id}")
def extract_entities(completion_id: int, db: Session = Depends(get_db)):
    extractor = EntityExtractor(db)
    extractor.process_completion(completion_id)
    return {"status": "entities extracted"}

@router.get("/", response_model=List[EntityResponse])
def list_entities(db: Session = Depends(get_db)):
    return db.query(Entity).all()