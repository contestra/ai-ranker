"""Test GPT-5 exactly as it was working earlier today"""
import asyncio
from app.llm.langchain_adapter import LangChainAdapter

async def test_gpt5():
    adapter = LangChainAdapter()
    
    # Test GPT-5 with the exact parameters that were working
    print("Testing GPT-5 with temperature=1.0 (as required for GPT-5)")
    
    result = await adapter.analyze_with_gpt4(
        prompt="What do you know about AVEA?",
        model_name="gpt-5",
        temperature=0.0,  # Will be overridden to 1.0 for GPT-5
        seed=42
    )
    
    print(f"Model: {result.get('model_version')}")
    print(f"Temperature: {result.get('temperature')}")
    print(f"Response time: {result.get('response_time_ms')}ms")
    print(f"Response length: {len(result.get('content', ''))}")
    print(f"Error: {result.get('error', 'None')}")
    print(f"Retry attempts: {result.get('retry_attempts', 0)}")
    print(f"\nResponse content:")
    print(result.get('content', 'EMPTY'))
    
if __name__ == "__main__":
    asyncio.run(test_gpt5())