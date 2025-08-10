from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import Experiment, Run
from app.core import PromptRunner

router = APIRouter()

class ExperimentCreate(BaseModel):
    title: str
    description: Optional[str] = None

class RunCreate(BaseModel):
    experiment_id: int
    model_vendor: str
    model_name: str
    prompts: List[str]
    repetitions: int = 3
    temperature: float = 0.1
    grounded: bool = False
    seed: Optional[int] = None

class ExperimentResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.post("/", response_model=ExperimentResponse)
def create_experiment(experiment: ExperimentCreate, db: Session = Depends(get_db)):
    db_experiment = Experiment(
        title=experiment.title,
        description=experiment.description
    )
    db.add(db_experiment)
    db.commit()
    db.refresh(db_experiment)
    return db_experiment

@router.get("/", response_model=List[ExperimentResponse])
def list_experiments(db: Session = Depends(get_db)):
    return db.query(Experiment).all()

@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(experiment_id: int, db: Session = Depends(get_db)):
    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment

@router.post("/run")
async def create_run(run_data: RunCreate, db: Session = Depends(get_db)):
    runner = PromptRunner(db)
    run = await runner.run_experiment(
        experiment_id=run_data.experiment_id,
        model_vendor=run_data.model_vendor,
        model_name=run_data.model_name,
        prompts=run_data.prompts,
        repetitions=run_data.repetitions,
        temperature=run_data.temperature,
        grounded=run_data.grounded,
        seed=run_data.seed
    )
    return {"run_id": run.id, "status": "completed"}