from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class Prompt(Base):
    __tablename__ = "prompts"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    type = Column(String)
    template_id = Column(Integer)
    input_text = Column(Text, nullable=False)
    variant_id = Column(Integer)
    
    run = relationship("Run", back_populates="prompts")
    completions = relationship("Completion", back_populates="prompt")