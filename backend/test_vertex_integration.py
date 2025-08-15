#!/usr/bin/env python
"""
Test Vertex GenAI integration with the langchain adapter
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.llm.langchain_adapter import LangChainAdapter

async def test_vertex_grounding():
    """Test that grounding uses Vertex GenAI"""
    
    print("=" * 60)
    print("Testing Vertex GenAI Integration")
    print("=" * 60)
    
    adapter = LangChainAdapter()
    
    # Test 1: Ungrounded (should use direct API)
    print("\nTest 1: Ungrounded (direct API)")
    print("-" * 40)
    
    result1 = await adapter.analyze_with_gemini(
        prompt="What is 2+2?",
        use_grounding=False,
        model_name="gemini-1.5-pro",
        temperature=0.0,
        seed=42
    )
    
    if result1.get("content"):
        print(f"[OK] Got response: {result1['content'][:50]}...")
    else:
        print(f"[ERROR] {result1.get('error', 'No content')}")
    
    # Test 2: Grounded (should use Vertex)
    print("\nTest 2: Grounded (Vertex GenAI)")
    print("-" * 40)
    
    result2 = await adapter.analyze_with_gemini(
        prompt="What is the current temperature in Tokyo?",
        use_grounding=True,
        model_name="gemini-1.5-pro",
        temperature=0.0,
        seed=42
    )
    
    if result2.get("content"):
        print(f"[OK] Got grounded response: {result2['content'][:100]}...")
        if result2.get("grounded"):
            print("[OK] Response marked as grounded")
    else:
        print(f"[ERROR] {result2.get('error', 'No content')}")
    
    # Test 3: With ALS context
    print("\nTest 3: Grounded with ALS context (Germany)")
    print("-" * 40)
    
    als_context = """Ambient Context:
- 2025-08-14 14:05, UTC+01:00
- bund.de — "Führerschein verlängern"
- 10115 Berlin • +49 30 xxxx xxxx • 12,90 €"""
    
    result3 = await adapter.analyze_with_gemini(
        prompt="What's the VAT rate?",
        use_grounding=False,  # Don't need grounding for this
        model_name="gemini-1.5-pro",
        temperature=0.0,
        seed=42,
        context=als_context
    )
    
    if result3.get("content"):
        print(f"[OK] Response: {result3['content']}")
        if "19" in result3['content']:
            print("[OK] Correctly inferred German VAT!")
    else:
        print(f"[ERROR] {result3.get('error', 'No content')}")
    
    # Test 4: Grounded with brand question
    print("\nTest 4: Grounded brand search")
    print("-" * 40)
    
    result4 = await adapter.analyze_with_gemini(
        prompt="What are the top 3 longevity supplement brands in 2024?",
        use_grounding=True,
        model_name="gemini-1.5-pro",
        temperature=0.0
    )
    
    if result4.get("content"):
        print(f"[OK] Got brand response: {result4['content'][:150]}...")
    else:
        print(f"[ERROR] {result4.get('error', 'No content')}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    tests = [
        ("Ungrounded", bool(result1.get("content"))),
        ("Grounded", bool(result2.get("content"))),
        ("ALS Context", bool(result3.get("content"))),
        ("Brand Search", bool(result4.get("content")))
    ]
    
    for name, passed in tests:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {name}")
    
    if all(t[1] for t in tests):
        print("\nSUCCESS! Vertex integration is working!")
    else:
        print("\nSome tests failed. Check if Vertex AI API is enabled.")

if __name__ == "__main__":
    asyncio.run(test_vertex_grounding())