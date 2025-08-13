"""Mimic exactly what the API does to find the leak"""

import asyncio
from app.llm.langchain_adapter import LangChainAdapter
from app.services.als import als_service

async def test_mimic_api():
    # Mimic the API flow exactly
    country = "DE"  # This is what API receives
    
    print("\n" + "="*80)
    print("MIMICKING API FLOW EXACTLY")
    print("="*80)
    
    # Create new adapter (like API does now)
    adapter = LangChainAdapter()
    
    # Build ALS block (like API does)
    ambient_block = ""
    if country != "NONE":
        if country in ['DE', 'CH', 'US', 'GB', 'AE', 'SG', 'IT', 'FR']:
            try:
                ambient_block = als_service.build_als_block(country)
                print(f"\n1. Built Ambient Block for country='{country}'")
                print(f"   Block preview: {ambient_block[:100]}...")
            except Exception as e:
                print(f"Failed to build Ambient Block: {e}")
    
    # Prepare prompt (like API does)
    prompt_text = "What are the top 3 longevity supplements?"
    
    # Keep prompt naked, ambient block separate (like API does)
    full_prompt = prompt_text  # UNMODIFIED
    context_message = ambient_block  # Separate
    
    print(f"\n2. Prepared messages:")
    print(f"   Naked prompt: {full_prompt}")
    print(f"   Has context: {bool(context_message)}")
    
    # Call Gemini (like API does)
    print("\n3. Calling Gemini...")
    result = await adapter.analyze_with_gemini(
        full_prompt,
        use_grounding=False,
        model_name='gemini-2.5-pro',
        temperature=0.0,
        seed=42,
        context=context_message
    )
    
    response_text = result['content']
    
    print("\n4. RESPONSE (first 500 chars):")
    print("-"*40)
    print(response_text[:500])
    print("-"*40)
    
    # Check for leaks
    leak_indicators = ['DE', 'Germany', 'Deutschland', 'location context']
    found_leaks = []
    
    for indicator in leak_indicators:
        if indicator in response_text:
            found_leaks.append(indicator)
    
    if found_leaks:
        print(f"\n[LEAK DETECTED] Response contains: {found_leaks}")
    else:
        print("\n[OK] No leaks detected")
    
    # The key question: Why does this work but API doesn't?
    print("\n" + "="*80)
    print("KEY DIFFERENCE ANALYSIS:")
    print("="*80)
    print("This test uses country='DE' internally, just like the API")
    print("But does Gemini see 'DE' anywhere in the messages? Let's check...")
    
    # Check if DE appears in the ambient block
    if 'DE' in ambient_block:
        print("\n[!] 'DE' found in ambient block")
    else:
        print("\n[OK] 'DE' not in ambient block")
    
    # The difference might be in:
    # 1. HTTP headers from the API
    # 2. Langchain callbacks/tracers
    # 3. Database context
    # 4. Session state
    
    return response_text

if __name__ == "__main__":
    asyncio.run(test_mimic_api())