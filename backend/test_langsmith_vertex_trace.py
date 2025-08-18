#!/usr/bin/env python3
"""
Test that Vertex grounding calls now appear in LangSmith.
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')

async def test_vertex_with_langsmith():
    """Test Vertex grounding with LangSmith tracing."""
    from app.llm.adapters.vertex_genai_adapter import VertexGenAIAdapter
    from app.llm.adapters.types import RunRequest, GroundingMode
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("\n" + "="*60)
    print(" TESTING VERTEX WITH LANGSMITH TRACING")
    print("="*60)
    print(f"LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")
    print(f"LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT')}")
    
    adapter = VertexGenAIAdapter(
        project="contestra-ai",
        location="europe-west4"
    )
    
    test_cases = [
        ("Test 1: No Grounding", GroundingMode.OFF, "What is AVEA?"),
        ("Test 2: Preferred Grounding", GroundingMode.PREFERRED, "What are the latest AI developments in 2025?"),
        ("Test 3: Enforced Grounding", GroundingMode.REQUIRED, "What is the current stock price of Tesla?"),
    ]
    
    for test_name, mode, prompt in test_cases:
        print(f"\n{test_name}")
        print(f"  Mode: {mode.value}")
        print(f"  Prompt: {prompt[:50]}...")
        
        try:
            req = RunRequest(
                run_id=f"test_{mode.value}",
                client_id="test_client",
                provider="vertex",
                model_name="gemini-2.5-pro",
                grounding_mode=mode,
                user_prompt=prompt,
                temperature=0.7,
                seed=42
            )
            
            result = adapter.run(req)
            
            print(f"  ✅ Success!")
            print(f"     Grounded: {result.grounded_effective}")
            print(f"     Citations: {len(result.citations)}")
            print(f"     Response preview: {result.json_text[:100] if result.json_text else 'No response'}...")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n" + "="*60)
    print(" CHECK LANGSMITH FOR:")
    print("   - Parent runs: vertex.grounded_run / vertex.ungrounded_run")
    print("   - Child runs: vertex.generate_content")
    print("   - Outputs with grounding metadata")
    print(f" URL: https://smith.langchain.com/o/{os.getenv('LANGCHAIN_PROJECT', 'ai-ranker')}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_vertex_with_langsmith())