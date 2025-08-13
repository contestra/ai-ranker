"""
SQLAlchemy models for Prompt Tracking feature
Works with both SQLite (local) and PostgreSQL (production)
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_name = Column(String, nullable=False, index=True)
    template_name = Column(String, nullable=False)
    prompt_text = Column(Text, nullable=False)
    prompt_hash = Column(String(64), index=True)  # SHA256 hash of prompt_text for integrity checking
    prompt_type = Column(String, default="custom")
    countries = Column(JSON, default=list)  # JSON for SQLite/PostgreSQL compatibility
    grounding_modes = Column(JSON, default=list)  # JSON for SQLite/PostgreSQL compatibility
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    runs = relationship("PromptRun", back_populates="template", cascade="all, delete-orphan")
    schedules = relationship("PromptSchedule", back_populates="template", cascade="all, delete-orphan")

class PromptRun(Base):
    __tablename__ = "prompt_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("prompt_templates.id", ondelete="CASCADE"))
    brand_name = Column(String, nullable=False, index=True)
    model_name = Column(String, nullable=False)
    country_code = Column(String)
    grounding_mode = Column(String)
    status = Column(String, default="pending", index=True)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    tokens_used = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    template = relationship("PromptTemplate", back_populates="runs")
    results = relationship("PromptResult", back_populates="run", cascade="all, delete-orphan", uselist=False)

class PromptResult(Base):
    __tablename__ = "prompt_results"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("prompt_runs.id", ondelete="CASCADE"), index=True)
    prompt_text = Column(Text, nullable=False)
    prompt_hash = Column(String(64))  # SHA256 hash of prompt sent to model (for verification)
    model_response = Column(Text)
    brand_mentioned = Column(Boolean, default=False)
    mention_count = Column(Integer, default=0)
    mention_positions = Column(JSON, default=list)  # JSON array
    competitors_mentioned = Column(JSON, default=list)  # JSON array
    confidence_score = Column(Float)
    response_metadata = Column(JSON, default=dict)  # JSON object
    
    # New fields for better tracking
    system_fingerprint = Column(String)  # OpenAI's system_fingerprint
    model_version = Column(String)  # Actual model version used
    temperature = Column(Float)  # Temperature setting used
    seed = Column(Integer)  # Seed for reproducibility
    timestamp_utc = Column(DateTime(timezone=True), server_default=func.now())  # UTC timestamp
    response_time_ms = Column(Integer)  # Response time in milliseconds
    token_count = Column(JSON)  # {"prompt_tokens": X, "completion_tokens": Y, "total_tokens": Z}
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    run = relationship("PromptRun", back_populates="results")

class PromptSchedule(Base):
    __tablename__ = "prompt_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("prompt_templates.id", ondelete="CASCADE"))
    schedule_type = Column(String)  # 'daily', 'weekly', 'monthly'
    run_time = Column(String)  # Store as string for simplicity
    timezone = Column(String, default="UTC")
    last_run_at = Column(DateTime(timezone=True))
    next_run_at = Column(DateTime(timezone=True), index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    template = relationship("PromptTemplate", back_populates="schedules")