
# prompter/models.py
from __future__ import annotations

import uuid
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Index, UniqueConstraint, func, event, DDL
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def gen_uuid() -> str:
    return str(uuid.uuid4())

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(String, primary_key=True, default=gen_uuid)
    org_id = Column(String, nullable=True)
    workspace_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    provider = Column(String, nullable=True)

    system_instructions = Column(Text, nullable=True)
    user_prompt_template = Column(Text, nullable=False)
    country_set = Column(Text, nullable=False)             # JSON string in SQLite
    model_id = Column(String, nullable=False)
    inference_params = Column(Text, nullable=False)        # JSON string in SQLite
    tools_spec = Column(Text, nullable=True)               # JSON string in SQLite
    response_format = Column(Text, nullable=True)          # JSON string in SQLite
    grounding_profile_id = Column(String, nullable=True)
    grounding_snapshot_id = Column(String, nullable=True)
    retrieval_params = Column(Text, nullable=True)         # JSON string in SQLite

    config_hash = Column(String, nullable=False)
    config_canonical_json = Column(Text, nullable=False)   # JSON string in SQLite

    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    versions = relationship("PromptVersion", back_populates="template", lazy="selectin")
    results = relationship("PromptResult", back_populates="template", lazy="selectin")

# Active-only unique partial index for SQLite (and PG if used without Alembic)
event.listen(
    PromptTemplate.__table__,
    "after_create",
    DDL(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_tpl_org_ws_confighash_active "
        "ON prompt_templates (org_id, workspace_id, config_hash) "
        "WHERE deleted_at IS NULL"
    )
)

class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(String, primary_key=True, default=gen_uuid)
    org_id = Column(String, nullable=False)
    workspace_id = Column(String, nullable=False)
    template_id = Column(String, ForeignKey("prompt_templates.id"), nullable=False)

    provider = Column(String, nullable=False)              # openai|google|anthropic|azure-openai
    provider_version_key = Column(String, nullable=False)  # fp_* | gemini-* | model id
    model_id = Column(String, nullable=False)

    fingerprint_captured_at = Column(DateTime(timezone=True), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    template = relationship("PromptTemplate", back_populates="versions", lazy="joined")

    __table_args__ = (
        UniqueConstraint("org_id", "workspace_id", "template_id", "provider_version_key",
                         name="ux_versions_org_ws_tpl_pvk"),
    )

class PromptResult(Base):
    __tablename__ = "prompt_results"

    id = Column(String, primary_key=True, default=gen_uuid)
    org_id = Column(String, nullable=False)
    workspace_id = Column(String, nullable=False)
    template_id = Column(String, ForeignKey("prompt_templates.id"), nullable=False)
    version_id = Column(String, ForeignKey("prompt_versions.id"), nullable=True)

    provider_version_key = Column(String, nullable=True)
    system_fingerprint = Column(String, nullable=True)

    request = Column(Text, nullable=False)                 # JSON string in SQLite
    response = Column(Text, nullable=False)                # JSON string in SQLite
    analysis_config = Column(Text, nullable=True)          # JSON string in SQLite

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    template = relationship("PromptTemplate", back_populates="results", lazy="joined")
    version = relationship("PromptVersion", lazy="joined")

# Useful indexes for queries (create if not exists on create_all)
event.listen(
    PromptResult.__table__,
    "after_create",
    DDL("CREATE INDEX IF NOT EXISTS ix_results_tpl_time ON prompt_results (template_id, created_at DESC)")
)
event.listen(
    PromptResult.__table__,
    "after_create",
    DDL("CREATE INDEX IF NOT EXISTS ix_results_workspace ON prompt_results (workspace_id, created_at DESC)")
)
