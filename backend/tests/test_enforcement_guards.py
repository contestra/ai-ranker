# tests/test_enforcement_guards.py
"""
Guardrail tests for enforcement integrity
Ensures fail-closed semantics are maintained
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.llm.adapters.openai_adapter import run_openai_with_grounding

class _FakeClientNoSearch:
    """Returns a message but no web_search_call"""
    class responses:
        @staticmethod
        def create(**kwargs):
            return {"output":[
                {"type":"reasoning","content":[]},
                {"type":"message","content":[{"type":"output_text","text":"Some answer"}]}
            ]}

class _FakeClientWithSearch:
    """Returns both web_search_call and message"""
    class responses:
        @staticmethod
        def create(**kwargs):
            return {"output":[
                {"type":"web_search_call","status":"ok"},
                {"type":"message","content":[{"type":"output_text","text":"Answer with cite"}]}
            ]}

def test_required_soft_fails_when_no_search_gpt5():
    """REQUIRED mode on GPT-5 must fail when no search occurs"""
    res = run_openai_with_grounding(
        client=_FakeClientNoSearch(), model="gpt-5-o",
        mode="REQUIRED", prompt="VAT in DE?", system="", als="", strict_fail=True
    )
    assert res["tool_call_count"] == 0
    assert res["status"] == "failed"
    assert res["enforcement_mode"] == "soft"
    assert res.get("enforcement_passed") is False
    assert res["error_code"] == "no_tool_call_in_soft_required"
    print("[PASS] REQUIRED soft fails when no search (GPT-5)")

def test_required_hard_fails_when_no_search_non_gpt5():
    """REQUIRED mode on non-GPT-5 must fail when no search occurs"""
    res = run_openai_with_grounding(
        client=_FakeClientNoSearch(), model="gpt-4o",
        mode="REQUIRED", prompt="VAT in DE?", system="", als="", strict_fail=True
    )
    assert res["tool_call_count"] == 0
    assert res["status"] == "failed"
    assert res["enforcement_mode"] == "hard"
    assert res.get("enforcement_passed") is False
    assert res["error_code"] == "no_tool_call_in_required"
    print("[PASS] REQUIRED hard fails when no search (non-GPT-5)")

def test_required_passes_when_search_occurs():
    """REQUIRED mode passes when search occurs"""
    res = run_openai_with_grounding(
        client=_FakeClientWithSearch(), model="gpt-5-o",
        mode="REQUIRED", prompt="VAT in DE?", system="", als="", strict_fail=True
    )
    assert res["tool_call_count"] >= 1
    assert res["status"] == "ok"
    assert res.get("enforcement_passed") is True
    assert res["enforcement_mode"] == "soft"
    print("[PASS] REQUIRED passes when search occurs")

def test_preferred_passes_regardless():
    """PREFERRED mode should pass even without searches"""
    res = run_openai_with_grounding(
        client=_FakeClientNoSearch(), model="gpt-5",
        mode="PREFERRED", prompt="VAT?", system="", als=""
    )
    assert res["status"] == "ok"
    # PREFERRED doesn't have enforcement requirements
    assert res["enforcement_mode"] == "none"
    print("[PASS] PREFERRED passes regardless of search")

def test_ungrounded_fails_with_search():
    """UNGROUNDED mode must fail if search occurs"""
    res = run_openai_with_grounding(
        client=_FakeClientWithSearch(), model="gpt-5",
        mode="UNGROUNDED", prompt="VAT?", system="", als=""
    )
    assert res["tool_call_count"] == 1
    assert res["status"] == "failed"
    assert res.get("enforcement_passed") is False
    assert res["error_code"] == "tool_used_in_ungrounded"
    print("[PASS] UNGROUNDED fails when search occurs")

def test_ungrounded_passes_without_search():
    """UNGROUNDED mode passes when no search"""
    res = run_openai_with_grounding(
        client=_FakeClientNoSearch(), model="gpt-5",
        mode="UNGROUNDED", prompt="VAT?", system="", als=""
    )
    assert res["tool_call_count"] == 0
    assert res["status"] == "ok"
    assert res.get("enforcement_passed") is True
    print("[PASS] UNGROUNDED passes without search")

if __name__ == "__main__":
    print("Testing enforcement guards...")
    print("=" * 60)
    
    test_required_soft_fails_when_no_search_gpt5()
    test_required_hard_fails_when_no_search_non_gpt5()
    test_required_passes_when_search_occurs()
    test_preferred_passes_regardless()
    test_ungrounded_fails_with_search()
    test_ungrounded_passes_without_search()
    
    print("\n" + "=" * 60)
    print("All enforcement guard tests passed!")
    print("Fail-closed semantics verified!")