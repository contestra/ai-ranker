from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base

class Model(Base):
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True, index=True)
    vendor = Column(String, nullable=False)
    name = Column(String, nullable=False)
    version = Column(String)
    mode = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())