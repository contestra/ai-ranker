from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from .db import Base
from .constants import RunStatus, GroundingMode, PromptCategory

def ts_now():
    return text("now()")

class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=ts_now())
    updated_at: Mapped[datetime] = mapped_column(server_default=ts_now())

class Brand(Base):
    __tablename__ = "brands"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"))
    name: Mapped[str]
    website_url: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=ts_now())
    updated_at: Mapped[datetime] = mapped_column(server_default=ts_now())
    deleted_at: Mapped[datetime | None]

class BrandVariation(Base):
    __tablename__ = "brand_variations"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"))
    brand_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"))
    value_raw: Mapped[str]
    value_normalized: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=ts_now())
    updated_at: Mapped[datetime] = mapped_column(server_default=ts_now())
    deleted_at: Mapped[datetime | None]

class Prompt(Base):
    __tablename__ = "prompts"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"))
    brand_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"))
    text: Mapped[str]
    prompt_text_normalized: Mapped[str]
    category: Mapped[PromptCategory] = mapped_column(Enum(PromptCategory, name="prompt_category"))
    language: Mapped[str] = mapped_column(default="en-US")
    created_at: Mapped[datetime] = mapped_column(server_default=ts_now())
    updated_at: Mapped[datetime] = mapped_column(server_default=ts_now())
    deleted_at: Mapped[datetime | None]

class PromptCountry(Base):
    __tablename__ = "prompt_countries"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"))
    prompt_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prompts.id", ondelete="CASCADE"))
    country_code: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=ts_now())
    updated_at: Mapped[datetime] = mapped_column(server_default=ts_now())
    deleted_at: Mapped[datetime | None]

class Model(Base):
    __tablename__ = "models"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    provider: Mapped[str]
    model_key: Mapped[str]
    capabilities: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=ts_now())
    updated_at: Mapped[datetime] = mapped_column(server_default=ts_now())

class PromptModel(Base):
    __tablename__ = "prompt_models"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"))
    prompt_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prompts.id", ondelete="CASCADE"))
    model_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("models.id", ondelete="RESTRICT"))
    grounding_mode: Mapped[GroundingMode] = mapped_column(Enum(GroundingMode, name="grounding_mode"), default=GroundingMode.NONE)
    grounding_policy: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=ts_now())
    updated_at: Mapped[datetime] = mapped_column(server_default=ts_now())
    deleted_at: Mapped[datetime | None]

class Schedule(Base):
    __tablename__ = "schedules"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"))
    prompt_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prompts.id", ondelete="CASCADE"))
    cadence: Mapped[str]
    timezone: Mapped[str]
    run_at: Mapped[datetime]  # time in DB
    next_run_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=ts_now())
    updated_at: Mapped[datetime] = mapped_column(server_default=ts_now())

class Run(Base):
    __tablename__ = "runs"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"))
    prompt_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prompts.id", ondelete="RESTRICT"))
    model_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("models.id", ondelete="RESTRICT"))
    country_code: Mapped[str]
    language: Mapped[str] = mapped_column(default="en-US")
    grounding_mode: Mapped[GroundingMode] = mapped_column(Enum(GroundingMode, name="grounding_mode"), default=GroundingMode.NONE)
    grounding_policy_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    brand_variation_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("brand_variations.id", ondelete="SET NULL"))
    canonical_brand_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="SET NULL"))
    idempotency_key: Mapped[str]
    location_effective: Mapped[bool] = mapped_column(default=True)
    scheduled_for_ts: Mapped[datetime | None]
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, name="run_status"), default=RunStatus.QUEUED)
    cost_estimate: Mapped[float | None]
    token_usage: Mapped[dict | None] = mapped_column(JSONB)
    raw_provider_meta: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=ts_now())
    updated_at: Mapped[datetime] = mapped_column(server_default=ts_now())

class Answer(Base):
    __tablename__ = "answers"
    run_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT"), primary_key=True)
    answer_text: Mapped[str]
    content_hash: Mapped[str]
    preview: Mapped[str | None]
    full_raw: Mapped[dict | None] = mapped_column(JSONB)
    citations: Mapped[dict | None] = mapped_column(JSONB)
    grounding_mode: Mapped[GroundingMode] = mapped_column(Enum(GroundingMode, name="grounding_mode"), default=GroundingMode.NONE)
    citation_count: Mapped[int] = mapped_column(default=0)
    brand_mentions: Mapped[dict | None] = mapped_column(JSONB)
    competitors: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=ts_now())
    updated_at: Mapped[datetime] = mapped_column(server_default=ts_now())
