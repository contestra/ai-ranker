"""
Test GPT-5 directly
"""
import asyncio
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
import os

async def test_gpt5():
    """Test GPT-5 directly"""
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set")
        return
    
    print(f"Using API key: {api_key[:10]}...")
    
    model = ChatOpenAI(
        model="gpt-5",
        temperature=1.0,
        api_key=api_key
    )
    
    print("Sending test message to GPT-5...")
    
    try:
        response = await model.ainvoke([
            HumanMessage(content="Say 'Hello World' and nothing else")
        ])
        
        print(f"Response type: {type(response)}")
        print(f"Response content: {response.content if hasattr(response, 'content') else 'NO CONTENT'}")
        print(f"Full response: {response}")
        
        if hasattr(response, 'response_metadata'):
            print(f"Metadata: {response.response_metadata}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    asyncio.run(test_gpt5())