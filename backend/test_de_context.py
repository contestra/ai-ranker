"""
Test to show exactly what context is sent for Germany
"""

import asyncio
from app.services.evidence_pack_builder import evidence_pack_builder

async def test_de_context():
    # Your exact prompt
    prompt = "List the top 10 longevity supplement companies"
    
    print("="*60)
    print("GERMANY (DE) CONTEXT TEST")
    print("="*60)
    
    print(f"\nOriginal Prompt: {prompt}")
    print("\n" + "-"*60)
    
    # Build evidence pack for Germany
    evidence_pack = await evidence_pack_builder.build_evidence_pack(
        prompt,
        "DE",
        max_snippets=5,
        max_tokens=600
    )
    
    if evidence_pack:
        print("\nEvidence Pack from Exa (Real German Search Results):")
        print("-"*60)
        print(evidence_pack)
        print("-"*60)
        
        # This is what gets sent when grounding_mode="web"
        full_prompt_grounded = f"""{evidence_pack}

Based on the above information and your knowledge, please answer:

{prompt}"""
        
        print("\nFULL PROMPT SENT TO GEMINI (Grounded Mode):")
        print("="*60)
        print(full_prompt_grounded)
        print("="*60)
        
        print("\nKEY POINTS:")
        print("- The model receives real German search results from Exa")
        print("- It's asked to consider this information when answering")
        print("- The model naturally infers German context from the evidence")
        print("- Notice how it mentioned MoleQlar and Purovitalis (EU companies) in response!")
    else:
        print("No evidence pack generated")

if __name__ == "__main__":
    asyncio.run(test_de_context())