#!/usr/bin/env python
"""
Simple test of Gemini to isolate the issue
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage
from app.config import settings

async def test_simple():
    """Simplest possible test"""
    
    print("Testing basic Gemini without any grounding...")
    
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0.1,
        google_api_key=settings.google_api_key
    )
    
    messages = [HumanMessage(content="What is 2+2?")]
    
    try:
        response = await model.ainvoke(messages)
        if response and response.content:
            print(f"SUCCESS: {response.content}")
        else:
            print("FAILED: Empty response")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple())