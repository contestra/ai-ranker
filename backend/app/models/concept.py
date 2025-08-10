from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base

class Concept(Base):
    __tablename__ = "concepts"
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    topic = Column(String)
    intent = Column(String)
    locale = Column(String, default="en")
    created_at = Column(DateTime(timezone=True), server_default=func.now())