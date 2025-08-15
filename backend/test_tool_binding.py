#!/usr/bin/env python
"""
Test if tool binding is working correctly with Gemini
"""

import asyncio
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from app.config import settings

async def test_tool_binding_methods():
    """Test different ways to bind tools"""
    
    print("=" * 60)
    print("Testing different tool binding methods")
    print("=" * 60)
    
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0.1,
        google_api_key=settings.google_api_key
    )
    
    # Method 1: Try with langchain tools format
    print("\nMethod 1: Using LangChain tools format")
    print("-" * 40)
    
    tools = [{
        "type": "function",
        "function": {
            "name": "google_search",
            "description": "Search Google for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        }
    }]
    
    try:
        model_with_tools = model.bind_tools(tools)
        messages = [
            HumanMessage(content="What is the current temperature in Tokyo right now?")
        ]
        response = await model_with_tools.ainvoke(messages)
        print(f"Response has content: {bool(response.content)}")
        print(f"Response has tool_calls: {bool(hasattr(response, 'tool_calls') and response.tool_calls)}")
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print(f"Tool calls: {response.tool_calls}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Method 2: Try with google_search_retrieval option
    print("\nMethod 2: Using google_search_retrieval in model_kwargs")
    print("-" * 40)
    
    try:
        # Try to enable grounding via model_kwargs
        model2 = ChatGoogleGenerativeAI(
            model="gemini-2.5-pro",
            temperature=0.1,
            google_api_key=settings.google_api_key,
            model_kwargs={
                "tools": [{"google_search_retrieval": {}}]
            }
        )
        
        messages = [
            HumanMessage(content="What is the current temperature in Tokyo right now?")
        ]
        response = await model2.ainvoke(messages)
        print(f"Response has content: {bool(response.content)}")
        if response.content:
            print(f"Content preview: {response.content[:100]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Method 3: Direct API call to check if grounding works at all
    print("\nMethod 3: Using direct Google GenerativeAI API")
    print("-" * 40)
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.google_api_key)
        
        # Try with tools parameter
        model3 = genai.GenerativeModel(
            'gemini-2.5-pro',
            tools=[{"google_search_retrieval": {}}]
        )
        
        response = model3.generate_content("What is the current temperature in Tokyo right now?")
        print(f"Response has text: {bool(response.text if hasattr(response, 'text') else None)}")
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content'):
                print(f"Content parts: {candidate.content.parts if hasattr(candidate.content, 'parts') else 'N/A'}")
    except Exception as e:
        print(f"Error: {e}")
        
    # Method 4: Check if we need to explicitly enable grounding
    print("\nMethod 4: Checking LangChain model configuration")
    print("-" * 40)
    
    model4 = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0.1,
        google_api_key=settings.google_api_key
    )
    
    print(f"Model dict keys: {model4.__dict__.keys()}")
    print(f"Model supports tools: {hasattr(model4, 'bind_tools')}")
    
    # Check what happens with a prompt that definitely needs current info
    messages = [
        SystemMessage(content="Use web search to get current information."),
        HumanMessage(content="What major news event happened today?")
    ]
    
    try:
        response = await model4.ainvoke(messages)
        print(f"Response length: {len(response.content) if response.content else 0}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_tool_binding_methods())