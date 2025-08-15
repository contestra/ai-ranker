"""
API endpoints for Grounding Test Grid
Uses the new production orchestrator architecture
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid

from app.llm.orchestrator import LLMOrchestrator
from app.llm.adapters.types import RunRequest, GroundingMode

router = APIRouter(prefix="/api/grounding-test", tags=["grounding-test"])

# Initialize orchestrator
orchestrator = LLMOrchestrator(
    gcp_project="contestra-ai",
    vertex_region="europe-west4"
)

class LocaleTestRequest(BaseModel):
    """Request for locale test"""
    provider: str  # 'openai' or 'vertex'
    model: str
    grounded: bool
    country: str
    als_block: str
    expected: Dict[str, Any]

class LocaleTestResponse(BaseModel):
    """Response from locale test"""
    success: bool
    grounded_effective: bool
    tool_call_count: int
    json_valid: bool
    json_obj: Optional[Dict[str, Any]]
    latency_ms: int
    error: Optional[str]
    passed_vat: bool = False
    passed_plug: bool = False
    passed_emergency: bool = False

# Locale probe schema
LOCALE_SCHEMA = {
    "name": "locale_probe",
    "schema": {
        "type": "object",
        "properties": {
            "vat_percent": {"type": "string"},
            "plug": {"type": "array", "items": {"type": "string"}},
            "emergency": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["vat_percent", "plug", "emergency"],
        "additionalProperties": False
    },
    "strict": True
}

@router.post("/run-locale-test", response_model=LocaleTestResponse)
async def run_locale_test(request: LocaleTestRequest):
    """
    Run a single locale test using the production orchestrator
    """
    try:
        # Determine grounding mode
        grounding_mode = GroundingMode.REQUIRED if request.grounded else GroundingMode.OFF
        
        # Build system text
        system_text = (
            "Use ambient context to infer locale. "
            "Output must match the JSON schema. "
            "Do not mention location."
        )
        
        # Build user prompt
        user_prompt = (
            "Return JSON with local VAT/GST rate (as percentage with % symbol), "
            "electrical plug type letters (array), "
            "and emergency phone numbers (array)."
        )
        
        # Create run request
        run_req = RunRequest(
            run_id=str(uuid.uuid4()),
            client_id="grounding_test",
            provider=request.provider,
            model_name=request.model,
            grounding_mode=grounding_mode,
            system_text=system_text,
            als_block=request.als_block,
            user_prompt=user_prompt,
            temperature=0.0,
            seed=42,
            schema=LOCALE_SCHEMA
        )
        
        # Run the request
        result = await orchestrator.run_async(run_req)
        
        # Check results against expected
        passed_vat = False
        passed_plug = False
        passed_emergency = False
        
        if result.json_valid and result.json_obj:
            # Check VAT
            if result.json_obj.get("vat_percent") == request.expected.get("vat_percent"):
                passed_vat = True
            
            # Check plug (at least one match)
            result_plugs = set(result.json_obj.get("plug", []))
            expected_plugs = set(request.expected.get("plug", []))
            if result_plugs & expected_plugs:  # Intersection
                passed_plug = True
            
            # Check emergency (at least one match)
            result_emergency = set(result.json_obj.get("emergency", []))
            expected_emergency = set(request.expected.get("emergency", []))
            if result_emergency & expected_emergency:  # Intersection
                passed_emergency = True
        
        # Overall success
        success = passed_vat and passed_plug and passed_emergency
        
        return LocaleTestResponse(
            success=success,
            grounded_effective=result.grounded_effective,
            tool_call_count=result.tool_call_count,
            json_valid=result.json_valid,
            json_obj=result.json_obj,
            latency_ms=result.latency_ms,
            error=result.error,
            passed_vat=passed_vat,
            passed_plug=passed_plug,
            passed_emergency=passed_emergency
        )
        
    except Exception as e:
        return LocaleTestResponse(
            success=False,
            grounded_effective=False,
            tool_call_count=0,
            json_valid=False,
            json_obj=None,
            latency_ms=0,
            error=str(e)
        )

@router.get("/test-grid-data")
async def get_test_grid_data():
    """
    Get configuration data for the test grid UI
    """
    return {
        "providers": [
            {"id": "openai", "name": "OpenAI", "models": ["gpt-5", "gpt-5-mini", "gpt-5-nano"]},
            {"id": "vertex", "name": "Vertex AI", "models": ["gemini-2.5-pro", "gemini-2.5-flash"]}
        ],
        "countries": [
            {
                "code": "SG",
                "name": "Singapore",
                "expected": {
                    "vat_percent": "9%",
                    "plug": ["G"],
                    "emergency": ["999", "995"]
                },
                "als_block": "[ALS]\nOperating from Singapore; prices in S$. Date format DD/MM/YYYY.\nPostal 018956. Tel +65 6123 4567. GST applies.\nEmergency: 999 (police), 995 (fire/ambulance)."
            },
            {
                "code": "US",
                "name": "United States",
                "expected": {
                    "vat_percent": "0%",
                    "plug": ["A", "B"],
                    "emergency": ["911"]
                },
                "als_block": "[ALS]\nOperating from USA; prices in USD. Date format MM/DD/YYYY.\nZIP 10001. Tel +1 212 555 0100. Sales tax varies by state.\nEmergency: 911."
            },
            {
                "code": "DE",
                "name": "Germany",
                "expected": {
                    "vat_percent": "19%",
                    "plug": ["F", "C"],
                    "emergency": ["112", "110"]
                },
                "als_block": "[ALS]\nBetrieb aus Deutschland; Preise in EUR. Datumsformat TT.MM.JJJJ.\n10115 Berlin. Tel +49 30 12345678. MwSt. 19%.\nNotruf: 112 (Notfall), 110 (Polizei)."
            },
            {
                "code": "CH",
                "name": "Switzerland",
                "expected": {
                    "vat_percent": "8.1%",
                    "plug": ["J", "C"],
                    "emergency": ["112", "117", "118", "144"]
                },
                "als_block": "[ALS]\nBetrieb aus der Schweiz; Preise in CHF. Datumsformat TT.MM.JJJJ.\n8001 Zürich. Tel +41 44 123 4567. MwSt. 8.1%.\nNotruf: 112 (allgemein), 117 (Polizei), 118 (Feuerwehr), 144 (Rettung)."
            }
        ]
    }