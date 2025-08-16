import types
from app.llm.adapters.openai_adapter import run_openai_with_grounding

class _FakeClient:
    def __init__(self, outputs):
        self._outputs = outputs
    class _RespObj:
        def __init__(self, output):
            self.output = output
    class responses:
        def __init__(self, parent):
            self.parent = parent
        def create(self, model, input, tools=None, tool_choice=None, **kwargs):
            # Accept any additional kwargs (seed, temperature, etc)
            return _FakeClient._RespObj(self.parent._outputs)

def _msg(text):  # minimal message block
    return {"type": "message", "content": [{"type": "output_text", "text": text}]}

def _search_call():
    return {"type": "web_search_call", "status": "ok"}

def test_required_soft_required_fails_when_no_search():
    fake = _FakeClient(outputs=[_msg("foo")])
    fake.responses = fake.responses(fake)
    res = run_openai_with_grounding(fake, model="gpt-5", mode="REQUIRED", prompt="VAT in SI?")
    assert res["soft_required"] is True
    assert res["tool_call_count"] == 0
    assert res["status"] == "failed"
    assert res["why_not_grounded"] == "tool_forcing_unsupported_on_gpt5"

def test_required_soft_required_passes_when_search():
    fake = _FakeClient(outputs=[_search_call(), _msg("bar")])
    fake.responses = fake.responses(fake)
    res = run_openai_with_grounding(fake, model="gpt-5", mode="REQUIRED", prompt="VAT in SI?")
    assert res["soft_required"] is True
    assert res["tool_call_count"] == 1
    assert res["status"] == "ok"
    assert res["grounded_effective"] is True

def test_required_strict_on_gpt4o():
    fake = _FakeClient(outputs=[_msg("baz")])
    fake.responses = fake.responses(fake)
    res = run_openai_with_grounding(fake, model="gpt-4o", mode="REQUIRED", prompt="VAT in SI?")
    assert res["soft_required"] is False
    assert res["tool_call_count"] == 0
    assert res["status"] == "failed"
    assert res["why_not_grounded"] == "no_tool_call_in_required"

def test_preferred_mode():
    fake = _FakeClient(outputs=[_msg("qux")])
    fake.responses = fake.responses(fake)
    res = run_openai_with_grounding(fake, model="gpt-5", mode="PREFERRED", prompt="VAT in SI?")
    assert res["soft_required"] is False
    assert res["tool_call_count"] == 0
    assert res["status"] == "ok"  # PREFERRED doesn't fail on no search
    assert res["grounded_effective"] is False
    assert res["enforcement_mode"] == "none"
    assert res["enforcement_passed"] is True

def test_tool_error_not_counted():
    """Test that web_search_call with error status is not counted"""
    error_call = {"type": "web_search_call", "status": "error"}
    fake = _FakeClient(outputs=[error_call, _msg("foo")])
    fake.responses = fake.responses(fake)
    res = run_openai_with_grounding(fake, model="gpt-5", mode="REQUIRED", prompt="VAT in SI?")
    assert res["tool_call_count"] == 0  # Error calls not counted
    assert res["status"] == "failed"  # No successful searches
    assert res["enforcement_passed"] is False

def test_gpt5_variant_detection():
    """Test that various GPT-5 model names are detected"""
    for model_name in ["gpt-5", "gpt-5o", "gpt-5-mini", "gpt-5.1", "GPT-5"]:
        fake = _FakeClient(outputs=[_msg("test")])
        fake.responses = fake.responses(fake)
        res = run_openai_with_grounding(fake, model=model_name, mode="REQUIRED", prompt="test")
        assert res["soft_required"] is True, f"Failed to detect {model_name} as GPT-5"
        assert res["enforcement_mode"] == "soft"

def test_non_gpt5_hard_enforcement():
    """Test that non-GPT-5 models use hard enforcement"""
    for model_name in ["gpt-4o", "gpt-4", "claude-3"]:
        fake = _FakeClient(outputs=[_msg("test")])
        fake.responses = fake.responses(fake)
        res = run_openai_with_grounding(fake, model=model_name, mode="REQUIRED", prompt="test")
        assert res["soft_required"] is False, f"{model_name} should not be soft-required"
        assert res["enforcement_mode"] == "hard"