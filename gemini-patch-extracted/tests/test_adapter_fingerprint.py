import pytest
from adapter_fingerprint import extract_model_fingerprint, build_run_record


def test_openai_fingerprint_basic():
    md = {"system_fingerprint": "fp-abc123", "id": "chatcmpl-xyz"}
    fp = extract_model_fingerprint("openai", md)
    assert fp.fingerprint == "fp-abc123"
    assert fp.fingerprint_type == "openai.system_fingerprint"
    # Extras include an OpenAI response id (parity with Gemini responseId)
    assert fp.extras.get("openai_response_id") == "chatcmpl-xyz"


def test_gemini_fingerprint_modelVersion_and_responseId():
    md = {"modelVersion": "2025-07-31_00_RC04", "responseId": "resp-123"}
    fp = extract_model_fingerprint("gemini", md)
    assert fp.fingerprint == "2025-07-31_00_RC04"
    assert fp.fingerprint_type == "gemini.modelVersion"
    assert fp.extras["gemini_model_version"] == "2025-07-31_00_RC04"
    assert fp.extras["gemini_response_id"] == "resp-123"


def test_gemini_fingerprint_snake_case():
    md = {"model_version": "2025-06-15_01_RC02", "response_id": "r-abc"}
    fp = extract_model_fingerprint("gemini", md)
    assert fp.fingerprint == "2025-06-15_01_RC02"
    assert fp.fingerprint_type == "gemini.modelVersion"
    assert fp.extras["gemini_model_version"] == "2025-06-15_01_RC02"
    assert fp.extras["gemini_response_id"] == "r-abc"


def test_build_run_record_merges_metadata_and_extras():
    md = {"modelVersion": "vRC03", "responseId": "resp-9"}
    usage = {"input_tokens": 100, "output_tokens": 200}
    rec = build_run_record(
        provider="gemini",
        model_alias="gemini-2.5-pro",
        prompt_text="Hi",
        completion_text="Hello",
        response_metadata=md,
        usage_metadata=usage,
        temperature=0.2,
        top_p=1.0,
        max_tokens=256,
        seed=42,
        existing_metadata_json={"trace_id": "t-1"},
    )
    assert rec["system_fingerprint"] == "vRC03"
    assert rec["fingerprint_type"] == "gemini.modelVersion"
    assert rec["metadata"]["trace_id"] == "t-1"
    assert rec["metadata"]["gemini_model_version"] == "vRC03"
    assert rec["metadata"]["gemini_response_id"] == "resp-9"
    assert rec["metadata"]["usage"]["input_tokens"] == 100
    assert rec["seed"] == 42