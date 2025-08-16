import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.llm.adapters.openai_adapter import run_openai_with_grounding

class MockClient:
    class responses:
        @staticmethod
        def create(**kwargs):
            return {"output": [{"type": "message", "content": [{"type": "output_text", "text": "No VAT"}]}], "usage": {"input_tokens": 10, "output_tokens": 20}}

result = run_openai_with_grounding(client=MockClient(), model="gpt-5-o", mode="REQUIRED", prompt="What?", strict_fail=True)
print(f"Status: {result['status']}, Enforcement: {result['enforcement_passed']}, Error: {result.get('error_code')}")
assert result['status'] == 'failed' and result['enforcement_passed'] is False
print("✅ Fail-closed semantics verified!")
