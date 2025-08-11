from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
from uuid import UUID
from .constants import PromptCategory, GroundingMode
from .config import settings
from .deps import LANG_RE

# ---- Brand ----
class BrandCreate(BaseModel):
    name: str
    website_url: str

class BrandVariationUpsert(BaseModel):
    variations: List[str]

class CanonicalToggle(BaseModel):
    enabled: bool
    canonical_brand_id: UUID
    variation_ids: List[UUID]

# ---- Prompt ----
class PromptCreate(BaseModel):
    brand_id: UUID
    text: str
    category: PromptCategory = PromptCategory.mofu
    language: str | None = settings.DEFAULT_LANGUAGE

    @field_validator("language")
    @classmethod
    def _lang(cls, v):
        if not v:
            return settings.DEFAULT_LANGUAGE
        return v if LANG_RE.match(v) else settings.DEFAULT_LANGUAGE

class PromptUpdate(BaseModel):
    text: Optional[str] = None
    category: Optional[PromptCategory] = None
    language: Optional[str] = None

class CountriesUpsert(BaseModel):
    countries: List[Literal["US","GB","AE","DE","CH","SG"]]

    @field_validator("countries")
    @classmethod
    def _cap(cls, v):
        if len(v) > 6:
            raise ValueError("Max 6 countries")
        return v

class PromptModelConfig(BaseModel):
    model_id: UUID
    grounding_mode: GroundingMode = GroundingMode.NONE
    grounding_policy: dict = Field(default_factory=dict)

class PromptModelsUpsert(BaseModel):
    models: List[PromptModelConfig]

# ---- Scheduling ----
class ScheduleCreate(BaseModel):
    cadence: Literal["daily","weekly","monthly"]
    timezone: str
    run_at: str  # time-with-tz string

# ---- Runs ----
class RunRequest(BaseModel):
    countries: Optional[List[Literal["US","GB","AE","DE","CH","SG"]]] = None
    models: Optional[List[PromptModelConfig]] = None
    language: Optional[str] = None
    grounding_mode: Optional[GroundingMode] = None
