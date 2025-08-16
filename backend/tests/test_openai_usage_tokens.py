"""
Test for OpenAI adapter usage token extraction and budget starvation detection
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.llm.adapters.openai_adapter import run_openai_with_grounding

class _FakeResp:
    def __init__(self, output, usage):
        self.output = output
        self.usage = usage

class _FakeClient:
    class responses:
        @staticmethod
        def create(**kwargs):
            # fake one reasoning item (no message) + usage with reasoning tokens
            output = [ {"type": "reasoning", "content": []} ]
            usage = {
                "input_tokens": 123,
                "output_tokens": 456,
                "total_tokens": 579,
                "output_tokens_details": {"reasoning_tokens": 111}
            }
            return _FakeResp(output, usage)

def test_usage_extraction_and_starvation():
    """Test that usage tokens are extracted correctly and starvation is detected"""
    fake = _FakeClient()
    res = run_openai_with_grounding(
        client=fake,
        model="gpt-5",
        mode="PREFERRED",
        prompt="VAT in SI?",
        system=None,
        als=None,
    )
    assert res["usage_input_tokens"] == 123
    assert res["usage_output_tokens"] == 456
    assert res["usage_total_tokens"] == 579
    assert res["usage_reasoning_tokens"] == 111
    assert res["budget_starved"] is True
    assert res["effective_max_output_tokens"] == 512  # auto-raised for GPT-5 + tools
    assert res["tool_call_count"] == 0
    assert res["grounded_effective"] is False
    
def test_no_starvation_with_message():
    """Test that starvation is not flagged when message exists"""
    
    class _FakeClientWithMessage:
        class responses:
            @staticmethod
            def create(**kwargs):
                # Both reasoning and message
                output = [
                    {"type": "reasoning", "content": []},
                    {"type": "message", "content": [{"type": "output_text", "text": "0% VAT"}]}
                ]
                usage = {
                    "input_tokens": 100,
                    "output_tokens": 200,
                    "total_tokens": 300,
                    "output_tokens_details": {"reasoning_tokens": 50}
                }
                return _FakeResp(output, usage)
    
    fake = _FakeClientWithMessage()
    res = run_openai_with_grounding(
        client=fake,
        model="gpt-5",
        mode="PREFERRED",
        prompt="VAT in US?",
        system=None,
        als=None,
    )
    assert res["usage_reasoning_tokens"] == 50
    assert res["budget_starved"] is False
    assert res["text"] == "0% VAT"
    assert res["effective_max_output_tokens"] == 512

def test_no_auto_raise_for_non_gpt5():
    """Test that non-GPT-5 models don't get auto-raised tokens"""
    
    class _FakeClientGPT4:
        class responses:
            @staticmethod
            def create(**kwargs):
                # Check that max_output_tokens wasn't set
                assert "max_output_tokens" not in kwargs
                output = [{"type": "message", "content": [{"type": "output_text", "text": "Answer"}]}]
                usage = {"input_tokens": 50, "output_tokens": 25, "total_tokens": 75}
                return _FakeResp(output, usage)
    
    fake = _FakeClientGPT4()
    res = run_openai_with_grounding(
        client=fake,
        model="gpt-4",  # Not GPT-5
        mode="PREFERRED",
        prompt="Test?",
        system=None,
        als=None,
    )
    assert res["effective_max_output_tokens"] is None  # Not auto-raised
    assert res["budget_starved"] is False

if __name__ == "__main__":
    test_usage_extraction_and_starvation()
    print("[PASS] Usage extraction and starvation detection test passed")
    
    test_no_starvation_with_message()
    print("[PASS] No false starvation detection test passed")
    
    test_no_auto_raise_for_non_gpt5()
    print("[PASS] No auto-raise for non-GPT-5 test passed")
    
    print("\nAll tests passed!")