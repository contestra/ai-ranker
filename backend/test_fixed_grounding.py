#!/usr/bin/env python
"""
Test the fixed grounding implementation with tool loop
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.llm.langchain_adapter import LangChainAdapter

async def test_grounding():
    """Test grounding with the fixed implementation"""
    
    adapter = LangChainAdapter()
    
    print("=" * 60)
    print("Testing FIXED grounding implementation")
    print("=" * 60)
    
    # Test 1: Without grounding
    print("\nTest 1: WITHOUT grounding")
    print("-" * 40)
    
    response1 = await adapter.analyze_with_gemini(
        prompt="What is the current temperature in Tokyo?",
        use_grounding=False,
        model_name="gemini-2.5-pro",
        temperature=0.1
    )
    
    if response1.get("content"):
        print(f"Response length: {len(response1['content'])}")
        print(f"Preview: {response1['content'][:150]}...")
    else:
        print("Empty response")
    
    # Test 2: WITH grounding (should trigger tool loop)
    print("\nTest 2: WITH grounding (tool loop)")
    print("-" * 40)
    
    response2 = await adapter.analyze_with_gemini(
        prompt="What is the current temperature in Tokyo?",
        use_grounding=True,  # This should trigger tool calls
        model_name="gemini-2.5-pro",
        temperature=0.1
    )
    
    if response2.get("content"):
        print(f"Response length: {len(response2['content'])}")
        print(f"Preview: {response2['content'][:150]}...")
    else:
        print("Empty response")
        print(f"Error details: {response2}")
    
    # Test 3: Grounding with brand question
    print("\nTest 3: Brand question WITH grounding")
    print("-" * 40)
    
    response3 = await adapter.analyze_with_gemini(
        prompt="What are the top 3 longevity supplement brands in 2024?",
        use_grounding=True,
        model_name="gemini-2.5-pro",
        temperature=0.1
    )
    
    if response3.get("content"):
        print(f"Response length: {len(response3['content'])}")
        print(f"Preview: {response3['content'][:150]}...")
    else:
        print("Empty response")
        print(f"Error details: {response3}")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("- Without grounding: Model uses training data only")
    print("- With grounding: Model should call web_search tool, then generate response")
    print("- Tool loop handles the tool calls automatically")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_grounding())