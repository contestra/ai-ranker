"""
Test what query is being built for evidence packs
"""

import asyncio
from app.api.prompt_tracking import *

async def test_query_building():
    # Simulate what happens when running a prompt test
    
    # Example template prompt
    template_prompt = "Where can I buy {brand_name} products?"
    brand_name = "AVEA"
    
    print("="*60)
    print("TESTING QUERY BUILDING FOR EVIDENCE PACKS")
    print("="*60)
    
    print(f"\nOriginal Template: {template_prompt}")
    print(f"Brand Name: {brand_name}")
    
    # Fill in the brand name
    prompt_text = template_prompt.replace("{brand_name}", brand_name)
    print(f"\nFilled Prompt: {prompt_text}")
    
    # Now build generic query (as done in prompt_tracking.py)
    generic_query = prompt_text
    
    # Remove brand name and placeholders
    if "{brand_name}" in generic_query:
        generic_query = generic_query.replace("{brand_name}", "")
    else:
        generic_query = generic_query.replace(brand_name, "")
    
    print(f"\nAfter removing brand: '{generic_query}'")
    
    # Apply replacements
    generic_replacements = [
        ("Tell me about ", "Tell me about longevity supplements"),
        ("Where can I buy  products", "Where can I buy longevity supplements"),
        ("Where can I buy ", "Where can I buy longevity supplements"),
        ("List top 10 brands including ", "List top 10 longevity supplement brands"),
        ("What is ", "What are longevity supplements"),
        ("How much does  cost", "How much do longevity supplements cost"),
        ("Is  worth it", "Are longevity supplements worth it"),
    ]
    
    for pattern, replacement in generic_replacements:
        if pattern in generic_query:
            print(f"\nMatched pattern: '{pattern}'")
            generic_query = generic_query.replace(pattern, replacement)
            print(f"Replaced with: '{generic_query}'")
            break
    
    # Check if we need fallback
    if generic_query.strip() == prompt_text.strip() or not generic_query.strip():
        print("\nUsing fallback query")
        generic_query = "longevity supplements anti-aging products"
    
    print(f"\nFINAL QUERY FOR EVIDENCE PACK: '{generic_query}'")
    
    # Test a few more examples
    print("\n" + "="*60)
    print("MORE EXAMPLES:")
    print("="*60)
    
    test_cases = [
        "List the top 10 longevity supplement companies",
        "Tell me about {brand_name}",
        "What is {brand_name}?",
        "How much does {brand_name} cost?",
        "Is {brand_name} worth buying?"
    ]
    
    for test in test_cases:
        filled = test.replace("{brand_name}", brand_name)
        generic = filled.replace(brand_name, "")
        
        # Apply replacements
        for pattern, replacement in generic_replacements:
            if pattern in generic:
                generic = generic.replace(pattern, replacement)
                break
        
        if generic.strip() == filled.strip() or not generic.strip():
            generic = "longevity supplements anti-aging products"
            
        print(f"\nOriginal: {test}")
        print(f"Generic:  {generic}")

if __name__ == "__main__":
    asyncio.run(test_query_building())