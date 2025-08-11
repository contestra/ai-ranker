"""
Test GPT-5 directly with AVEA to see raw response
"""
import asyncio
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import os
import json

async def test_avea():
    """Test AVEA with GPT-5 directly"""
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set")
        return
    
    model = ChatOpenAI(
        model="gpt-5",
        temperature=1.0,
        api_key=api_key,
        max_tokens=4000
    )
    
    system_prompt = """You are evaluating whether a brand/company is genuinely known to you.

Classify responses into one of these categories:
- OK_STRONG: You have specific, verifiable facts about this real entity (founding date, location, products, leadership, etc.)
- OK_WEAK: You recognize the name or have some context but lack specific details
- CLARIFY: You have no information about this brand - it's completely unknown to you
- BLOCKED: You cannot or will not provide information

Important: 
1. Be honest about what you don't know. If you have zero information about a brand, classify it as CLARIFY.
2. If multiple entities share the same name, mention all of them and indicate which one you know best.
3. If an industry hint is provided, focus on that specific entity.

Be honest about what you actually know vs. what you're inferring."""
    
    user_prompt = """Tell me about AVEA. What do they do, where are they based, and what are they known for?

Provide your response in this JSON format:
{
    "classification": "OK_STRONG|OK_WEAK|CLARIFY|HALLUCINATION|BLOCKED",
    "confidence": 0-100,
    "reasoning": "Brief explanation of your classification",
    "specific_claims": ["List of specific, verifiable facts you know"],
    "generic_claims": ["List of generic or inferred statements"],
    "response_text": "Your natural language response about the brand",
    "disambiguation_needed": true/false,
    "other_entities": ["List of other entities with the same name if any"]
}"""
    
    print("Testing AVEA with GPT-5...")
    print("="*60)
    
    try:
        # Combine prompts
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        response = await model.ainvoke([
            HumanMessage(content=combined_prompt)
        ])
        
        # Save raw response to file to avoid encoding issues
        with open('avea_response.txt', 'w', encoding='utf-8') as f:
            f.write(response.content)
        
        print("RAW RESPONSE saved to avea_response.txt")
        # Try to display safely
        safe_content = response.content.encode('ascii', errors='replace').decode('ascii')
        print("SAFE VERSION (? = replaced characters):")
        print(safe_content[:500] + "..." if len(safe_content) > 500 else safe_content)
        print("\n" + "="*60)
        
        # Try to parse JSON
        content = response.content
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = content[json_start:json_end]
            parsed = json.loads(json_str)
            print("\nPARSED RESPONSE:")
            print(f"Classification: {parsed['classification']}")
            print(f"Confidence: {parsed['confidence']}")
            response_text = parsed.get('response_text', '')
            safe_text = response_text[:300].encode('ascii', errors='replace').decode('ascii')
            print(f"Response text: {safe_text}...")
            if parsed.get('other_entities'):
                safe_entities = [e.encode('ascii', errors='replace').decode('ascii') for e in parsed['other_entities']]
                print(f"Other entities mentioned: {safe_entities}")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_avea())