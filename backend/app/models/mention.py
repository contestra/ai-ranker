from sqlalchemy import Column, Integer, ForeignKey, Float, String
from sqlalchemy.orm import relationship
from app.database import Base

class Mention(Base):
    __tablename__ = "mentions"
    
    id = Column(Integer, primary_key=True, index=True)
    completion_id = Column(Integer, ForeignKey("completions.id"), nullable=False)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    start_idx = Column(Integer)
    rank_pos = Column(Integer)
    sentiment = Column(String)
    confidence = Column(Float)
    
    completion = relationship("Completion", back_populates="mentions")
    entity = relationship("Entity")