#!/usr/bin/env python
"""
Test different Gemini model variants to see which ones work
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage
from app.config import settings

async def test_model(model_name: str, use_grounding: bool = False):
    """Test a specific Gemini model"""
    print(f"\nTesting model: {model_name} (grounding={'ON' if use_grounding else 'OFF'})")
    print("-" * 40)
    
    try:
        model = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.1,
            google_api_key=settings.google_api_key
        )
        
        if use_grounding:
            prompt = "Please search the web and tell me: What are the top 3 longevity supplement brands in 2024?"
        else:
            prompt = "What are the top 3 longevity supplement brands?"
        
        messages = [HumanMessage(content=prompt)]
        
        response = await model.ainvoke(messages)
        
        if response and response.content:
            print(f"SUCCESS - Response length: {len(response.content)} chars")
            print(f"Preview: {response.content[:100]}...")
        else:
            print(f"FAILED - Empty response")
            
    except Exception as e:
        print(f"ERROR: {e}")

async def main():
    """Test various Gemini models"""
    
    models_to_test = [
        ("gemini-2.5-pro", False),
        ("gemini-2.5-pro", True),
        ("gemini-2.5-flash", False),
        ("gemini-2.5-flash", True),
        ("gemini-2.0-flash-exp", False),
        ("gemini-2.0-flash-exp", True),
        ("gemini-1.5-pro", False),
        ("gemini-1.5-flash", False),
    ]
    
    print("Testing Gemini Model Variants")
    print("=" * 60)
    
    for model_name, use_grounding in models_to_test:
        await test_model(model_name, use_grounding)
        await asyncio.sleep(1)  # Small delay between tests
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("- gemini-2.5-pro and gemini-2.5-flash are the latest models")
    print("- gemini-2.0-flash-exp is experimental")
    print("- Grounding (web search) may not work with all model variants")

if __name__ == "__main__":
    asyncio.run(main())