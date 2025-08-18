"""
SQLAlchemy models for Prompter V7 - Multi-tenant prompt deduplication
Extends existing prompt_tracking models with workspace support
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, ForeignKey, JSON, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Organization(Base):
    """Organization for multi-tenant support"""
    __tablename__ = "organizations"
    
    id = Column(String, primary_key=True)  # UUID as string
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    workspaces = relationship("Workspace", back_populates="organization")
    prompt_templates_v7 = relationship("PromptTemplateV7", back_populates="organization")
    prompt_versions = relationship("PromptVersion", back_populates="organization")


class Workspace(Base):
    """Workspace (brand) within an organization"""
    __tablename__ = "workspaces"
    
    id = Column(String, primary_key=True)  # UUID as string
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    brand_name = Column(String, nullable=False)  # Links to existing brand system
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="workspaces")
    prompt_templates_v7 = relationship("PromptTemplateV7", back_populates="workspace")
    prompt_versions = relationship("PromptVersion", back_populates="workspace")
    
    # Index for brand lookup
    __table_args__ = (
        Index("ix_workspaces_org_brand", "org_id", "brand_name"),
    )


class PromptTemplateV7(Base):
    """Enhanced prompt template with deduplication support"""
    __tablename__ = "prompt_templates_v7"
    
    id = Column(String, primary_key=True)  # UUID as string
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    
    # Template data
    name = Column(String, nullable=False)
    config = Column(JSON, nullable=False)  # Full template config
    config_hash = Column(String(64), nullable=False)  # SHA256 hash for deduplication
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="prompt_templates_v7")
    workspace = relationship("Workspace", back_populates="prompt_templates_v7")
    runs_v7 = relationship("PromptRunV7", back_populates="template")
    
    # Unique constraint for active templates only (partial index)
    # PostgreSQL supports partial indexes for better performance
    # This will be handled in the migration/schema SQL
    __table_args__ = (
        Index("ix_prompt_templates_v7_org_ws_hash", "org_id", "workspace_id", "config_hash"),
    )


class PromptVersion(Base):
    """Provider version tracking for deduplication"""
    __tablename__ = "prompt_versions"
    
    id = Column(String, primary_key=True)  # UUID as string
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    
    # Provider info
    provider = Column(String, nullable=False)  # 'openai', 'google', 'anthropic'
    model_id = Column(String, nullable=False)  # 'gpt-4o', 'gemini-2.5-pro', etc.
    provider_version_key = Column(String)  # system_fingerprint or modelVersion
    
    # Tracking
    first_seen_at = Column(DateTime(timezone=True), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=False)
    probe_count = Column(Integer, default=1)
    version_metadata = Column(JSON, default=dict)  # Renamed from 'metadata' (reserved in SQLAlchemy)
    
    # Relationships
    organization = relationship("Organization", back_populates="prompt_versions")
    workspace = relationship("Workspace", back_populates="prompt_versions")
    
    # Indexes
    __table_args__ = (
        Index("ix_prompt_versions_provider", "provider", "model_id"),
        Index("ix_prompt_versions_org_ws", "org_id", "workspace_id"),
        UniqueConstraint("org_id", "workspace_id", "provider", "model_id", name="uq_prompt_versions_org_ws_provider_model"),
    )


class PromptRunV7(Base):
    """Enhanced prompt run with V7 features"""
    __tablename__ = "prompt_runs_v7"
    
    id = Column(String, primary_key=True)  # UUID as string
    template_id = Column(String, ForeignKey("prompt_templates_v7.id"))
    
    # Existing fields from PromptRun
    brand_name = Column(String, nullable=False, index=True)
    model_name = Column(String, nullable=False)
    country_code = Column(String)
    grounding_mode = Column(String)
    status = Column(String, default="pending", index=True)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    tokens_used = Column(Integer)
    
    # V7 additions
    provider = Column(String)
    provider_version_key = Column(String)  # Captured at run time
    config_hash = Column(String(64))  # For audit trail
    idempotency_key = Column(String(64), index=True)  # For duplicate prevention
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    template = relationship("PromptTemplateV7", back_populates="runs_v7")
    results = relationship("PromptResultV7", back_populates="run", cascade="all, delete-orphan", uselist=False)


class PromptResultV7(Base):
    """Enhanced prompt result with V7 tracking"""
    __tablename__ = "prompt_results_v7"
    
    id = Column(String, primary_key=True)  # UUID as string
    run_id = Column(String, ForeignKey("prompt_runs_v7.id", ondelete="CASCADE"), index=True)
    
    # Core result fields (from existing PromptResult)
    prompt_text = Column(Text, nullable=False)
    prompt_hash = Column(String(64))
    model_response = Column(Text)
    brand_mentioned = Column(Boolean, default=False)
    mention_count = Column(Integer, default=0)
    mention_positions = Column(JSON, default=list)
    competitors_mentioned = Column(JSON, default=list)
    confidence_score = Column(Float)
    response_metadata = Column(JSON, default=dict)
    
    # Enhanced tracking (from existing + V7)
    system_fingerprint = Column(String)  # OpenAI's system_fingerprint
    model_version = Column(String)  # Actual model version used
    temperature = Column(Float)
    seed = Column(Integer)
    timestamp_utc = Column(DateTime(timezone=True), server_default=func.now())
    response_time_ms = Column(Integer)
    token_count = Column(JSON)
    
    # V7 additions
    provider_version_key = Column(String)  # Normalized version key
    fingerprint_type = Column(String)  # 'openai.system_fingerprint', 'gemini.modelVersion', etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    run = relationship("PromptRunV7", back_populates="results")