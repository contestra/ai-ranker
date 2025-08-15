#!/usr/bin/env python
"""
Test proper API-level grounding vs prompt-based grounding
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from app.config import settings

# Check if Google grounding tools are available
try:
    from google.ai.generativelanguage_v1beta.types import Tool as GenAITool
    GROUNDING_AVAILABLE = True
    print("SUCCESS: Google grounding tools available")
except ImportError:
    GROUNDING_AVAILABLE = False
    print("WARNING: Google grounding tools NOT available")

async def test_api_grounding():
    """Test API-level grounding (the right way)"""
    
    print("\n" + "=" * 60)
    print("Testing API-level grounding (the RIGHT way)")
    print("=" * 60)
    
    if not GROUNDING_AVAILABLE:
        print("Cannot test - grounding tools not available")
        return
    
    # Create model
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0.1,
        google_api_key=settings.google_api_key
    )
    
    # Enable grounding via API tools
    try:
        search_tool = GenAITool(google_search={})
        grounded_model = model.bind_tools([search_tool])
        print("SUCCESS: Successfully bound Google Search tool to model")
    except Exception as e:
        print(f"FAILED: Failed to bind tools: {e}")
        return
    
    # Test with a naked prompt (no "please search" text)
    prompt = "What are the top 3 longevity supplement brands in 2024?"
    
    # Add only a system message about tool usage
    messages = [
        SystemMessage(content="You may use tools to verify facts. Do not mention tool use, sources, or URLs in the answer."),
        HumanMessage(content=prompt)  # NAKED prompt
    ]
    
    print(f"\nPrompt (naked): {prompt}")
    print("Grounding: ENABLED via API tools")
    
    try:
        response = await grounded_model.ainvoke(messages)
        if response and response.content:
            print(f"\nSUCCESS: SUCCESS - Response length: {len(response.content)} chars")
            print(f"Preview: {response.content[:200]}...")
            
            # Check if tools were actually used
            if hasattr(response, 'response_metadata'):
                metadata = response.response_metadata
                if 'tool_calls' in metadata or 'grounding_chunks' in metadata:
                    print("\nSUCCESS: Tools were used (found in metadata)")
                else:
                    print("\n? Tool usage not visible in metadata")
        else:
            print("\nFAILED: FAILED - Empty response")
    except Exception as e:
        print(f"\nFAILED: ERROR: {e}")

async def test_prompt_grounding():
    """Test prompt-based grounding (the WRONG way)"""
    
    print("\n" + "=" * 60)
    print("Testing prompt-based grounding (the OLD/WRONG way)")
    print("=" * 60)
    
    # Create model WITHOUT tools
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0.1,
        google_api_key=settings.google_api_key
    )
    
    # Modify prompt to ask for web search (wrong approach)
    prompt = "Please search the web and tell me: What are the top 3 longevity supplement brands in 2024?"
    
    messages = [HumanMessage(content=prompt)]
    
    print(f"\nPrompt (modified): {prompt}")
    print("Grounding: Via prompt text only (no API tools)")
    
    try:
        response = await model.ainvoke(messages)
        if response and response.content:
            print(f"\nSUCCESS: Response length: {len(response.content)} chars")
            print(f"Preview: {response.content[:200]}...")
        else:
            print("\nFAILED: Empty response")
    except Exception as e:
        print(f"\nFAILED: ERROR: {e}")

async def main():
    """Run both tests"""
    
    print("Comparing API-level grounding vs prompt-based grounding")
    print("=" * 60)
    
    # Test the right way
    await test_api_grounding()
    
    # Test the wrong way
    await test_prompt_grounding()
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("- API-level grounding: Uses actual Google Search tool via API")
    print("- Prompt-based: Just adds 'please search' to the prompt text")
    print("- API-level is deterministic and controllable")
    print("- Prompt-based is fragile and model-dependent")

if __name__ == "__main__":
    asyncio.run(main())