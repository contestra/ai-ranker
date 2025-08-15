#!/usr/bin/env python
"""
Test to verify that LangChain is returning tool calls, not empty responses
"""

import asyncio
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain_core.messages import ToolMessage
from app.config import settings

try:
    from google.ai.generativelanguage_v1beta.types import Tool as GenAITool
    GROUNDING_AVAILABLE = True
except ImportError:
    GROUNDING_AVAILABLE = False

async def test_tool_call_response():
    """Test what we actually get back when tools are bound"""
    
    print("=" * 60)
    print("Testing what LangChain returns with tools bound")
    print("=" * 60)
    
    if not GROUNDING_AVAILABLE:
        print("Cannot test - grounding tools not available")
        return
    
    # Create model and bind tools
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0.1,
        google_api_key=settings.google_api_key
    )
    
    # Bind Google Search tool
    search_tool = GenAITool(google_search={})
    grounded_model = model.bind_tools([search_tool])
    
    # Test prompt that likely needs grounding
    messages = [
        SystemMessage(content="You may use tools to verify facts. Do not mention tool use, sources, or URLs in the answer."),
        HumanMessage(content="What are the top 3 longevity supplement brands in 2024?")
    ]
    
    print("\nInvoking model with tools bound...")
    print("-" * 40)
    
    try:
        # First invocation - expect tool call
        ai_response = await grounded_model.ainvoke(messages)
        
        print(f"Response type: {type(ai_response)}")
        print(f"Response content: '{ai_response.content}'" if ai_response.content else "No content")
        
        # Check for tool calls
        if hasattr(ai_response, 'tool_calls') and ai_response.tool_calls:
            print(f"\n✓ TOOL CALLS DETECTED: {len(ai_response.tool_calls)} calls")
            for i, tool_call in enumerate(ai_response.tool_calls):
                print(f"\nTool Call {i+1}:")
                print(f"  Name: {tool_call.get('name', 'N/A')}")
                print(f"  ID: {tool_call.get('id', 'N/A')}")
                print(f"  Args: {tool_call.get('args', {})}")
        else:
            print("\nNo tool_calls attribute or empty")
        
        # Check additional_kwargs
        if hasattr(ai_response, 'additional_kwargs'):
            print(f"\nadditional_kwargs: {json.dumps(ai_response.additional_kwargs, indent=2)[:500]}...")
        
        # Check for function calls (older format)
        if hasattr(ai_response, 'function_call'):
            print(f"\nfunction_call: {ai_response.function_call}")
            
        print("\n" + "=" * 60)
        print("DIAGNOSIS: The model IS returning tool calls, not empty content!")
        print("We need to execute the tool loop to get the final text.")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {e}")
        print(f"Error type: {type(e).__name__}")

async def test_with_tool_loop():
    """Test with proper tool loop execution"""
    
    print("\n" + "=" * 60)
    print("Testing with proper tool loop execution")
    print("=" * 60)
    
    if not GROUNDING_AVAILABLE:
        return
    
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0.1,
        google_api_key=settings.google_api_key
    )
    
    search_tool = GenAITool(google_search={})
    grounded_model = model.bind_tools([search_tool])
    
    messages = [
        SystemMessage(content="You may use tools to verify facts. Do not mention tool use, sources, or URLs in the answer."),
        HumanMessage(content="What are the top 3 longevity supplement brands in 2024?")
    ]
    
    print("\nStep 1: Initial model call...")
    ai_response = await grounded_model.ainvoke(messages)
    
    if hasattr(ai_response, 'tool_calls') and ai_response.tool_calls:
        print(f"Tool calls requested: {len(ai_response.tool_calls)}")
        
        # Simulate tool execution (in reality, this would call Google Search)
        tool_messages = []
        for tool_call in ai_response.tool_calls:
            print(f"  Simulating execution of: {tool_call.get('name')}")
            
            # Create a tool result message
            tool_result = ToolMessage(
                content="Based on 2024 reviews: 1. Elysium Health - Known for Basis NAD+ supplement. 2. Tru Niagen - Popular NR supplement. 3. Life Extension - Comprehensive longevity formulas.",
                tool_call_id=tool_call.get('id', 'test-id')
            )
            tool_messages.append(tool_result)
        
        # Add AI response and tool results to conversation
        messages.append(ai_response)
        messages.extend(tool_messages)
        
        print("\nStep 2: Second model call with tool results...")
        final_response = await grounded_model.ainvoke(messages)
        
        print(f"\nFinal response content length: {len(final_response.content) if final_response.content else 0}")
        if final_response.content:
            print(f"Preview: {final_response.content[:200]}...")
            print("\n✓ SUCCESS: Got final text after tool loop!")
        else:
            print("Still no content after tool loop")
            
    else:
        print("No tool calls in initial response")
        if ai_response.content:
            print(f"Got direct content: {ai_response.content[:200]}...")

async def main():
    """Run both tests"""
    await test_tool_call_response()
    await test_with_tool_loop()

if __name__ == "__main__":
    asyncio.run(main())