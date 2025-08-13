"""Test script to debug where 'DE' is leaking to Gemini"""

import asyncio
from app.llm.langchain_adapter import LangChainAdapter
from app.services.als import als_service

async def test_de_leak():
    # Build the Ambient Block for Germany
    ambient_block = als_service.build_als_block('DE')
    
    print("\n" + "="*80)
    print("TEST: Checking for 'DE' leak in Gemini responses")
    print("="*80)
    
    print("\n1. AMBIENT BLOCK CONTENT:")
    print("-"*40)
    print(repr(ambient_block))
    print("-"*40)
    
    # Check if "DE" appears anywhere in the ambient block
    if "DE" in ambient_block or "de" in ambient_block.lower().split():
        print("\n[WARNING] Found potential 'DE' in ambient block!")
        for line in ambient_block.split('\n'):
            if 'DE' in line or 'de' in line.lower().split():
                print(f"   Line with potential leak: {repr(line)}")
    else:
        print("\n[OK] No 'DE' found in ambient block")
    
    # Test with Gemini
    adapter = LangChainAdapter()
    
    print("\n2. SENDING TO GEMINI...")
    print("-"*40)
    
    result = await adapter.analyze_with_gemini(
        'List the top 10 longevity supplement companies',
        use_grounding=False,
        model_name='gemini-2.5-pro',
        temperature=0.0,
        seed=42,
        context=ambient_block
    )
    
    print("\n3. GEMINI RESPONSE:")
    print("-"*40)
    response_text = result['content']
    print(response_text[:500])
    print("-"*40)
    
    # Check if response mentions DE or Germany explicitly
    leak_indicators = ['DE', 'Germany', 'Deutschland', 'German', 'location context']
    found_leaks = []
    
    for indicator in leak_indicators:
        if indicator in response_text:
            found_leaks.append(indicator)
    
    if found_leaks:
        print(f"\n[LEAK DETECTED] Response contains: {found_leaks}")
        # Show the sentences containing the leak
        sentences = response_text.split('.')
        for sentence in sentences[:10]:  # Check first 10 sentences
            for leak in found_leaks:
                if leak in sentence:
                    print(f"\n   Leaking sentence: {sentence.strip()}")
                    break
    else:
        print("\n[OK] No obvious leaks detected in response")
    
    return response_text

if __name__ == "__main__":
    asyncio.run(test_de_leak())