#!/usr/bin/env python
"""
Test specifically why Switzerland (CH) with grounding fails
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.llm.langchain_adapter import LangChainAdapter
from app.services.als import als_service

async def test_ch_grounding():
    """Test CH specifically with and without ALS context"""
    
    adapter = LangChainAdapter()
    prompt = "List the top 10 longevity supplement brands"
    
    # Get CH ambient block
    ch_ambient = als_service.build_als_block("CH")
    print("CH Ambient Block:")
    print("=" * 60)
    print(ch_ambient)
    print("=" * 60)
    
    # Test 1: CH with grounding but NO ambient context
    print("\nTest 1: Grounding WITHOUT ambient context")
    print("-" * 40)
    try:
        response1 = await adapter.analyze_with_gemini(
            prompt=prompt,
            use_grounding=True,
            model_name="gemini-2.5-pro",
            temperature=0.0,
            seed=42,
            context=None  # No ambient context
        )
        if response1.get("content"):
            print(f"SUCCESS - Length: {len(response1['content'])}")
            print(f"Preview: {response1['content'][:100]}...")
        else:
            print("FAILED - Empty response")
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test 2: CH with grounding AND ambient context
    print("\nTest 2: Grounding WITH CH ambient context")
    print("-" * 40)
    try:
        response2 = await adapter.analyze_with_gemini(
            prompt=prompt,
            use_grounding=True,
            model_name="gemini-2.5-pro",
            temperature=0.0,
            seed=42,
            context=ch_ambient  # With CH ambient context
        )
        if response2.get("content"):
            print(f"SUCCESS - Length: {len(response2['content'])}")
            print(f"Preview: {response2['content'][:100]}...")
        else:
            print("FAILED - Empty response")
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test 3: CH WITHOUT grounding but WITH ambient context
    print("\nTest 3: NO grounding WITH CH ambient context")
    print("-" * 40)
    try:
        response3 = await adapter.analyze_with_gemini(
            prompt=prompt,
            use_grounding=False,  # No grounding
            model_name="gemini-2.5-pro",
            temperature=0.0,
            seed=42,
            context=ch_ambient  # With CH ambient context
        )
        if response3.get("content"):
            print(f"SUCCESS - Length: {len(response3['content'])}")
            print(f"Preview: {response3['content'][:100]}...")
        else:
            print("FAILED - Empty response")
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test 4: US ambient for comparison
    print("\nTest 4: Grounding WITH US ambient context (for comparison)")
    print("-" * 40)
    us_ambient = als_service.build_als_block("US")
    try:
        response4 = await adapter.analyze_with_gemini(
            prompt=prompt,
            use_grounding=True,
            model_name="gemini-2.5-pro",
            temperature=0.0,
            seed=42,
            context=us_ambient  # With US ambient context
        )
        if response4.get("content"):
            print(f"SUCCESS - Length: {len(response4['content'])}")
            print(f"Preview: {response4['content'][:100]}...")
        else:
            print("FAILED - Empty response")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_ch_grounding())