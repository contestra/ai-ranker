"""
Bridge module to integrate new production orchestrator with existing langchain_adapter
Provides backward compatibility while migrating to new architecture
"""

import uuid
import asyncio
import json
from typing import Dict, Any, Optional, List
from .orchestrator import LLMOrchestrator
from .adapters.types import RunRequest, RunResult, GroundingMode

# Initialize global orchestrator
_orchestrator = None

def get_orchestrator() -> LLMOrchestrator:
    """Get or create the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = LLMOrchestrator(
            gcp_project="contestra-ai",
            vertex_region="europe-west4"
        )
    return _orchestrator


async def analyze_with_orchestrator(
    prompt: str,
    model_name: str = "gpt-4o",
    vendor: str = "openai",
    use_grounding: bool = False,
    context: Optional[str] = None,
    temperature: float = 0.0,
    seed: Optional[int] = 42,
    als_variant_id: Optional[str] = None,
    enforce_json_schema: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Bridge function to use new orchestrator with existing interface
    
    Args:
        prompt: User prompt
        model_name: Model identifier
        vendor: Provider (openai/google/gemini)
        use_grounding: Whether to use web search
        context: ALS context block
        temperature: Sampling temperature
        seed: Random seed
        als_variant_id: ALS variant identifier
        enforce_json_schema: JSON schema to enforce
        
    Returns:
        Dict with response data matching existing format
    """
    
    # Map vendor to provider
    provider_map = {
        "openai": "openai",
        "google": "vertex",
        "gemini": "vertex",
        "vertex": "vertex"
    }
    provider = provider_map.get(vendor.lower(), vendor.lower())
    
    # Determine grounding mode
    if use_grounding:
        grounding_mode = GroundingMode.REQUIRED
    else:
        grounding_mode = GroundingMode.OFF
    
    # Map model names
    if provider == "vertex":
        # Map to publisher path format if needed
        if not model_name.startswith("publishers/"):
            if "gemini-2.0" in model_name:
                model_name = f"publishers/google/models/{model_name}"
            elif "gemini-1.5" in model_name:
                model_name = f"publishers/google/models/{model_name}"
            elif "gemini-2.5" in model_name:
                # Map to available model
                model_name = "publishers/google/models/gemini-2.0-flash"
    
    # Build system text
    system_text = ""
    if context and enforce_json_schema:
        system_text = (
            "Use ambient context to infer locale. "
            "Output must match the JSON schema. "
            "Do not mention location."
        )
    elif context:
        system_text = (
            "Answer the user's question directly and naturally. "
            "You may use any ambient context provided only to infer locale. "
            "Do not mention or cite the ambient context."
        )
    
    # Create run request
    req = RunRequest(
        run_id=str(uuid.uuid4()),
        client_id="langchain_bridge",
        provider=provider,
        model_name=model_name,
        grounding_mode=grounding_mode,
        system_text=system_text,
        als_block=context or "",
        user_prompt=prompt,
        temperature=temperature,
        seed=seed,
        schema=enforce_json_schema or {}
    )
    
    # Get orchestrator and run
    orch = get_orchestrator()
    
    try:
        # Run request
        result = await orch.run_async(req)
        
        # Format response to match existing interface
        response = {
            "content": result.json_text,
            "vendor": vendor,
            "model": result.model_name,
            "grounded_effective": result.grounded_effective,
            "tool_call_count": result.tool_call_count,
            "json_valid": result.json_valid,
            "system_fingerprint": result.system_fingerprint,
            "usage": result.usage,
            "metadata": {
                **result.meta,
                "als_variant_id": als_variant_id,
                "citations": result.citations
            }
        }
        
        # Add parsed JSON if valid
        if result.json_valid and result.json_obj:
            response["json_obj"] = result.json_obj
        
        return response
        
    except Exception as e:
        # Return error response matching existing format
        return {
            "content": f"Error: {str(e)}",
            "vendor": vendor,
            "model": model_name,
            "grounded_effective": False,
            "tool_call_count": 0,
            "json_valid": False,
            "error": str(e),
            "metadata": {
                "als_variant_id": als_variant_id
            }
        }


def analyze_with_orchestrator_sync(
    prompt: str,
    model_name: str = "gpt-4o",
    vendor: str = "openai",
    use_grounding: bool = False,
    context: Optional[str] = None,
    temperature: float = 0.0,
    seed: Optional[int] = 42,
    als_variant_id: Optional[str] = None,
    enforce_json_schema: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Synchronous wrapper for analyze_with_orchestrator
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            analyze_with_orchestrator(
                prompt=prompt,
                model_name=model_name,
                vendor=vendor,
                use_grounding=use_grounding,
                context=context,
                temperature=temperature,
                seed=seed,
                als_variant_id=als_variant_id,
                enforce_json_schema=enforce_json_schema
            )
        )
    finally:
        loop.close()


async def run_locale_probe(
    country: str,
    model_name: str,
    vendor: str,
    use_grounding: bool,
    als_block: str,
    probe_prompt: str,
    expected_values: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Run a locale probe test using the orchestrator
    
    Args:
        country: Country code
        model_name: Model to use
        vendor: Provider
        use_grounding: Whether to use web search
        als_block: ALS context block
        probe_prompt: Probe question
        expected_values: Expected results
        
    Returns:
        Test results dict
    """
    
    # Define JSON schema for locale probe
    locale_schema = {
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
    
    # Run probe
    result = await analyze_with_orchestrator(
        prompt=probe_prompt,
        model_name=model_name,
        vendor=vendor,
        use_grounding=use_grounding,
        context=als_block,
        temperature=0.0,
        seed=42,
        enforce_json_schema=locale_schema
    )
    
    # Check results
    test_result = {
        "country": country,
        "model": model_name,
        "vendor": vendor,
        "grounded": use_grounding,
        "grounded_effective": result.get("grounded_effective", False),
        "tool_calls": result.get("tool_call_count", 0),
        "json_valid": result.get("json_valid", False),
        "passed": False,
        "details": {}
    }
    
    if result.get("json_valid") and result.get("json_obj"):
        data = result["json_obj"]
        
        # Check VAT
        vat_match = data.get("vat_percent") == expected_values.get("vat_percent")
        test_result["details"]["vat"] = {
            "expected": expected_values.get("vat_percent"),
            "actual": data.get("vat_percent"),
            "match": vat_match
        }
        
        # Check plug
        expected_plugs = set(expected_values.get("plug", []))
        actual_plugs = set(data.get("plug", []))
        plug_match = bool(expected_plugs & actual_plugs)  # At least one match
        test_result["details"]["plug"] = {
            "expected": list(expected_plugs),
            "actual": list(actual_plugs),
            "match": plug_match
        }
        
        # Check emergency
        expected_emergency = set(expected_values.get("emergency", []))
        actual_emergency = set(data.get("emergency", []))
        emergency_match = bool(expected_emergency & actual_emergency)  # At least one match
        test_result["details"]["emergency"] = {
            "expected": list(expected_emergency),
            "actual": list(actual_emergency),
            "match": emergency_match
        }
        
        # Overall pass
        test_result["passed"] = vat_match and plug_match and emergency_match
    
    return test_result