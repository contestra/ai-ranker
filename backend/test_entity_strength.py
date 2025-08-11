"""
Test Entity Strength prompt with GPT-5
"""
import asyncio
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import os
import json

async def test_entity_strength():
    """Test Entity Strength prompt with GPT-5"""
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set")
        return
    
    model = ChatOpenAI(
        model="gpt-5",
        temperature=1.0,
        api_key=api_key
    )
    
    system_prompt = """You are evaluating whether a brand/company is genuinely known to you.

Classify responses into one of these categories:
- OK_STRONG: You have specific, verifiable facts about this real entity (founding date, location, products, leadership, etc.)
- OK_WEAK: You recognize the name or have some context but lack specific details
- CLARIFY: You have no information about this brand - it's completely unknown to you
- BLOCKED: You cannot or will not provide information

Important: Be honest about what you don't know. If you have zero information about a brand, classify it as CLARIFY. Only use OK_WEAK if you have at least some contextual knowledge.

Be honest about what you actually know vs. what you're inferring."""
    
    user_prompt = """Tell me about Apple. What do they do, where are they based, and what are they known for?

Provide your response in this JSON format:
{
    "classification": "OK_STRONG|OK_WEAK|CLARIFY|HALLUCINATION|BLOCKED",
    "confidence": 0-100,
    "reasoning": "Brief explanation of your classification",
    "specific_claims": ["List of specific, verifiable facts you know"],
    "generic_claims": ["List of generic or inferred statements"],
    "response_text": "Your natural language response about the brand"
}"""
    
    print("Testing Entity Strength with Apple...")
    
    try:
        # Combine prompts for OpenAI (it doesn't use system messages the same way)
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        response = await model.ainvoke([
            HumanMessage(content=combined_prompt)
        ])
        
        print(f"\nResponse content:\n{response.content.encode('utf-8', errors='replace').decode('utf-8')}")
        print(f"\nReasoning tokens used: {response.response_metadata.get('token_usage', {}).get('completion_tokens_details', {}).get('reasoning_tokens', 0)}")
        
        # Try to parse JSON
        content = response.content
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = content[json_start:json_end]
            print(f"\nExtracted JSON:\n{json_str}")
            parsed = json.loads(json_str)
            print(f"\nParsed successfully: {parsed['classification']}")
        else:
            print("\nNo JSON found in response")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_entity_strength())