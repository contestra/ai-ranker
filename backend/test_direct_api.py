"""
Test the API directly to see what's happening with evidence packs
"""

import asyncio
from app.services.evidence_pack_builder import evidence_pack_builder
from app.llm.langchain_adapter import LangChainAdapter

async def test_direct():
    # Initialize adapter
    adapter = LangChainAdapter()
    
    # Test prompt
    base_prompt = "What are the top 3 longevity supplements?"
    
    print("=" * 60)
    print("TEST 1: BASE MODEL (No evidence)")
    print("=" * 60)
    
    # Base model - no evidence
    response = await adapter.analyze_with_gemini(
        base_prompt,
        use_grounding=False,
        temperature=0.0,
        seed=42,
        context=None
    )
    
    print("Response preview:")
    print(response['content'][:300])
    
    print("\n" + "=" * 60)
    print("TEST 2: SWITZERLAND (With evidence pack)")
    print("=" * 60)
    
    # Get Swiss evidence pack
    ch_evidence = await evidence_pack_builder.build_evidence_pack(
        base_prompt,
        "CH",
        max_snippets=3,
        max_tokens=600
    )
    
    print("Evidence pack:")
    print(ch_evidence)
    print("\nSending to model...")
    
    # Test with evidence as context
    response = await adapter.analyze_with_gemini(
        base_prompt,
        use_grounding=False,
        temperature=0.0,
        seed=42,
        context=ch_evidence
    )
    
    print("\nResponse preview:")
    print(response['content'][:300])
    
    # Check for location markers
    if 'swiss' in response['content'].lower() or 'chf' in response['content'].lower():
        print("\n[SUCCESS] Location inference detected!")
    else:
        print("\n[FAIL] No location inference")
    
    print("\n" + "=" * 60)
    print("TEST 3: INTEGRATED PROMPT (Evidence in prompt)")
    print("=" * 60)
    
    # Test with evidence integrated into prompt
    integrated_prompt = f"""{ch_evidence}

Based on the above information and your training data:

{base_prompt}"""
    
    print("Integrated prompt:")
    print(integrated_prompt[:300])
    print("\nSending to model...")
    
    response = await adapter.analyze_with_gemini(
        integrated_prompt,
        use_grounding=False,
        temperature=0.0,
        seed=42,
        context=None  # No separate context
    )
    
    print("\nResponse preview:")
    print(response['content'][:300])
    
    # Check for location markers
    if 'swiss' in response['content'].lower() or 'chf' in response['content'].lower():
        print("\n[SUCCESS] Location inference detected!")
    else:
        print("\n[FAIL] No location inference")

if __name__ == "__main__":
    asyncio.run(test_direct())