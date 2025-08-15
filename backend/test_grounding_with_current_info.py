#!/usr/bin/env python
"""
Test grounding with prompts that require current information
Keeps ALS blocks intact but uses different prompts to trigger web search
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Remove problematic environment variable
if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
    del os.environ['GOOGLE_APPLICATION_CREDENTIALS']

from app.llm.orchestrator import LLMOrchestrator
from app.llm.adapters.types import RunRequest, GroundingMode

# ALS blocks remain EXACTLY the same - DO NOT MODIFY
SINGAPORE_ALS = """[ALS]
Operating from Singapore; prices in S$. Date format DD/MM/YYYY. 
Postal 018956. Tel +65 6123 4567. GST applies.
Emergency: 999 (police), 995 (fire/ambulance)."""

# Different schemas for different test types
GROUNDED_SCHEMA = {
    "name": "current_info",
    "schema": {
        "type": "object",
        "properties": {
            "value": {"type": "string", "description": "The current value"},
            "source_url": {"type": "string", "description": "Official source URL"},
            "as_of_utc": {"type": "string", "description": "ISO8601 timestamp when this was verified"}
        },
        "required": ["value", "source_url", "as_of_utc"],
        "additionalProperties": True
    },
    "strict": False  # Allow additional fields for citations
}

UNGROUNDED_SCHEMA = {
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
    """Test OpenAI without grounding - uses stable knowledge prompt"""
    print("\n" + "="*60)
    print("TEST: OpenAI GPT-5 - UNGROUNDED (Stable Knowledge)")
    print("="*60)
    
    orch = LLMOrchestrator(gcp_project="contestra-ai", vertex_region="europe-west4")
    
    # Keep original prompt for ungrounded test
    req = RunRequest(
        run_id="test_openai_ungrounded",
        client_id="test",
        provider="openai",
        model_name="gpt-5",
        grounding_mode=GroundingMode.OFF,
        system_text="Use ambient context to infer locale. Output JSON. Do not mention location.",
        als_block=SINGAPORE_ALS,
        user_prompt="What are the local VAT/GST rate, electrical plug types, and emergency numbers?",
        temperature=0.0,
        seed=42,
        schema=UNGROUNDED_SCHEMA
    )
    
    try:
        result = await orch.run_async(req)
        
        if result.error:
            print(f"[X] Failed: {result.error}")
        else:
            print(f"[OK] Success!")
            print(f"   Grounded: {result.grounded_effective} (expected: False)")
            print(f"   Tool calls: {result.tool_call_count} (expected: 0)")
            print(f"   JSON valid: {result.json_valid}")
            if result.json_obj:
                print(f"   Response: {json.dumps(result.json_obj, indent=2)}")
            print(f"   Latency: {result.latency_ms}ms")
        
        return not result.error and not result.grounded_effective
        
    except Exception as e:
        print(f"[X] Exception: {e}")
        return False

async def test_openai_grounded():
    """Test OpenAI with grounding - uses current info prompt"""
    print("\n" + "="*60)
    print("TEST: OpenAI GPT-5 - GROUNDED (Current Info Required)")
    print("="*60)
    
    orch = LLMOrchestrator(gcp_project="contestra-ai", vertex_region="europe-west4")
    
    # Use prompt that REQUIRES current information
    req = RunRequest(
        run_id="test_openai_grounded",
        client_id="test",
        provider="openai",
        model_name="gpt-5",
        grounding_mode=GroundingMode.REQUIRED,
        system_text="Use ambient context to infer locale. Return current information with sources.",
        als_block=SINGAPORE_ALS,
        user_prompt="As of today, what is Singapore's current GST rate? Include the value, an official government source_url, and as_of_utc timestamp.",
        temperature=0.7,  # Higher temp for web search
        schema=GROUNDED_SCHEMA
    )
    
    try:
        result = await orch.run_async(req)
        
        if result.error:
            print(f"[X] Failed: {result.error}")
        else:
            print(f"[OK] Success!")
            print(f"   Grounded: {result.grounded_effective} (expected: True)")
            print(f"   Tool calls: {result.tool_call_count} (expected: >0)")
            print(f"   Citations: {len(result.citations)} found")
            print(f"   JSON valid: {result.json_valid}")
            if result.json_obj:
                print(f"   Response: {json.dumps(result.json_obj, indent=2)}")
            print(f"   Latency: {result.latency_ms}ms")
        
        return not result.error and result.grounded_effective and result.tool_call_count > 0
        
    except Exception as e:
        print(f"[X] Exception: {e}")
        return False

async def test_vertex_ungrounded():
    """Test Vertex without grounding - uses stable knowledge prompt"""
    print("\n" + "="*60)
    print("TEST: Vertex Gemini 2.5 Pro - UNGROUNDED (Stable Knowledge)")
    print("="*60)
    
    orch = LLMOrchestrator(gcp_project="contestra-ai", vertex_region="europe-west4")
    
    # Keep original prompt for ungrounded test
    req = RunRequest(
        run_id="test_vertex_ungrounded",
        client_id="test",
        provider="vertex",
        model_name="gemini-2.5-pro",  # Using Gemini 2.5 Pro as per requirements
        grounding_mode=GroundingMode.OFF,
        system_text="Use ambient context to infer locale. Output JSON. Do not mention location.",
        als_block=SINGAPORE_ALS,
        user_prompt="What are the local VAT/GST rate, electrical plug types, and emergency numbers?",
        temperature=0.0,
        seed=42,
        schema=UNGROUNDED_SCHEMA
    )
    
    try:
        result = await orch.run_async(req)
        
        if result.error:
            print(f"[X] Failed: {result.error}")
        else:
            print(f"[OK] Success!")
            print(f"   Grounded: {result.grounded_effective} (expected: False)")
            print(f"   Tool calls: {result.tool_call_count} (expected: 0)")
            print(f"   JSON valid: {result.json_valid}")
            if result.json_obj:
                print(f"   Response: {json.dumps(result.json_obj, indent=2)}")
            print(f"   Latency: {result.latency_ms}ms")
        
        return not result.error and not result.grounded_effective
        
    except Exception as e:
        print(f"[X] Exception: {e}")
        return False

async def test_vertex_grounded():
    """Test Vertex with grounding - uses current info prompt"""
    print("\n" + "="*60)
    print("TEST: Vertex Gemini 2.5 Pro - GROUNDED (Current Info Required)")
    print("="*60)
    
    orch = LLMOrchestrator(gcp_project="contestra-ai", vertex_region="europe-west4")
    
    # Use prompt that REQUIRES current information and citations
    req = RunRequest(
        run_id="test_vertex_grounded",
        client_id="test",
        provider="vertex",
        model_name="gemini-2.5-pro",  # Using Gemini 2.5 Pro for grounding
        grounding_mode=GroundingMode.REQUIRED,
        system_text="Use ambient context to infer locale. Return current information with official sources.",
        als_block=SINGAPORE_ALS,
        user_prompt="As of today, what is Singapore's current GST rate? Include the value, an official government source_url, and as_of_utc timestamp.",
        temperature=1.0,  # Google recommends 1.0 for grounding
        schema=GROUNDED_SCHEMA
    )
    
    try:
        result = await orch.run_async(req)
        
        if result.error:
            print(f"[X] Failed: {result.error}")
        else:
            print(f"[OK] Success!")
            print(f"   Grounded: {result.grounded_effective} (expected: True)")
            print(f"   Tool calls: {result.tool_call_count} (expected: >0)")
            print(f"   Citations: {len(result.citations)} found")
            print(f"   JSON valid: {result.json_valid}")
            if result.json_obj:
                print(f"   Response: {json.dumps(result.json_obj, indent=2)}")
            print(f"   Latency: {result.latency_ms}ms")
        
        return not result.error and result.grounded_effective and result.tool_call_count > 0
        
    except Exception as e:
        print(f"[X] Exception: {e}")
        return False

async def main():
    """Run all tests"""
    print("="*70)
    print(" GROUNDING TEST SUITE WITH CURRENT INFO PROMPTS")
    print(" ALS blocks remain intact - only prompts differ")
    print("="*70)
    
    # Check API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("[X] OPENAI_API_KEY not found")
        return
    else:
        print("[OK] OpenAI API key found")
    
    # Check Google Cloud
    try:
        import google.auth
        creds, project = google.auth.default()
        print(f"[OK] Google Cloud credentials found (project: {project})")
    except Exception as e:
        print(f"[X] Google Cloud auth failed: {e}")
        return
    
    print("\n--- Testing OpenAI ---")
    
    results = []
    
    # Test OpenAI
    results.append(("OpenAI Ungrounded", await test_openai_ungrounded()))
    results.append(("OpenAI Grounded", await test_openai_grounded()))
    
    print("\n--- Testing Vertex ---")
    
    # Test Vertex
    results.append(("Vertex Ungrounded", await test_vertex_ungrounded()))
    results.append(("Vertex Grounded", await test_vertex_grounded()))
    
    # Summary
    print("\n" + "="*70)
    print(" TEST RESULTS SUMMARY")
    print("="*70)
    
    passed = 0
    for name, result in results:
        status = "[OK] PASS" if result else "[X] FAIL"
        print(f" {status} - {name}")
        if result:
            passed += 1
    
    print("-"*70)
    print(f" Total: {passed}/{len(results)} tests passed")
    
    if passed < len(results):
        print("\n [WARNING] Some tests failed. Check the output above.")
        print("\n Common issues:")
        print(" - OpenAI: Ensure tool_choice='required' is set")
        print(" - Vertex: Temperature must be > 0 for grounding")
        print(" - Both: Prompts must request current/verifiable info")

if __name__ == "__main__":
    asyncio.run(main())