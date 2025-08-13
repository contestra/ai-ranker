"""
Show EXACTLY what gets sent to Gemini for DE + Grounded
"""

import asyncio
from app.services.evidence_pack_builder import evidence_pack_builder
from app.llm.langchain_adapter import LangChainAdapter

async def test_exact_messages():
    # Your exact prompt
    prompt_text = "List the top 10 longevity supplement companies"
    country = "DE"
    grounding_mode = "web"
    
    print("\n" + "="*80)
    print("TESTING EXACT MESSAGES FOR: DE + Grounded + Gemini")
    print("="*80)
    
    # Step 1: Build evidence pack
    evidence_pack = await evidence_pack_builder.build_evidence_pack(
        prompt_text,
        country,
        max_snippets=5,
        max_tokens=600
    )
    
    # Step 2: Prepare the full prompt (exactly as in prompt_tracking.py)
    if evidence_pack:
        if grounding_mode == "web":
            full_prompt = f"""{evidence_pack}

Based on the above information and your knowledge, please answer:

{prompt_text}"""
        else:
            full_prompt = f"""{evidence_pack}

Based on the above information and your training data:

{prompt_text}"""
        context_message = None  # Don't send as separate message
    else:
        # Fallback if no evidence pack
        if grounding_mode == "web":
            full_prompt = f"""Please use web search to answer this question accurately:

{prompt_text}"""
        else:
            full_prompt = f"""Based only on your training data (do not search the web):

{prompt_text}"""
        context_message = None
    
    # Step 3: Call Gemini (this will print debug info)
    adapter = LangChainAdapter()
    
    print("\nCalling Gemini with these exact parameters...")
    print("The debug output below shows EXACTLY what gets sent:")
    
    response = await adapter.analyze_with_gemini(
        full_prompt,  # The combined prompt with evidence
        grounding_mode == "web",  # True for grounded mode
        model_name="gemini-2.5-pro",
        temperature=0.0,
        seed=42,
        context=context_message  # None in this case
    )
    
    print("\n" + "="*80)
    print("RESPONSE PREVIEW:")
    print("="*80)
    print(response['content'][:500] + "..." if len(response['content']) > 500 else response['content'])

if __name__ == "__main__":
    asyncio.run(test_exact_messages())