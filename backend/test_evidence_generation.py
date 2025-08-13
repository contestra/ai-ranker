"""
Test if evidence packs are being generated properly in the API flow
"""

import asyncio
from app.services.evidence_pack_builder import evidence_pack_builder

async def test_evidence():
    # Test with the exact prompt being used
    prompt = "What are the top 3 longevity supplements?"
    
    for country in ['CH', 'US']:
        print(f"\n{'='*60}")
        print(f"COUNTRY: {country}")
        print(f"{'='*60}")
        
        evidence = await evidence_pack_builder.build_evidence_pack(
            prompt,
            country,
            max_snippets=5,
            max_tokens=600
        )
        
        if evidence:
            print("Evidence pack generated:")
            print(evidence)
        else:
            print("NO EVIDENCE PACK GENERATED!")

if __name__ == "__main__":
    asyncio.run(test_evidence())