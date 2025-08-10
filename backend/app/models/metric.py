from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime
from sqlalchemy.sql import func
from app.database import Base

class Metric(Base):
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    concept_id = Column(Integer, ForeignKey("concepts.id"))
    mention_rate = Column(Float)
    avg_rank = Column(Float)
    weighted_score = Column(Float)
    ci_low = Column(Float)
    ci_high = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())