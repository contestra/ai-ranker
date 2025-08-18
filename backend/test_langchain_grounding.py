#!/usr/bin/env python3
"""
Test the actual LangChain integration with canonical grounding modes.
This will show up in LangSmith and test the real execution path.
"""
import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure UTF-8 for Windows
if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')

async def test_langchain_grounding():
    """Test grounding through the actual LangChain adapter."""
    from app.llm.langchain_adapter import LangChainAdapter
    from app.services.grounding_enforcement import normalize_grounding_mode
    
    adapter = LangChainAdapter()
    
    test_cases = [
        ("not_grounded", "What is AVEA?", False),  # Should NOT use grounding
        ("preferred", "What are the latest AI developments in 2025?", True),  # Should use grounding
        ("enforced", "What is the current stock price of Tesla?", True),  # Must use grounding
    ]
    
    print("\n" + "="*60)
    print(" TESTING LANGCHAIN GROUNDING INTEGRATION")
    print("="*60)
    
    for mode, prompt, expect_grounding in test_cases:
        canonical_mode = normalize_grounding_mode(mode)
        print(f"\n[TEST] Mode: {canonical_mode}")
        print(f"       Prompt: {prompt}")
        print(f"       Expect grounding: {expect_grounding}")
        
        try:
            # Determine if we should use grounding based on canonical mode
            use_grounding = canonical_mode in ["preferred", "enforced"]
            
            # Test with Gemini (Vertex)
            print("\n  Testing with Gemini...")
            result = await adapter.analyze_with_gemini(
                prompt=prompt,
                use_grounding=use_grounding,
                model_name="gemini-2.5-pro",
                temperature=0.7,
                seed=42
            )
            
            # Check results
            grounded = result.get("grounded_effective", False) or result.get("grounded", False)
            content = result.get("content", "")[:100]
            
            print(f"    Grounded: {grounded}")
            print(f"    Response preview: {content}...")
            
            if expect_grounding and not grounded and canonical_mode == "enforced":
                print(f"    ⚠️ WARNING: Grounding was enforced but didn't occur!")
            elif grounded == expect_grounding or canonical_mode == "preferred":
                print(f"    ✅ PASS: Grounding behavior as expected")
            else:
                print(f"    ❌ FAIL: Expected grounding={expect_grounding}, got {grounded}")
                
        except Exception as e:
            print(f"    ❌ ERROR: {e}")
    
    print("\n" + "="*60)
    print(" This should now appear in your LangSmith interface!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_langchain_grounding())