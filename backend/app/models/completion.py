from sqlalchemy import Column, Integer, ForeignKey, Text, JSON, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Completion(Base):
    __tablename__ = "completions"
    
    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False)
    raw_json = Column(JSON)
    text = Column(Text, nullable=False)
    tokens = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    prompt = relationship("Prompt", back_populates="completions")
    mentions = relationship("Mention", back_populates="completion")