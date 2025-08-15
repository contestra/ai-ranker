"""
Test script to verify OpenAI Responses API with web search
This tests the CORRECT API for GPT grounding
"""

import asyncio
import json
import os
from app.llm.openai_responses_adapter import OpenAIResponsesAdapter
from app.config import settings

async def test_responses_api():
    """Test OpenAI Responses API with web search"""
    
    print("=" * 60)
    print("OPENAI RESPONSES API TEST")
    print("=" * 60)
    
    adapter = OpenAIResponsesAdapter(api_key=settings.openai_api_key)
    
    # Test prompt that should benefit from web search
    test_prompt = "What are the current top 3 AI news headlines from today?"
    
    # Test with Singapore ALS context
    singapore_als = """[ALS]
Operating from Singapore; prices in S$. Date format DD/MM/YYYY. Postal 018956. Tel +65 6123 4567. GST applies.
Emergency: 999 (police), 995 (fire/ambulance)."""
    
    print("\n1. Testing GPT-4o UNGROUNDED (no web search)...")
    print("-" * 40)
    
    try:
        ungrounded_result = await adapter.analyze_with_responses(
            prompt=test_prompt,
            model_name="gpt-4o",
            use_grounding=False,
            temperature=0.0,
            seed=42,
            context=singapore_als
        )
        
        print(f"API used: {ungrounded_result.get('api_used', 'unknown')}")
        print(f"Response received: {len(ungrounded_result.get('content', ''))} chars")
        print(f"Tool calls: {ungrounded_result.get('tool_call_count', 0)}")
        print(f"Grounded effective: {ungrounded_result.get('grounded_effective', False)}")
        print(f"Response preview: {ungrounded_result.get('content', '')[:200]}...")
        
        if ungrounded_result.get('tool_call_count', 0) > 0:
            print("[ERROR] Ungrounded mode made tool calls! This shouldn't happen.")
        else:
            print("[OK] Ungrounded mode confirmed (no tool calls)")
    
    except Exception as e:
        print(f"[ERROR] Ungrounded test failed: {str(e)}")
    
    print("\n2. Testing GPT-4o GROUNDED (with web search via Responses API)...")
    print("-" * 40)
    
    try:
        grounded_result = await adapter.analyze_with_responses(
            prompt=test_prompt,
            model_name="gpt-4o",
            use_grounding=True,  # THIS SHOULD USE WEB SEARCH!
            temperature=0.0,
            seed=42,
            context=singapore_als
        )
        
        print(f"API used: {grounded_result.get('api_used', 'unknown')}")
        print(f"Response received: {len(grounded_result.get('content', ''))} chars")
        print(f"Tool calls: {grounded_result.get('tool_call_count', 0)}")
        print(f"Grounded effective: {grounded_result.get('grounded_effective', False)}")
        print(f"Has citations: {grounded_result.get('has_citations', False)}")
        print(f"Response preview: {grounded_result.get('content', '')[:200]}...")
        
        if grounded_result.get('grounding_note'):
            print(f"Note: {grounded_result.get('grounding_note')}")
        
        if grounded_result.get('warning'):
            print(f"Warning: {grounded_result.get('warning')}")
        
        if grounded_result.get('tool_call_count', 0) > 0:
            print("[SUCCESS] Grounded mode made tool calls - web search is working!")
        else:
            print("[INFO] No tool calls made - checking API response...")
            if grounded_result.get('api_used') == 'chat_completions_fallback':
                print("[WARNING] Fell back to Chat Completions API - Responses API may not be available yet")
            else:
                print("[WARNING] Responses API was used but no web search occurred")
    
    except Exception as e:
        print(f"[ERROR] Grounded test failed: {str(e)}")
    
    print("\n3. Testing locale probe with JSON schema enforcement...")
    print("-" * 40)
    
    # Define the exact schema we want
    locale_schema = {
        "type": "object",
        "properties": {
            "vat_percent": {"type": "string"},
            "plug": {"type": "array", "items": {"type": "string"}},
            "emergency": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["vat_percent", "plug", "emergency"],
        "additionalProperties": False
    }
    
    locale_probe = "What are the VAT/GST rate, electrical plug types, and emergency phone numbers for this location?"
    
    try:
        probe_result = await adapter.analyze_with_responses(
            prompt=locale_probe,
            model_name="gpt-4o",
            use_grounding=False,
            temperature=0.0,
            seed=42,
            context=singapore_als,
            enforce_json_schema=locale_schema
        )
        
        print(f"API used: {probe_result.get('api_used', 'unknown')}")
        response = probe_result.get('content', '')
        print(f"Response: {response}")
        print(f"JSON valid flag: {probe_result.get('json_valid')}")
        
        # Try to parse as JSON
        try:
            # Handle potential code fences
            clean_response = response
            if response.startswith('```json'):
                clean_response = response[7:]
                if clean_response.endswith('```'):
                    clean_response = clean_response[:-3]
            
            parsed = json.loads(clean_response.strip())
            print("[OK] Valid JSON returned!")
            print(f"  VAT: {parsed.get('vat_percent')}")
            print(f"  Plug: {parsed.get('plug')}")
            print(f"  Emergency: {parsed.get('emergency')}")
            
            # Check Singapore values
            if parsed.get('vat_percent') in ['8%', '9%']:  # Singapore GST is 8% as of 2024, might be 9% in 2025
                print(f"  [OK] Correct Singapore GST rate: {parsed.get('vat_percent')}")
            if 'G' in parsed.get('plug', []):
                print("  [OK] Correct Singapore plug type!")
            if '999' in parsed.get('emergency', []):
                print("  [OK] Correct Singapore emergency number!")
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON: {e}")
            print(f"Raw response: {response}")
    
    except Exception as e:
        print(f"[ERROR] Locale probe test failed: {str(e)}")
    
    print("\n" + "=" * 60)
    print("RESPONSES API TEST SUMMARY")
    print("=" * 60)
    
    print("\nExpected results when Responses API is available:")
    print("1. Ungrounded: tool_call_count = 0")
    print("2. Grounded: tool_call_count > 0 (web searches made)")
    print("3. JSON enforcement: Clean JSON without code fences")
    print("\nIf seeing fallback warnings, the Responses API may not be")
    print("fully deployed yet. Check OpenAI's API documentation.")

if __name__ == "__main__":
    print("Testing OpenAI Responses API...")
    print("Note: This tests the CORRECT API for web search grounding")
    asyncio.run(test_responses_api())