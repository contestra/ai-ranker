"""
Show the ACTUAL content sent to Gemini - no placeholders!
"""

import asyncio
from app.services.evidence_pack_builder import evidence_pack_builder

async def show_real_content():
    # Your exact prompt
    prompt_text = "List the top 10 longevity supplement companies"
    
    print("\n" + "="*80)
    print("FETCHING REAL CONTENT FROM EXA FOR GERMANY")
    print("="*80)
    
    # Get the ACTUAL evidence pack from Exa
    evidence_pack = await evidence_pack_builder.build_evidence_pack(
        prompt_text,
        "DE",
        max_snippets=5,
        max_tokens=600
    )
    
    print("\nACTUAL EVIDENCE PACK CONTENT:")
    print("-"*80)
    print(evidence_pack)
    print("-"*80)
    
    # Build the EXACT message that gets sent
    if evidence_pack:
        full_message = f"""{evidence_pack}

Based on the above information and your knowledge, please answer:

{prompt_text}"""
    
        print("\n" + "="*80)
        print("THIS IS THE EXACT, COMPLETE MESSAGE SENT TO GEMINI:")
        print("="*80)
        print(full_message)
        print("="*80)
        
        print("\nNOTE: This is sent as a single HumanMessage object to Gemini")
        print("No other messages or context - just this one message!")

if __name__ == "__main__":
    asyncio.run(show_real_content())