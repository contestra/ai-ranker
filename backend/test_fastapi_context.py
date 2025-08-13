"""Test if FastAPI context is causing the leak"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
import asyncio
from app.llm.langchain_adapter import LangChainAdapter
from app.services.als import als_service

app = FastAPI()

@app.get("/test-direct")
async def test_direct():
    """Test calling Gemini directly from FastAPI endpoint"""
    
    # Exactly like the API does
    country = "DE"
    adapter = LangChainAdapter()
    
    # Build ALS
    ambient_block = als_service.build_als_block(country)
    
    # Call Gemini
    result = await adapter.analyze_with_gemini(
        'List the top 3 longevity supplements',
        use_grounding=False,
        model_name='gemini-2.5-pro',
        temperature=0.0,
        seed=42,
        context=ambient_block
    )
    
    response_text = result['content']
    
    # Check for leak
    has_leak = False
    if 'DE' in response_text or 'Germany' in response_text or 'location context' in response_text:
        has_leak = True
    
    return {
        "has_leak": has_leak,
        "response_preview": response_text[:300],
        "country_internal": country  # This is internal, not sent to model
    }

@app.get("/test-with-metadata")
async def test_with_metadata():
    """Test if adding metadata causes leak"""
    
    # Store country in various places
    country = "DE"
    
    # Add to locals
    local_country = country
    
    # Create adapter
    adapter = LangChainAdapter()
    
    # Build ALS
    ambient_block = als_service.build_als_block(local_country)
    
    # Call with local variable
    result = await adapter.analyze_with_gemini(
        'List the top 3 longevity supplements',
        use_grounding=False,
        model_name='gemini-2.5-pro',
        temperature=0.0,
        seed=42,
        context=ambient_block
    )
    
    response_text = result['content']
    
    # Check for leak
    has_leak = False
    if 'DE' in response_text or 'Germany' in response_text or 'location context' in response_text:
        has_leak = True
    
    return {
        "has_leak": has_leak,
        "response_preview": response_text[:300],
        "metadata": {"country": country}  # Return metadata in response
    }

if __name__ == "__main__":
    client = TestClient(app)
    
    print("\n" + "="*80)
    print("TEST 1: Direct from FastAPI endpoint")
    print("="*80)
    
    response1 = client.get("/test-direct")
    data1 = response1.json()
    
    if data1["has_leak"]:
        print("[LEAK] FastAPI direct endpoint has leak!")
    else:
        print("[OK] FastAPI direct endpoint - no leak")
    
    print(f"Response: {data1['response_preview'][:100]}...")
    
    print("\n" + "="*80)
    print("TEST 2: With metadata in response")
    print("="*80)
    
    response2 = client.get("/test-with-metadata")
    data2 = response2.json()
    
    if data2["has_leak"]:
        print("[LEAK] FastAPI with metadata has leak!")
    else:
        print("[OK] FastAPI with metadata - no leak")
    
    print(f"Response: {data2['response_preview'][:100]}...")
    print(f"Metadata returned: {data2['metadata']}")
    
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    
    if not data1["has_leak"] and not data2["has_leak"]:
        print("FastAPI itself is NOT causing the leak")
        print("The issue must be in the prompt_tracking.py specific logic")
    else:
        print("FastAPI context IS causing the leak!")