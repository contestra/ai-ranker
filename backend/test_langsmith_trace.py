#!/usr/bin/env python3
"""
Test that LangSmith tracing is working by using the direct LangChain path.
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')

async def test_langsmith():
    """Test that should definitely show up in LangSmith."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.schema import HumanMessage, SystemMessage
    from langchain.callbacks import LangChainTracer
    from langsmith import Client
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Set up tracing
    tracer = LangChainTracer(
        project_name=os.getenv("LANGCHAIN_PROJECT", "ai-ranker"),
        client=Client(api_key=os.getenv("LANGCHAIN_API_KEY"))
    )
    
    print("\n" + "="*60)
    print(" TESTING LANGSMITH TRACING")
    print("="*60)
    
    # Create model with explicit API key
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.7
    )
    
    # Test message
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="What is 2+2? Reply with just the number.")
    ]
    
    print("\nSending test message to Gemini via LangChain...")
    print(f"Project: {os.getenv('LANGCHAIN_PROJECT')}")
    print(f"Tracing: {os.getenv('LANGCHAIN_TRACING_V2')}")
    
    try:
        # Invoke with callbacks
        response = await model.ainvoke(
            messages,
            config={"callbacks": [tracer]}
        )
        
        print(f"Response: {response.content}")
        print("\n✅ This should now appear in LangSmith!")
        print(f"Check: https://smith.langchain.com/o/{os.getenv('LANGCHAIN_PROJECT', 'ai-ranker')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_langsmith())