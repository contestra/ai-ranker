"""Test ALS with GPT-5 - verify German locale inference"""
import asyncio
from app.llm.langchain_adapter import LangChainAdapter
from app.services.als.als_builder import ALSBuilder

async def test_als_gpt5():
    adapter = LangChainAdapter()
    als_builder = ALSBuilder()
    
    # Generate German ALS block
    als_block = als_builder.build_als_block("DE", include_weather=True, randomize=False)
    
    print("=" * 60)
    print("TESTING ALS WITH GPT-5")
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
    
    print("Testing locale inference with GPT-5...")
    print("Note: GPT-5 is currently returning empty responses from OpenAI API")
    print("=" * 60)
    
    for i, probe in enumerate(probes, 1):
        print(f"\nProbe {i}: {probe}")
        print("-" * 40)
        
        # Call GPT-5 with ALS context
        result = await adapter.analyze_with_gpt4(
            prompt=probe,  # Naked prompt
            model_name="gpt-5",
            temperature=1.0,  # GPT-5 requires temperature=1.0
            seed=42,
            context=als_block  # German ALS as separate context
        )
        
        response = result.get("content", "")
        
        # Check if response is empty or error
        if not response or response.startswith("[ERROR]"):
            print("[INFO] GPT-5 returned empty/error response (expected behavior)")
            print(f"Response: {response if response else '(empty)'}")
            continue
        
        # Check for German-specific answers (if GPT-5 starts working)
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
        
        print(f"\nResponse: {response[:200] if response else '(empty)'}...")
    
    # Also test with GPT-4o as fallback
    print("\n" + "=" * 60)
    print("TESTING WITH GPT-4o AS FALLBACK")
    print("=" * 60)
    
    print("\nTesting first probe with GPT-4o...")
    result = await adapter.analyze_with_gpt4(
        prompt=probes[0],  # VAT rate probe
        model_name="gpt-4o",
        temperature=0.3,
        seed=42,
        context=als_block
    )
    
    response = result.get("content", "")
    if response and not response.startswith("[ERROR]"):
        if "19" in response:
            print("[PASS] GPT-4o correctly identified German VAT rate (19%)")
        else:
            print("[FAIL] GPT-4o did not identify German VAT rate")
        print(f"\nResponse: {response[:200]}...")
    else:
        print(f"[ERROR] GPT-4o also returned empty/error: {response if response else '(empty)'}")
        
    print("\n" + "=" * 60)
    print("ALS TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_als_gpt5())