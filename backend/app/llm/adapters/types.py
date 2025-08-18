"""
Shared types for LLM adapters
Production-grade type definitions with Pydantic
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

class GroundingMode(str, Enum):
    """Grounding mode semantics for web search"""
    REQUIRED = "required"     # Must use provider's web tool; fail closed
    PREFERRED = "preferred"   # Try tool; optional fallback if enabled  
    OFF = "off"              # Ungrounded only

class RunRequest(BaseModel):
    """Request model for LLM runs"""
    run_id: str = Field(..., description="Unique identifier for this run")
    client_id: str = Field(..., description="Client/organization identifier")
    provider: str = Field(..., description="Provider: 'openai' | 'vertex'")
    model_name: str = Field(..., description="Model identifier e.g. 'gpt-4o', 'gemini-2.0-flash'")
    region: Optional[str] = Field(None, description="Vertex only: e.g. 'europe-west4'")
    grounding_mode: GroundingMode = Field(GroundingMode.OFF, description="Web search requirement")
    system_text: str = Field("", description="System prompt/instructions")
    als_block: str = Field("", description="Ambient Location Signals block (≤350 chars)")
    user_prompt: str = Field(..., description="User's actual prompt (naked/unmodified)")
    temperature: float = Field(0.0, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema for structured outputs")
    allow_equiv_fallback: bool = Field(False, description="Allow fallback if grounding_mode==PREFERRED")
    timeout_seconds: int = Field(90, description="Request timeout in seconds")

class RunResult(BaseModel):
    """Result model for LLM runs"""
    run_id: str = Field(..., description="Unique identifier matching request")
    provider: str = Field(..., description="Provider that handled the request")
    model_name: str = Field(..., description="Actual model used")
    region: Optional[str] = Field(None, description="Region for Vertex requests")
    grounded_effective: bool = Field(..., description="Whether grounding actually occurred")
    tool_call_count: int = Field(0, description="Number of web search tool calls made")
    citations: List[Dict[str, Any]] = Field(default_factory=list, description="Web search citations")
    json_text: str = Field(..., description="Raw JSON response text")
    json_obj: Optional[Dict[str, Any]] = Field(None, description="Parsed JSON object")
    json_valid: bool = Field(..., description="Whether JSON parsing succeeded")
    latency_ms: int = Field(..., description="Response time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if failed")
    system_fingerprint: Optional[str] = Field(None, description="Model version fingerprint")
    usage: Dict[str, int] = Field(default_factory=dict, description="Token usage statistics")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator("citations", mode="before")
    @classmethod
    def _coerce_citations(cls, v):
        """Defensive validator: coerce list[str] → list[{"uri": ...}] to prevent production breakage"""
        if not v: 
            return []
        out = []
        for x in (v if isinstance(v, list) else [v]):
            if isinstance(x, dict): 
                out.append(x)
            elif isinstance(x, str): 
                out.append({"uri": x, "title": "No title", "source": "web_search"})
            else: 
                out.append({"note": str(x)})
        return out

class LocaleProbeSchema(BaseModel):
    """Standard schema for locale probe responses"""
    vat_percent: str = Field(..., description="VAT/GST rate as percentage string")
    plug: List[str] = Field(..., description="Electrical plug type letters")
    emergency: List[str] = Field(..., description="Emergency phone numbers")

# Standard JSON schema for locale probes
LOCALE_PROBE_SCHEMA = {
    "type": "object",
    "properties": {
        "vat_percent": {"type": "string", "description": "VAT/GST rate with % symbol"},
        "plug": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Electrical plug type letters (e.g., 'G', 'F')"
        },
        "emergency": {
            "type": "array", 
            "items": {"type": "string"},
            "description": "Emergency phone numbers"
        }
    },
    "required": ["vat_percent", "plug", "emergency"],
    "additionalProperties": False
}