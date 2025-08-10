from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float, Date, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class TrackedPhrase(Base):
    __tablename__ = "tracked_phrases"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    phrase = Column(String, nullable=False, index=True)
    category = Column(String)  # e.g., "product", "benefit", "technology"
    priority = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    brand = relationship("Brand", back_populates="tracked_phrases")
    weekly_metrics = relationship("WeeklyMetric", back_populates="tracked_phrase")
    phrase_results = relationship("PhraseResult", back_populates="tracked_phrase")

class WeeklyMetric(Base):
    __tablename__ = "weekly_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    tracked_phrase_id = Column(Integer, ForeignKey("tracked_phrases.id"))
    entity_id = Column(Integer, ForeignKey("entities.id"))
    competitor_brand_id = Column(Integer, ForeignKey("brands.id"))
    week_starting = Column(Date, nullable=False, index=True)
    
    # E→B metrics (when tracking phrases to find brands)
    rank_position = Column(Integer)  # Position when brand appears for phrase
    frequency = Column(Integer)  # Times appeared this week
    variance = Column(Integer)  # Variance in results
    
    # B→E metrics (when tracking brand to find entities)
    entity_frequency = Column(Integer)
    entity_rank = Column(Float)
    
    # Calculated metrics
    weighted_score = Column(Float)
    mention_rate = Column(Float)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    brand = relationship("Brand", foreign_keys=[brand_id])
    tracked_phrase = relationship("TrackedPhrase", back_populates="weekly_metrics")
    entity = relationship("Entity")
    competitor_brand = relationship("Brand", foreign_keys=[competitor_brand_id])

class PhraseResult(Base):
    __tablename__ = "phrase_results"
    
    id = Column(Integer, primary_key=True, index=True)
    tracked_phrase_id = Column(Integer, ForeignKey("tracked_phrases.id"), nullable=False)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    prompt_template = Column(Text)  # The prompt template used
    model_vendor = Column(String)  # openai, google, anthropic
    
    # Results
    response_text = Column(Text)
    brands_found = Column(JSON)  # List of brands found (JSON for SQLite compatibility)
    target_brand_position = Column(Integer)  # Position of our brand (if found)
    target_brand_mentioned = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tracked_phrase = relationship("TrackedPhrase", back_populates="phrase_results")
    run = relationship("Run")

class ThresholdResult(Base):
    __tablename__ = "threshold_results"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    base_prompt = Column(Text)
    modifiers = Column(JSON)  # List of modifier words (JSON for SQLite compatibility)
    triggers_mention = Column(Boolean)
    token_position = Column(Integer)  # Position where brand first appears
    confidence_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    brand = relationship("Brand")
    pivot_analyses = relationship("PivotAnalysis", back_populates="threshold")

class PivotAnalysis(Base):
    __tablename__ = "pivot_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    threshold_id = Column(Integer, ForeignKey("threshold_results.id"), nullable=False)
    original_word = Column(String(100))
    replacement_word = Column(String(100))
    maintains_mention = Column(Boolean)
    impact_level = Column(String(20))  # 'critical', 'moderate', 'neutral'
    position_change = Column(Integer)  # Change in position after replacement
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    threshold = relationship("ThresholdResult", back_populates="pivot_analyses")