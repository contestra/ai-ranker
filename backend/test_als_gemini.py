"""Test ALS with Gemini - verify German locale inference"""
import asyncio
from app.llm.langchain_adapter import LangChainAdapter
from app.services.als.als_builder import ALSBuilder

async def test_als_gemini():
    adapter = LangChainAdapter()
    als_builder = ALSBuilder()
    
    # Generate German ALS block
    als_block = als_builder.build_als_block("DE", include_weather=True, randomize=False)
    
    print("=" * 60)
    print("TESTING ALS WITH GEMINI")
    print("=" * 60)
    print("\nGerman ALS Block:")
    print("-" * 40)
    print(als_block)
    print("-" * 40)
    print(f"Block length: {len(als_block)} chars\n")
    
    # Test probes for locale inference
    probes = [
        "What is the standard VAT rate?",
        "What type of electrical plug is used?",
        "What is the emergency phone number?"
    ]
    
    print("Testing locale inference with Gemini 2.5 Pro...")
    print("=" * 60)
    
    for i, probe in enumerate(probes, 1):
        print(f"\nProbe {i}: {probe}")
        print("-" * 40)
        
        # Call Gemini with ALS context
        result = await adapter.analyze_with_gemini(
            prompt=probe,  # Naked prompt
            use_grounding=False,
            model_name="gemini-2.5-pro",
            temperature=0.0,
            seed=42,
            context=als_block  # German ALS as separate context
        )
        
        response = result.get("content", "")
        
        # Check for German-specific answers
        if i == 1:  # VAT probe
            if "19" in response:
                print("[PASS] Correctly identified German VAT rate (19%)")
            else:
                print("[FAIL] Did not identify German VAT rate")
                
        elif i == 2:  # Plug probe
            if any(term in response.lower() for term in ["type f", "schuko", "europlug", "cee 7"]):
                print("[PASS] Correctly identified German plug type")
            else:
                print("[FAIL] Did not identify German plug type")
                
        elif i == 3:  # Emergency probe
            if "112" in response:
                print("[PASS] Correctly identified European emergency number")
                if "110" in response:
                    print("  BONUS: Also mentioned German police number")
            else:
                print("[FAIL] Did not identify emergency number")
        
        print(f"\nResponse: {response[:200]}...")
        
    print("\n" + "=" * 60)
    print("ALS TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_als_gemini())