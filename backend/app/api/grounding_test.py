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
from app.services.als.als_builder import ALSBuilder

router = APIRouter(tags=["grounding-test"])

# Initialize orchestrator and ALS builder
orchestrator = LLMOrchestrator(
    gcp_project="contestra-ai",
    vertex_region="europe-west4"
)
als_builder = ALSBuilder()

class LocaleTestRequest(BaseModel):
    """Request for locale test with grounding mode"""
    provider: str  # 'openai' or 'vertex'
    model: str
    grounded: bool
    grounding_mode: Optional[str] = "preferred"  # 'preferred' or 'required'
    country: str
    als_block: str
    expected: Dict[str, Any]

class LocaleTestResponse(BaseModel):
    """Response from locale test"""
    success: bool
    grounding_mode: str
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
        # Determine grounding mode based on request
        if not request.grounded:
            grounding_mode = GroundingMode.OFF
        elif request.grounding_mode and request.grounding_mode.lower() == "required":
            grounding_mode = GroundingMode.REQUIRED
        else:
            grounding_mode = GroundingMode.PREFERRED
        
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
        
        # Use proper ALS block from templates if a simple one was provided
        als_block = request.als_block
        if als_block and als_block.startswith("[ALS]\nOperating from"):
            # This is the simple placeholder, replace with proper ALS
            als_block = als_builder.build_als_block(request.country)
        
        # Create run request
        run_req = RunRequest(
            run_id=str(uuid.uuid4()),
            client_id="grounding_test",
            provider=request.provider,
            model_name=request.model,
            grounding_mode=grounding_mode,
            system_text=system_text,
            als_block=als_block,
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
            grounding_mode=grounding_mode.value,
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
        # Try to get grounding_mode from locals or default to "off"
        try:
            mode = grounding_mode.value if 'grounding_mode' in locals() else "off"
        except:
            mode = "off"
            
        return LocaleTestResponse(
            success=False,
            grounding_mode=mode,
            grounded_effective=False,
            tool_call_count=0,
            json_valid=False,
            json_obj=None,
            latency_ms=0,
            error=str(e)
        )

@router.get("/als-block/{country_code}")
async def get_als_block(country_code: str):
    """
    Get the proper ALS block for a specific country
    """
    als_block = als_builder.build_als_block(country_code)
    if not als_block:
        return {"error": f"Country {country_code} not supported"}
    return {
        "country_code": country_code,
        "als_block": als_block
    }

@router.get("/test-grid-data")
async def get_test_grid_data():
    """
    Get configuration data for the test grid UI
    Three modes represent real user behavior:
    - Ungrounded: Pure model recall (baseline)
    - Grounded (Auto): Realistic browsing (model decides)
    - Grounded (Required): Upper bound (forced search)
    """
    return {
        "providers": [
            {"id": "openai", "name": "OpenAI", "models": ["gpt-5", "gpt-5-mini", "gpt-5-nano"]},
            {"id": "vertex", "name": "Vertex AI", "models": ["gemini-2.5-pro", "gemini-2.5-flash"]}
        ],
        "grounding_modes": [
            {"id": "off", "name": "Ungrounded", "description": "Pure model recall - baseline brand memory"},
            {"id": "preferred", "name": "Grounded (Auto)", "description": "Realistic - model decides when to search"},
            {"id": "required", "name": "Grounded (Required)", "description": "Upper bound - forces web search"}
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

@router.post("/calculate-metrics")
async def calculate_metrics(runs: List[LocaleTestResponse]):
    """
    Calculate aggregate metrics from test runs
    Returns visibility rates, grounding effectiveness, and uplift metrics
    """
    if not runs:
        return {"error": "No runs provided"}
    
    # Group by grounding mode
    ungrounded = [r for r in runs if r.grounding_mode == "off"]
    auto = [r for r in runs if r.grounding_mode == "preferred"]
    required = [r for r in runs if r.grounding_mode == "required"]
    
    def calculate_mode_metrics(mode_runs):
        if not mode_runs:
            return {
                "count": 0,
                "success_rate": 0,
                "grounding_effectiveness": 0,
                "avg_tool_calls": 0,
                "avg_latency_ms": 0
            }
        
        return {
            "count": len(mode_runs),
            "success_rate": sum(1 for r in mode_runs if r.success) / len(mode_runs),
            "grounding_effectiveness": sum(1 for r in mode_runs if r.grounded_effective) / len(mode_runs),
            "avg_tool_calls": sum(r.tool_call_count for r in mode_runs) / len(mode_runs),
            "avg_latency_ms": sum(r.latency_ms for r in mode_runs) / len(mode_runs)
        }
    
    metrics = {
        "ungrounded": calculate_mode_metrics(ungrounded),
        "grounded_auto": calculate_mode_metrics(auto),
        "grounded_required": calculate_mode_metrics(required),
        "uplift": {}
    }
    
    # Calculate uplift if we have baseline
    if ungrounded and metrics["ungrounded"]["success_rate"] > 0:
        baseline = metrics["ungrounded"]["success_rate"]
        if auto:
            metrics["uplift"]["auto_vs_baseline"] = metrics["grounded_auto"]["success_rate"] - baseline
        if required:
            metrics["uplift"]["ceiling_vs_baseline"] = metrics["grounded_required"]["success_rate"] - baseline
    
    return metrics