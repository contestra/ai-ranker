"""
Test what evidence pack is actually being generated
"""

import asyncio
from app.services.evidence_pack_builder import evidence_pack_builder

async def test_evidence_pack():
    # Test for Switzerland
    print("=" * 60)
    print("SWITZERLAND EVIDENCE PACK:")
    print("=" * 60)
    
    ch_pack = await evidence_pack_builder.build_evidence_pack(
        "What are the most popular longevity supplements?",
        "CH",
        max_snippets=3,
        max_tokens=600
    )
    print(ch_pack)
    
    print("\n" + "=" * 60)
    print("US EVIDENCE PACK:")
    print("=" * 60)
    
    us_pack = await evidence_pack_builder.build_evidence_pack(
        "What are the most popular longevity supplements?",
        "US",
        max_snippets=3,
        max_tokens=600
    )
    print(us_pack)

if __name__ == "__main__":
    asyncio.run(test_evidence_pack())