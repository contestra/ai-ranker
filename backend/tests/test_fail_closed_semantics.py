"""
Test fail-closed semantics for REQUIRED mode
Critical for measurement integrity
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.llm.adapters.openai_adapter import run_openai_with_grounding

class _FakeResp:
    def __init__(self, output, usage):
        self.output = output
        self.usage = usage

class _FakeClientNoSearch:
    """Fake client that returns a message but no web_search_call"""
    class responses:
        @staticmethod
        def create(**kwargs):
            # Returns message but no search
            output = [
                {"type": "reasoning", "content": []},
                {"type": "message", "content": [{"type": "output_text", "text": '{"vat": "0%"}'}]}
            ]
            usage = {
                "input_tokens": 100,
                "output_tokens": 200,
                "total_tokens": 300,
                "output_tokens_details": {"reasoning_tokens": 100}
            }
            return _FakeResp(output, usage)

def test_required_soft_fails_when_no_search_gpt5():
    """CRITICAL: REQUIRED mode must fail when no searches performed"""
    fake = _FakeClientNoSearch()
    res = run_openai_with_grounding(
        client=fake,
        model="gpt-5",  # GPT-5 uses soft-required
        mode="REQUIRED",
        prompt="What is the VAT rate in Germany?",
        system="",
        als="",
        strict_fail=True,  # Ensure fail-closed
    )
    
    # Verify critical invariants
    assert res["tool_call_count"] == 0, "Expected 0 tool calls"
    assert res["status"] == "failed", "REQUIRED with 0 searches must be failed"
    assert res["enforcement_mode"] == "soft", "GPT-5 should use soft enforcement"
    assert res["why_not_grounded"] == "tool_forcing_unsupported_on_gpt5"
    assert res["error_code"] == "no_tool_call_in_soft_required"
    assert res["soft_required"] == True
    assert res["text"] == '{"vat": "0%"}', "Should still have output text"
    
    print("[PASS] REQUIRED soft fails correctly when no search (GPT-5)")

def test_required_hard_fails_when_no_search_gpt4():
    """Non-GPT-5 models use hard-required and also fail"""
    fake = _FakeClientNoSearch()
    res = run_openai_with_grounding(
        client=fake,
        model="gpt-4",  # Non-GPT-5 uses hard-required
        mode="REQUIRED",
        prompt="What is the VAT rate in Germany?",
        system="",
        als="",
        strict_fail=True,
    )
    
    assert res["tool_call_count"] == 0
    assert res["status"] == "failed", "REQUIRED with 0 searches must be failed"
    assert res["enforcement_mode"] == "hard", "GPT-4 should use hard enforcement"
    assert res["error_code"] == "no_tool_call_in_required"
    assert res["soft_required"] == False
    
    print("[PASS] REQUIRED hard fails correctly when no search (GPT-4)")

def test_preferred_ok_when_no_search():
    """PREFERRED mode should be OK even with no searches"""
    fake = _FakeClientNoSearch()
    res = run_openai_with_grounding(
        client=fake,
        model="gpt-5",
        mode="PREFERRED",
        prompt="What is the VAT rate?",
        system="",
        als="",
    )
    
    assert res["tool_call_count"] == 0
    assert res["status"] == "ok", "PREFERRED with 0 searches should be OK"
    assert res["enforcement_mode"] == "none"
    assert res["error_code"] is None
    
    print("[PASS] PREFERRED ok when no search")

def test_ungrounded_fails_with_search():
    """UNGROUNDED mode must fail if searches occur"""
    
    class _FakeClientWithSearch:
        class responses:
            @staticmethod
            def create(**kwargs):
                output = [
                    {"type": "web_search_call", "status": "ok"},
                    {"type": "message", "content": [{"type": "output_text", "text": "answer"}]}
                ]
                usage = {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
                return _FakeResp(output, usage)
    
    fake = _FakeClientWithSearch()
    res = run_openai_with_grounding(
        client=fake,
        model="gpt-5",
        mode="UNGROUNDED",
        prompt="What is the VAT rate?",
        system="",
        als="",
    )
    
    assert res["tool_call_count"] == 1
    assert res["status"] == "failed", "UNGROUNDED with searches must fail"
    assert res["error_code"] == "tool_used_in_ungrounded"
    
    print("[PASS] UNGROUNDED fails when search occurs")

if __name__ == "__main__":
    print("Testing fail-closed semantics...")
    print("=" * 60)
    
    test_required_soft_fails_when_no_search_gpt5()
    test_required_hard_fails_when_no_search_gpt4()
    test_preferred_ok_when_no_search()
    test_ungrounded_fails_with_search()
    
    print("\n" + "=" * 60)
    print("All fail-closed semantic tests passed!")
    print("Measurement integrity preserved!")