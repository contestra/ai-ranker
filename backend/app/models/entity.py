from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base

class Entity(Base):
    __tablename__ = "entities"
    
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, nullable=False, index=True)
    canonical_id = Column(Integer, ForeignKey("entities.id"))
    type = Column(String)