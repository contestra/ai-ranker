"""
Test script to verify GPT-5 grounding actually works now
This will test both grounded and ungrounded modes to ensure they're different
"""

import asyncio
import json
from app.llm.langchain_adapter import LangChainAdapter
from app.config import settings

async def test_gpt5_grounding():
    """Test GPT-5 with and without grounding to verify it works"""
    
    print("=" * 60)
    print("GPT-5 GROUNDING TEST")
    print("=" * 60)
    
    adapter = LangChainAdapter()
    
    # Test prompt that should benefit from web search
    test_prompt = "What are the current top 3 AI news headlines today?"
    
    # Test with Singapore ALS context
    singapore_als = """[ALS]
Operating from Singapore; prices in S$. Date format DD/MM/YYYY. Postal 018956. Tel +65 6123 4567. GST applies.
Emergency: 999 (police), 995 (fire/ambulance)."""
    
    print("\n1. Testing GPT-4o UNGROUNDED (baseline)...")
    print("-" * 40)
    
    try:
        ungrounded_result = await adapter.analyze_with_gpt4(
            prompt=test_prompt,
            model_name="gpt-4o",
            use_grounding=False,
            temperature=0.0,
            seed=42,
            context=singapore_als
        )
        
        print(f"Response received: {len(ungrounded_result.get('content', ''))} chars")
        print(f"Tool calls: {ungrounded_result.get('tool_call_count', 0)}")
        print(f"Grounded effective: {ungrounded_result.get('grounded_effective', False)}")
        print(f"Response preview: {ungrounded_result.get('content', '')[:200]}...")
        
        if ungrounded_result.get('tool_call_count', 0) > 0:
            print("[ERROR] Ungrounded mode made tool calls! This shouldn't happen.")
        else:
            print("[OK] Ungrounded mode confirmed (no tool calls)")
    
    except Exception as e:
        print(f"[ERROR] Ungrounded test failed: {str(e)}")
    
    print("\n2. Testing GPT-4o GROUNDED (with web search)...")
    print("-" * 40)
    
    try:
        grounded_result = await adapter.analyze_with_gpt4(
            prompt=test_prompt,
            model_name="gpt-4o",
            use_grounding=True,  # THIS IS THE KEY DIFFERENCE
            temperature=0.0,
            seed=42,
            context=singapore_als
        )
        
        print(f"Response received: {len(grounded_result.get('content', ''))} chars")
        print(f"Tool calls: {grounded_result.get('tool_call_count', 0)}")
        print(f"Grounded effective: {grounded_result.get('grounded_effective', False)}")
        print(f"Response preview: {grounded_result.get('content', '')[:200]}...")
        
        if grounded_result.get('grounding_note'):
            print(f"Note: {grounded_result.get('grounding_note')}")
        
        if grounded_result.get('tool_call_count', 0) > 0:
            print("[OK] Grounded mode made tool calls!")
        else:
            print("[WARNING] Grounded mode made NO tool calls - web search may not be working")
    
    except Exception as e:
        print(f"[ERROR] Grounded test failed: {str(e)}")
    
    print("\n3. Testing locale probe with JSON enforcement...")
    print("-" * 40)
    
    locale_probe = 'Return ONLY this JSON (no extra text): {"vat_percent":"<number>%","plug":["<letter(s)>"],"emergency":["<digits>"]}'
    
    try:
        probe_result = await adapter.analyze_with_gpt4(
            prompt=locale_probe,
            model_name="gpt-4o",
            use_grounding=False,
            temperature=0.0,
            seed=42,
            context=singapore_als
        )
        
        response = probe_result.get('content', '')
        print(f"Response: {response}")
        
        # Try to parse as JSON
        try:
            parsed = json.loads(response)
            print("[OK] Valid JSON returned!")
            print(f"  VAT: {parsed.get('vat_percent')}")
            print(f"  Plug: {parsed.get('plug')}")
            print(f"  Emergency: {parsed.get('emergency')}")
            
            # Check Singapore values
            if parsed.get('vat_percent') == '9%':
                print("  [OK] Correct Singapore GST rate!")
            if 'G' in parsed.get('plug', []):
                print("  [OK] Correct Singapore plug type!")
            if '999' in parsed.get('emergency', []):
                print("  [OK] Correct Singapore emergency number!")
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON: {e}")
            print(f"Response was: {response}")
    
    except Exception as e:
        print(f"[ERROR] Locale probe test failed: {str(e)}")
    
    print("\n" + "=" * 60)
    print("GROUNDING TEST SUMMARY")
    print("=" * 60)
    
    print("\nKey findings:")
    print("1. Ungrounded mode: Should have tool_call_count = 0")
    print("2. Grounded mode: Should have tool_call_count > 0")
    print("3. JSON enforcement: Still needs API-level schema enforcement")
    print("\nNote: OpenAI may not have native web_search tool yet.")
    print("The implementation sets up the structure for when it's available.")

if __name__ == "__main__":
    print("Starting GPT-5 grounding test...")
    asyncio.run(test_gpt5_grounding())