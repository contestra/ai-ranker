"""Direct test of GPT-5 API to diagnose empty response issue"""
import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_gpt5_models():
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    models_to_test = [
        ("gpt-4o", 0.7),  # GPT-4o with normal temperature
        ("gpt-4o-mini", 0.7),  # GPT-4o-mini with normal temperature
        ("gpt-4-turbo-preview", 0.7),  # GPT-4 Turbo
        ("gpt-3.5-turbo", 0.7),  # GPT-3.5 for baseline
    ]
    
    # Note: GPT-5 models commented out as they don't exist yet
    # The "gpt-5" model names in the codebase are placeholders/future-proofing
    
    prompt = "What do you know about AVEA? List any companies or brands with this name."
    
    for model_name, temp in models_to_test:
        print(f"\n{'='*60}")
        print(f"Testing model: {model_name} (temperature: {temp})")
        print(f"{'='*60}")
        
        try:
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temp,
                max_tokens=500,
                seed=42
            )
            
            content = response.choices[0].message.content
            print(f"Response length: {len(content) if content else 0}")
            print(f"Response preview: {content[:200] if content else 'EMPTY'}")
            
            # Check response metadata
            if hasattr(response, 'usage'):
                print(f"Tokens used: {response.usage.total_tokens}")
            if hasattr(response, 'system_fingerprint'):
                print(f"System fingerprint: {response.system_fingerprint}")
                
        except Exception as e:
            print(f"ERROR: {str(e)}")
            if "model" in str(e).lower():
                print("Note: Model might not exist or be accessible")

if __name__ == "__main__":
    asyncio.run(test_gpt5_models())