#!/usr/bin/env python3
"""
Comprehensive test of all 3 grounding modes for both GPT-5 and Gemini
"""

import asyncio
import json
from app.llm.orchestrator import LLMOrchestrator
from app.llm.adapters.types import RunRequest, GroundingMode
from app.services.als.als_builder import ALSBuilder
import uuid

orchestrator = LLMOrchestrator(
    gcp_project="contestra-ai",
    vertex_region="europe-west4"
)
als_builder = ALSBuilder()

async def test_mode(provider: str, model: str, mode: GroundingMode, country: str = "DE"):
    """Test a single mode"""
    
    # Build ALS block for Germany
    als_block = als_builder.build_als_block(country)
    
    # Build request
    req = RunRequest(
        run_id=str(uuid.uuid4()),
        client_id="test",
        provider=provider,
        model_name=model,
        grounding_mode=mode,
        system_text="Use ambient context to infer locale. Output must match the JSON schema. Do not mention location.",
        als_block=als_block,
        user_prompt="Return JSON with local VAT/GST rate (as percentage with % symbol), electrical plug type letters (array), and emergency phone numbers (array).",
        temperature=0.0,
        seed=42,
        schema={
            "type": "object",
            "properties": {
                "vat_percent": {"type": "string"},
                "plug": {"type": "array", "items": {"type": "string"}},
                "emergency": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["vat_percent", "plug", "emergency"],
            "additionalProperties": False
        }
    )
    
    try:
        result = await orchestrator.run_async(req)
        
        # Check results
        passed_vat = False
        passed_plug = False
        passed_emergency = False
        
        if result.json_valid and result.json_obj:
            # Check VAT (Germany = 19%)
            if result.json_obj.get("vat_percent") == "19%":
                passed_vat = True
            
            # Check plug (Germany = F, C)
            result_plugs = set(result.json_obj.get("plug", []))
            if result_plugs & {"F", "C"}:
                passed_plug = True
            
            # Check emergency (Germany = 112, 110)
            result_emergency = set(result.json_obj.get("emergency", []))
            if result_emergency & {"112", "110"}:
                passed_emergency = True
        
        return {
            "provider": provider,
            "model": model,
            "mode": mode.value,
            "grounded_effective": result.grounded_effective,
            "tool_calls": result.tool_call_count,
            "json_valid": result.json_valid,
            "passed_vat": passed_vat,
            "passed_plug": passed_plug,
            "passed_emergency": passed_emergency,
            "all_passed": passed_vat and passed_plug and passed_emergency,
            "latency_ms": result.latency_ms,
            "error": result.error,
            "json_obj": result.json_obj
        }
    except Exception as e:
        return {
            "provider": provider,
            "model": model,
            "mode": mode.value,
            "error": str(e),
            "all_passed": False
        }

async def run_all_tests():
    """Run all test combinations"""
    
    tests = [
        # GPT-5 tests
        ("openai", "gpt-5", GroundingMode.OFF),
        ("openai", "gpt-5", GroundingMode.PREFERRED),
        ("openai", "gpt-5", GroundingMode.REQUIRED),
        
        # Gemini tests
        ("vertex", "gemini-2.5-pro", GroundingMode.OFF),
        ("vertex", "gemini-2.5-pro", GroundingMode.PREFERRED),
        ("vertex", "gemini-2.5-pro", GroundingMode.REQUIRED),
    ]
    
    print("\n" + "="*80)
    print("COMPREHENSIVE GROUNDING MODE TESTS")
    print("="*80)
    
    results = []
    for provider, model, mode in tests:
        print(f"\nTesting {provider}/{model} in {mode.value} mode...")
        result = await test_mode(provider, model, mode)
        results.append(result)
        
        # Print result
        if result.get("error"):
            print(f"  ERROR: {result['error'][:100]}")
        else:
            status = "PASS" if result["all_passed"] else "PARTIAL"
            print(f"  {status} - Grounded: {result['grounded_effective']}, Tool calls: {result['tool_calls']}")
            print(f"     VAT: {'PASS' if result['passed_vat'] else 'FAIL'}, Plug: {'PASS' if result['passed_plug'] else 'FAIL'}, Emergency: {'PASS' if result['passed_emergency'] else 'FAIL'}")
            if result.get("json_obj"):
                print(f"     Response: {json.dumps(result['json_obj'], indent=8)[:200]}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    for r in results:
        status = "PASS" if r.get("all_passed") else "FAIL"
        grounded = "[SEARCH]" if r.get("grounded_effective") else "[NOSEARCH]"
        print(f"{status} {grounded} {r['provider']}/{r['model']:<20} {r['mode']:<12} Latency: {r.get('latency_ms', 'N/A')}ms")
    
    # Overall
    total_passed = sum(1 for r in results if r.get("all_passed"))
    print(f"\nOverall: {total_passed}/{len(results)} tests passed")

if __name__ == "__main__":
    asyncio.run(run_all_tests())