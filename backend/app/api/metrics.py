from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import Metric
from app.core import Scorer

router = APIRouter()

class MetricResponse(BaseModel):
    id: int
    run_id: int
    brand_id: int
    concept_id: Optional[int]
    mention_rate: float
    avg_rank: Optional[float]
    weighted_score: float
    ci_low: float
    ci_high: float
    
    class Config:
        from_attributes = True

class ScoreRequest(BaseModel):
    run_id: int
    brand_id: int
    concept_id: Optional[int] = None

@router.post("/calculate")
def calculate_metrics(request: ScoreRequest, db: Session = Depends(get_db)):
    scorer = Scorer(db)
    metric = scorer.save_metrics(
        run_id=request.run_id,
        brand_id=request.brand_id,
        concept_id=request.concept_id
    )
    return MetricResponse.from_orm(metric)

@router.get("/run/{run_id}", response_model=List[MetricResponse])
def get_run_metrics(run_id: int, db: Session = Depends(get_db)):
    metrics = db.query(Metric).filter(Metric.run_id == run_id).all()
    return metrics

@router.get("/brand/{brand_id}", response_model=List[MetricResponse])
def get_brand_metrics(brand_id: int, db: Session = Depends(get_db)):
    metrics = db.query(Metric).filter(Metric.brand_id == brand_id).all()
    return metrics

@router.get("/stability/{brand_id}/{run_id}")
def get_stability(brand_id: int, run_id: int, db: Session = Depends(get_db)):
    scorer = Scorer(db)
    stability = scorer.calculate_stability(brand_id, run_id)
    return {"stability": stability}