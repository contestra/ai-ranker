"""Simple test to verify GPT-5 works"""
import asyncio
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

async def test_gpt5():
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    print("Testing GPT-5 with OpenAI client...")
    
    try:
        response = await client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": "What do you know about AVEA? Keep response short."}],
            temperature=1.0,  # GPT-5 requires 1.0
            max_completion_tokens=200  # GPT-5 uses max_completion_tokens
            # Removed seed parameter to test
        )
        
        content = response.choices[0].message.content
        print(f"Response length: {len(content)}")
        print(f"Response: {content}")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_gpt5())
    print(f"\nTest {'PASSED' if success else 'FAILED'}")