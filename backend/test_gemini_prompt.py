import asyncio
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage

# Load environment variables
load_dotenv()

async def test_gemini():
    """Test Gemini directly with a simple prompt"""
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found in environment")
        return
    
    print(f"API Key loaded: {api_key[:10]}...")
    
    # Test with gemini-2.5-pro (what the code uses)
    model_name = "gemini-2.5-pro"
    print(f"\nTesting with model: {model_name}")
    
    try:
        model = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.0,
            google_api_key=api_key
        )
        
        # Simple test prompt
        prompt = "List the top 10 longevity supplement companies"
        print(f"Prompt: {prompt}")
        
        messages = [HumanMessage(content=prompt)]
        
        print("\nCalling Gemini...")
        response = await model.ainvoke(messages)
        
        print(f"\nResponse type: {type(response)}")
        print(f"Response content type: {type(response.content) if hasattr(response, 'content') else 'No content attr'}")
        print(f"Response length: {len(response.content) if hasattr(response, 'content') else 0}")
        print(f"\nResponse content:\n{response.content if hasattr(response, 'content') else response}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_gemini())