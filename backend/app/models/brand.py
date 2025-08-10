from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Brand(Base):
    __tablename__ = "brands"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    domain = Column(String)
    wikidata_qid = Column(String)
    aliases = Column(JSON, default=list)  # Using JSON for SQLite compatibility
    category = Column(JSON, default=list)  # Using JSON for SQLite compatibility
    use_canonical_entities = Column(Boolean, default=True)  # Group variations
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tracked_phrases = relationship("TrackedPhrase", back_populates="brand", cascade="all, delete-orphan")