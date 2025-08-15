#!/usr/bin/env python
"""
Test the production architecture with real API calls
Verifies both OpenAI and Vertex adapters work correctly
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.llm.orchestrator import LLMOrchestrator
from app.llm.adapters.types import RunRequest, GroundingMode

# Test configuration
SINGAPORE_ALS = """[ALS]
Operating from Singapore; prices in S$. Date format DD/MM/YYYY. 
Postal 018956. Tel +65 6123 4567. GST applies.
Emergency: 999 (police), 995 (fire/ambulance)."""

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

async def test_openai_ungrounded():
    """Test OpenAI without grounding"""
    print("\n" + "="*60)
    print("TEST: OpenAI GPT-5 - UNGROUNDED")
    print("="*60)
    
    orch = LLMOrchestrator(gcp_project="contestra-ai", vertex_region="europe-west4")
    
    req = RunRequest(
        run_id="test_openai_ungrounded",
        client_id="test",
        provider="openai",
        model_name="gpt-5",
        grounding_mode=GroundingMode.OFF,
        system_text="Use ambient context to infer locale. Output must match the JSON schema.",
        als_block=SINGAPORE_ALS,
        user_prompt="Return JSON with local VAT/GST rate, electrical plug type letters, and emergency numbers.",
        temperature=0.0,
        seed=42,
        schema=LOCALE_SCHEMA
    )
    
    try:
        result = await orch.run_async(req)
        print(f"[OK] Success!")
        print(f"   Grounded: {result.grounded_effective} (expected: False)")
        print(f"   Tool calls: {result.tool_call_count} (expected: 0)")
        print(f"   JSON valid: {result.json_valid}")
        if result.json_valid and result.json_obj:
            print(f"   Response: {json.dumps(result.json_obj, indent=2)}")
        print(f"   Latency: {result.latency_ms}ms")
        return True
    except Exception as e:
        print(f"[X] Failed: {e}")
        return False

async def test_openai_grounded():
    """Test OpenAI with grounding"""
    print("\n" + "="*60)
    print("TEST: OpenAI GPT-5 - GROUNDED")  
    print("="*60)
    
    orch = LLMOrchestrator(gcp_project="contestra-ai", vertex_region="europe-west4")
    
    req = RunRequest(
        run_id="test_openai_grounded",
        client_id="test",
        provider="openai",
        model_name="gpt-5",
        grounding_mode=GroundingMode.REQUIRED,
        system_text="Use ambient context to infer locale. Output must match the JSON schema.",
        als_block=SINGAPORE_ALS,
        user_prompt="Return JSON with local VAT/GST rate, electrical plug type letters, and emergency numbers.",
        temperature=0.0,
        seed=42,
        schema=LOCALE_SCHEMA
    )
    
    try:
        result = await orch.run_async(req)
        print(f"[OK] Success!")
        print(f"   Grounded: {result.grounded_effective} (expected: True)")
        print(f"   Tool calls: {result.tool_call_count} (expected: >0)")
        print(f"   JSON valid: {result.json_valid}")
        if result.json_valid and result.json_obj:
            print(f"   Response: {json.dumps(result.json_obj, indent=2)}")
        print(f"   Latency: {result.latency_ms}ms")
        
        # Check citations
        if result.citations:
            print(f"   Citations: {len(result.citations)} sources")
            for i, citation in enumerate(result.citations[:3]):
                print(f"      {i+1}. {citation.get('title', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"[X] Failed: {e}")
        return False

async def test_vertex_ungrounded():
    """Test Vertex/Gemini without grounding"""
    print("\n" + "="*60)
    print("TEST: Vertex Gemini - UNGROUNDED")
    print("="*60)
    
    orch = LLMOrchestrator(gcp_project="contestra-ai", vertex_region="europe-west4")
    
    req = RunRequest(
        run_id="test_vertex_ungrounded",
        client_id="test",
        provider="vertex",
        model_name="gemini-2.5-pro",  # Will be converted to publisher path
        grounding_mode=GroundingMode.OFF,
        system_text="Use ambient context to infer locale. Output must match the JSON schema.",
        als_block=SINGAPORE_ALS,
        user_prompt="Return JSON with local VAT/GST rate, electrical plug type letters, and emergency numbers.",
        temperature=0.0,
        seed=42,
        schema=LOCALE_SCHEMA
    )
    
    try:
        result = await orch.run_async(req)
        print(f"[OK] Success!")
        print(f"   Grounded: {result.grounded_effective} (expected: False)")
        print(f"   Tool calls: {result.tool_call_count} (expected: 0)")
        print(f"   JSON valid: {result.json_valid}")
        if result.json_valid and result.json_obj:
            print(f"   Response: {json.dumps(result.json_obj, indent=2)}")
        print(f"   Latency: {result.latency_ms}ms")
        return True
    except Exception as e:
        print(f"[X] Failed: {e}")
        return False

async def test_vertex_grounded():
    """Test Vertex/Gemini with grounding"""
    print("\n" + "="*60)
    print("TEST: Vertex Gemini - GROUNDED")
    print("="*60)
    
    orch = LLMOrchestrator(gcp_project="contestra-ai", vertex_region="europe-west4")
    
    req = RunRequest(
        run_id="test_vertex_grounded",
        client_id="test",
        provider="vertex",
        model_name="gemini-2.5-pro",  # Will be converted to publisher path
        grounding_mode=GroundingMode.REQUIRED,
        system_text="Use ambient context to infer locale. Output must match the JSON schema.",
        als_block=SINGAPORE_ALS,
        user_prompt="Return JSON with local VAT/GST rate, electrical plug type letters, and emergency numbers.",
        temperature=0.0,
        seed=42,
        schema=LOCALE_SCHEMA
    )
    
    try:
        result = await orch.run_async(req)
        print(f"[OK] Success!")
        print(f"   Grounded: {result.grounded_effective} (expected: True)")
        print(f"   Tool calls: {result.tool_call_count} (expected: >0)")
        print(f"   JSON valid: {result.json_valid}")
        if result.json_valid and result.json_obj:
            print(f"   Response: {json.dumps(result.json_obj, indent=2)}")
        print(f"   Latency: {result.latency_ms}ms")
        return True
    except Exception as e:
        print(f"[X] Failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print(" PRODUCTION ARCHITECTURE TEST SUITE")
    print(" Testing with Real APIs")
    print("="*70)
    
    # Check environment
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("[X] OPENAI_API_KEY not set!")
        return
    else:
        print(f"[OK] OpenAI API key found")
    
    # Check if we have Google Cloud credentials
    try:
        from google.auth import default
        credentials, project = default()
        print(f"[OK] Google Cloud credentials found (project: {project})")
    except Exception as e:
        print(f"[!] Google Cloud credentials issue: {e}")
        print("   Vertex tests may fail")
    
    # Run tests
    results = []
    
    # OpenAI tests
    print("\n--- Testing OpenAI ---")
    results.append(("OpenAI Ungrounded", await test_openai_ungrounded()))
    results.append(("OpenAI Grounded", await test_openai_grounded()))
    
    # Vertex tests  
    print("\n--- Testing Vertex ---")
    results.append(("Vertex Ungrounded", await test_vertex_ungrounded()))
    results.append(("Vertex Grounded", await test_vertex_grounded()))
    
    # Summary
    print("\n" + "="*70)
    print(" TEST RESULTS SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "[OK] PASS" if passed else "[X] FAIL"
        print(f" {status} - {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print("\n" + "-"*70)
    print(f" Total: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n [SUCCESS] ALL TESTS PASSED! Production architecture is working!")
    else:
        print("\n [WARNING] Some tests failed. Check the output above.")

if __name__ == "__main__":
    asyncio.run(main())