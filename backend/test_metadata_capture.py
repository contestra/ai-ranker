"""Test script to verify Gemini metadata capture (modelVersion and responseId)"""
import asyncio
import json
from app.llm.langchain_adapter import LangChainAdapter

async def test_metadata_capture():
    """Test that we properly capture modelVersion and responseId from Gemini"""
    adapter = LangChainAdapter()
    
    print("Testing Gemini metadata capture...")
    print("=" * 80)
    
    # Test 1: Direct generate method with Gemini
    print("\n1. Testing generate() method with Gemini:")
    result = await adapter.generate(
        vendor="google",
        prompt="What is 2+2?",
        temperature=0.0,
        seed=42
    )
    
    print(f"   Text response: {result.get('text', 'NO TEXT')}")
    print(f"   System fingerprint: {result.get('system_fingerprint', 'NOT CAPTURED')}")
    print(f"   Fingerprint type: {result.get('fingerprint_type', 'NOT SET')}")
    print(f"   Metadata: {json.dumps(result.get('metadata', {}), indent=2)}")
    print(f"   Raw response_metadata keys: {list(result.get('raw', {}).keys())}")
    if result.get('raw'):
        print(f"   Raw response_metadata: {json.dumps(result.get('raw'), indent=2)[:500]}...")
    
    # Test 2: analyze_with_gemini method
    print("\n2. Testing analyze_with_gemini() method:")
    result2 = await adapter.analyze_with_gemini(
        prompt="What is the capital of France?",
        model_name="gemini-2.5-pro",
        temperature=0.0,
        seed=123
    )
    
    print(f"   Content: {result2.get('content', 'NO CONTENT')[:50]}...")
    print(f"   System fingerprint: {result2.get('system_fingerprint', 'NOT CAPTURED')}")
    print(f"   Metadata: {json.dumps(result2.get('metadata', {}), indent=2)}")
    
    # Test 3: analyze_with_gpt4 method for comparison
    print("\n3. Testing analyze_with_gpt4() method (for comparison):")
    result3 = await adapter.analyze_with_gpt4(
        prompt="What is 3+3?",
        model_name="gpt-4o",
        temperature=0.0,
        seed=456
    )
    
    print(f"   Content: {result3.get('content', 'NO CONTENT')[:50]}...")
    print(f"   System fingerprint: {result3.get('system_fingerprint', 'NOT CAPTURED')}")
    print(f"   Metadata: {json.dumps(result3.get('metadata', {}), indent=2)}")
    
    print("\n" + "=" * 80)
    print("Metadata capture test complete!")
    
    # Summary (using ASCII characters for Windows compatibility)
    print("\nSUMMARY:")
    if result.get('system_fingerprint'):
        print("[OK] Gemini modelVersion captured in generate()")
    else:
        print("[FAIL] Gemini modelVersion NOT captured in generate()")
        
    if result2.get('system_fingerprint'):
        print("[OK] Gemini modelVersion captured in analyze_with_gemini()")
    else:
        print("[FAIL] Gemini modelVersion NOT captured in analyze_with_gemini()")
        
    if result3.get('system_fingerprint'):
        print("[OK] OpenAI system_fingerprint captured in analyze_with_gpt4()")
    else:
        print("[FAIL] OpenAI system_fingerprint NOT captured in analyze_with_gpt4()")

if __name__ == "__main__":
    asyncio.run(test_metadata_capture())