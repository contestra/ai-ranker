#!/usr/bin/env python3
"""
Test GPT-5 with OpenAI SDK Responses API
Testing the correct approach with web_search tool
"""

from openai import OpenAI
import os
import json

client = OpenAI()

def run_openai_required_search(model: str, user_text: str, force_specific: bool = False):
    """
    Run OpenAI Responses API with required web search
    Using the correct SDK approach, not raw HTTP
    """
    tools = [{"type": "web_search"}]  # only the web_search tool enabled
    tool_choice = "required"           # guarantees ≥1 tool call
    
    # If you want to force *this* tool specifically
    if force_specific:
        tool_choice = {"type": "tool", "name": "web_search"}
    
    print(f"\n{'='*60}")
    print(f"Testing {model} with tool_choice={tool_choice}")
    print(f"Prompt: {user_text[:100]}...")
    print('='*60)
    
    try:
        resp = client.responses.create(
            model=model,  # e.g., "gpt-5" or "gpt-4o"
            input=user_text,
            tools=tools,
            tool_choice=tool_choice,
            temperature=1.0 if 'gpt-5' in model else 0.0,
            # If you want strict JSON later, do a *second* pass that formats JSON
            # from the first pass's `message` output_text. Don't mix tools + json_schema.
        )
        
        # Debug: show output structure
        print(f"Response has {len(resp.output)} output items")
        for i, o in enumerate(resp.output[:5]):  # First 5 items
            print(f"  Item {i}: type={getattr(o, 'type', 'unknown')}")
        
        # Enforce REQUIRED by counting web searches
        search_calls = [o for o in resp.output if getattr(o, "type", None) == "web_search_call"]
        print(f"\nWeb search calls found: {len(search_calls)}")
        
        if len(search_calls) == 0 and tool_choice == "required":
            print("❌ FAILED: REQUIRED mode but no web_search_call items found")
        else:
            print(f"✅ SUCCESS: Found {len(search_calls)} web search calls")
        
        # Extract assistant text from message outputs
        message_texts = []
        for o in resp.output:
            if getattr(o, "type", None) == "message":
                for c in getattr(o, "content", []):
                    if getattr(c, "type", None) == "output_text":
                        text = getattr(c, "text", "")
                        if text:
                            message_texts.append(text)
                            print(f"\nMessage text preview: {text[:200]}...")
        
        result = {
            "tool_call_count": len(search_calls),
            "text": "\n\n".join(message_texts).strip(),
            "text_length": sum(len(t) for t in message_texts)
        }
        
        print(f"\nResult summary:")
        print(f"  - Tool calls: {result['tool_call_count']}")
        print(f"  - Text length: {result['text_length']} chars")
        
        return result
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print(f"Error type: {type(e).__name__}")
        return {"error": str(e), "tool_call_count": 0, "text": ""}

def test_suite():
    """Run comprehensive tests"""
    
    # Test 1: VAT probe with Required mode
    print("\n" + "="*80)
    print("TEST 1: VAT probe with REQUIRED mode")
    print("="*80)
    result1 = run_openai_required_search(
        "gpt-5",
        "What is the standard VAT rate in Slovenia (SI) today? Cite sources."
    )
    
    # Test 2: Weather query (should definitely trigger search)
    print("\n" + "="*80)
    print("TEST 2: Current weather with REQUIRED mode")
    print("="*80)
    result2 = run_openai_required_search(
        "gpt-5",
        "What is the current weather in New York City right now? Search for the latest information."
    )
    
    # Test 3: Try with gpt-4o for comparison
    print("\n" + "="*80)
    print("TEST 3: GPT-4o comparison with REQUIRED mode")
    print("="*80)
    result3 = run_openai_required_search(
        "gpt-4o",
        "What is the standard VAT rate in Germany today? Cite sources."
    )
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"GPT-5 VAT query: {result1.get('tool_call_count', 0)} searches, {result1.get('text_length', 0)} chars")
    print(f"GPT-5 Weather query: {result2.get('tool_call_count', 0)} searches, {result2.get('text_length', 0)} chars")
    print(f"GPT-4o VAT query: {result3.get('tool_call_count', 0)} searches, {result3.get('text_length', 0)} chars")

if __name__ == "__main__":
    test_suite()