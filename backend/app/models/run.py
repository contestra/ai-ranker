from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Run(Base):
    __tablename__ = "runs"
    
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    locale = Column(String, default="en")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    seed = Column(Integer)
    temperature = Column(Float, default=0.1)
    grounded = Column(Boolean, default=False)
    
    experiment = relationship("Experiment", back_populates="runs")
    model = relationship("Model")
    prompts = relationship("Prompt", back_populates="run")