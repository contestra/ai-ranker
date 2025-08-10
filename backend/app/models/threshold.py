from sqlalchemy import Column, Integer, ForeignKey, Text, String
from app.database import Base

class Threshold(Base):
    __tablename__ = "thresholds"
    
    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False)
    token_idx_first_mention = Column(Integer)
    preceding_window = Column(Text)
    pattern_hash = Column(String)