"""Test if Langchain callbacks are causing the leak"""

import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from app.config import settings
from app.services.als import als_service

async def test_without_callbacks():
    print("\n" + "="*80)
    print("TEST 1: WITH CALLBACKS (normal)")
    print("="*80)
    
    # Normal adapter with callbacks
    from app.llm.langchain_adapter import LangChainAdapter
    adapter = LangChainAdapter()
    
    ambient_block = als_service.build_als_block('DE')
    result = await adapter.analyze_with_gemini(
        'List the top 3 longevity supplements',
        use_grounding=False,
        model_name='gemini-2.5-pro',
        temperature=0.0,
        seed=42,
        context=ambient_block
    )
    
    response_with_callbacks = result['content']
    
    if 'DE' in response_with_callbacks or 'Germany' in response_with_callbacks:
        print("[LEAK] WITH callbacks: DE/Germany found in response")
    else:
        print("[OK] WITH callbacks: No leak")
    
    print("\n" + "="*80)
    print("TEST 2: WITHOUT CALLBACKS (direct)")
    print("="*80)
    
    # Direct model without callbacks
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0.0,
        google_api_key=settings.google_api_key
    )
    
    messages = []
    
    # Same system prompt
    system_prompt = """Answer the user's question directly and naturally.
You may use any ambient context provided only to infer locale and set defaults (language variants, units, currency, regulatory framing).
Do not mention, cite, or acknowledge the ambient context or any location inference.
Do not state or imply country/region/city names unless the user explicitly asks.
Do not preface with anything about training data or location. Produce the answer only."""
    
    messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=ambient_block))
    messages.append(HumanMessage(content='List the top 3 longevity supplements'))
    
    # Call WITHOUT callbacks
    response = await model.ainvoke(
        messages,
        config={"callbacks": []}  # Empty callbacks
    )
    
    response_without_callbacks = response.content
    
    if 'DE' in response_without_callbacks or 'Germany' in response_without_callbacks:
        print("[LEAK] WITHOUT callbacks: DE/Germany found in response")
    else:
        print("[OK] WITHOUT callbacks: No leak")
    
    print("\n" + "="*80)
    print("COMPARISON")
    print("="*80)
    
    print("\nWith callbacks (first 200 chars):")
    print(response_with_callbacks[:200])
    
    print("\nWithout callbacks (first 200 chars):")
    print(response_without_callbacks[:200])

if __name__ == "__main__":
    asyncio.run(test_without_callbacks())