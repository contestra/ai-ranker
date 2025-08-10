from sqlalchemy import Column, Integer, ForeignKey, String, Float
from app.database import Base

class Pivot(Base):
    __tablename__ = "pivots"
    
    id = Column(Integer, primary_key=True, index=True)
    threshold_id = Column(Integer, ForeignKey("thresholds.id"), nullable=False)
    term = Column(String)
    variant = Column(String)
    delta_prob = Column(Float)
    significance = Column(Float)