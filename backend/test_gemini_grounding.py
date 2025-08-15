#!/usr/bin/env python
"""
Test script to verify Gemini grounding (web search) functionality
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.llm.langchain_adapter import LangChainAdapter

async def test_gemini_grounding():
    """Test Gemini with and without grounding"""
    
    adapter = LangChainAdapter()
    prompt = "What are the top 3 longevity supplement brands in 2024?"
    
    print("Testing Gemini WITHOUT grounding (model knowledge only)...")
    print("=" * 60)
    
    try:
        # Test without grounding
        response_no_ground = await adapter.analyze_with_gemini(
            prompt=prompt,
            use_grounding=False,
            model_name="gemini-2.5-pro",
            temperature=0.1,
            seed=42
        )
        
        if response_no_ground.get("content"):
            print("SUCCESS - Response received without grounding:")
            print(response_no_ground["content"][:200] + "...")
        else:
            print("FAILED - Empty response without grounding")
            print(f"Full response: {response_no_ground}")
    except Exception as e:
        print(f"ERROR without grounding: {e}")
    
    print("\n" + "=" * 60)
    print("Testing Gemini WITH grounding (web search)...")
    print("=" * 60)
    
    try:
        # Test with grounding
        response_with_ground = await adapter.analyze_with_gemini(
            prompt=prompt,
            use_grounding=True,
            model_name="gemini-2.5-pro",
            temperature=0.1,
            seed=42
        )
        
        if response_with_ground.get("content"):
            print("SUCCESS - Response received with grounding:")
            print(response_with_ground["content"][:200] + "...")
        else:
            print("FAILED - Empty response with grounding")
            print(f"Full response: {response_with_ground}")
    except Exception as e:
        print(f"ERROR with grounding: {e}")
    
    print("\n" + "=" * 60)
    print("Testing with simpler prompt...")
    print("=" * 60)
    
    simple_prompt = "What is the current weather in New York?"
    
    try:
        # Test with grounding on a simple prompt
        response_simple = await adapter.analyze_with_gemini(
            prompt=simple_prompt,
            use_grounding=True,
            model_name="gemini-2.5-pro",
            temperature=0.1
        )
        
        if response_simple.get("content"):
            print("SUCCESS - Simple prompt with grounding:")
            print(response_simple["content"][:200] + "...")
        else:
            print("FAILED - Empty response for simple prompt with grounding")
            print(f"Full response: {response_simple}")
    except Exception as e:
        print(f"ERROR with simple prompt: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini_grounding())