#!/usr/bin/env python
"""
Comprehensive test of Vertex GenAI adapter with grounding
Tests all the fixes from ChatGPT's recommendations
"""

import os
import sys
import asyncio
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Clear any existing Google credentials to force ADC
os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)
os.environ['GOOGLE_CLOUD_PROJECT'] = 'contestra-ai'

from app.llm.adapters.vertex_genai_adapter import VertexGenAIAdapter
from app.llm.adapters.types import RunRequest, GroundingMode

async def test_vertex_adapter():
    """Test the Vertex adapter with various scenarios"""
    
    print("=" * 60)
    print("VERTEX GENAI ADAPTER COMPREHENSIVE TEST")
    print("=" * 60)
    
    # Initialize adapter
    adapter = VertexGenAIAdapter(project="contestra-ai", location="europe-west4")
    print(f"\n✓ Adapter initialized: project={adapter.project}, location={adapter.location}")
    
    # Test 1: Simple prompt without grounding
    print("\n" + "=" * 60)
    print("TEST 1: Simple prompt without grounding")
    print("-" * 60)
    
    req1 = RunRequest(
        run_id="test-001",
        client_id="test",
        provider="vertex",
        model_name="gemini-2.0-flash",
        grounding_mode=GroundingMode.OFF,
        system_text="You are a helpful assistant.",
        user_prompt="Say 'Hello World' and nothing else.",
        temperature=0.0,
        seed=42
    )
    
    try:
        result1 = adapter.run(req1)
        print(f"✓ Response: {result1.json_text}")
        print(f"✓ Grounded: {result1.grounded_effective}")
        print(f"✓ Citations: {len(result1.citations)}")
        assert result1.grounded_effective == False, "Should not be grounded"
        assert len(result1.citations) == 0, "Should have no citations"
        print("✓ TEST 1 PASSED")
    except Exception as e:
        print(f"✗ TEST 1 FAILED: {e}")
    
    # Test 2: Grounding with web search
    print("\n" + "=" * 60)
    print("TEST 2: Grounding with web search")
    print("-" * 60)
    
    req2 = RunRequest(
        run_id="test-002",
        client_id="test",
        provider="vertex",
        model_name="gemini-2.0-flash",
        grounding_mode=GroundingMode.REQUIRED,
        system_text="Answer based on current information.",
        user_prompt="What is the current VAT rate in Germany? Just give the percentage.",
        temperature=0.0,
        seed=42
    )
    
    try:
        result2 = adapter.run(req2)
        print(f"✓ Response: {result2.json_text}")
        print(f"✓ Grounded: {result2.grounded_effective}")
        print(f"✓ Tool calls: {result2.tool_call_count}")
        print(f"✓ Citations: {len(result2.citations)}")
        
        # Check citations are dicts
        if result2.citations:
            print("\nCitation details:")
            for i, cite in enumerate(result2.citations[:3]):  # Show first 3
                print(f"  Citation {i+1}:")
                print(f"    Type: {type(cite).__name__}")
                if isinstance(cite, dict):
                    for key, val in cite.items():
                        print(f"    {key}: {val}")
                else:
                    print(f"    ERROR: Not a dict! Got: {cite}")
        
        assert result2.grounded_effective == True, "Should be grounded"
        assert result2.tool_call_count > 0, "Should have tool calls"
        
        # Verify all citations are dicts
        for i, cite in enumerate(result2.citations):
            assert isinstance(cite, dict), f"Citation {i} is not a dict: {type(cite).__name__}"
        
        print("✓ TEST 2 PASSED")
    except Exception as e:
        print(f"✗ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: JSON schema without grounding (tests the conflict resolution)
    print("\n" + "=" * 60)
    print("TEST 3: JSON schema without grounding")
    print("-" * 60)
    
    schema = {
        "type": "object",
        "properties": {
            "greeting": {"type": "string"},
            "number": {"type": "number"}
        },
        "required": ["greeting", "number"]
    }
    
    req3 = RunRequest(
        run_id="test-003",
        client_id="test",
        provider="vertex",
        model_name="gemini-2.0-flash",
        grounding_mode=GroundingMode.OFF,
        system_text="Return JSON only.",
        user_prompt="Return a JSON object with greeting='Hello' and number=42",
        temperature=0.0,
        seed=42,
        schema=schema
    )
    
    try:
        result3 = adapter.run(req3)
        print(f"✓ Response: {result3.json_text}")
        print(f"✓ JSON valid: {result3.json_valid}")
        print(f"✓ JSON object: {result3.json_obj}")
        print(f"✓ Grounded: {result3.grounded_effective}")
        
        assert result3.json_valid == True, "Should have valid JSON"
        assert result3.json_obj is not None, "Should have JSON object"
        assert result3.grounded_effective == False, "Should not be grounded"
        print("✓ TEST 3 PASSED")
    except Exception as e:
        print(f"✗ TEST 3 FAILED: {e}")
    
    # Test 4: Grounding PREFERRED mode (graceful degradation)
    print("\n" + "=" * 60)
    print("TEST 4: Grounding PREFERRED mode")
    print("-" * 60)
    
    req4 = RunRequest(
        run_id="test-004",
        client_id="test",
        provider="vertex",
        model_name="gemini-2.0-flash",
        grounding_mode=GroundingMode.PREFERRED,
        system_text="Answer the question.",
        user_prompt="What is 2+2?",  # Won't trigger search
        temperature=0.0,
        seed=42
    )
    
    try:
        result4 = adapter.run(req4)
        print(f"✓ Response: {result4.json_text}")
        print(f"✓ Grounded: {result4.grounded_effective}")
        print(f"✓ Tool calls: {result4.tool_call_count}")
        # Should succeed even if not grounded (PREFERRED mode)
        print("✓ TEST 4 PASSED")
    except Exception as e:
        print(f"✗ TEST 4 FAILED: {e}")
    
    # Test 5: Legacy interface compatibility
    print("\n" + "=" * 60)
    print("TEST 5: Legacy analyze_with_gemini interface")
    print("-" * 60)
    
    try:
        legacy_result = await adapter.analyze_with_gemini(
            prompt="What is the capital of France?",
            use_grounding=True,
            model_name="gemini-2.0-flash",
            temperature=0.0,
            seed=42
        )
        print(f"✓ Response: {legacy_result.get('content', '')[:100]}...")
        print(f"✓ Grounded: {legacy_result.get('grounded')}")
        print(f"✓ Model version: {legacy_result.get('model_version')}")
        print("✓ TEST 5 PASSED")
    except Exception as e:
        print(f"✗ TEST 5 FAILED: {e}")
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    # Run the async tests
    asyncio.run(test_vertex_adapter())