import uuid
import json
from datetime import datetime
from fastapi.testclient import TestClient

# ---------- Helpers ----------
def make_template_payload():
    return {
        "org_id": str(uuid.uuid4()),
        "workspace_id": str(uuid.uuid4()),
        "name": "AVEA — Top brands",
        "provider": "openai",
        "system_instructions": "Be concise.",
        "user_prompt_template": "List top 10 longevity supplement brands.",
        "country_set": ["US","GB"],
        "model_id": "gpt-4o",
        "inference_params": {"temperature": 0, "max_tokens": 128},
        "tools_spec": [],
        "response_format": {"type": "text"},
        "created_by": str(uuid.uuid4())
    }

def create_and_expect_201(client: TestClient, payload: dict) -> dict:
    r = client.post("/api/prompt-templates", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert "id" in body and body["config_hash"]
    return body

# ---------- Tests ----------

def test_create_template_and_duplicate_409(client: TestClient):
    payload = make_template_payload()
    created = create_and_expect_201(client, payload)
    # Same payload in the SAME workspace should 409
    r = client.post("/api/prompt-templates", json=payload)
    assert r.status_code == 409, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "TEMPLATE_EXISTS"
    assert "template_id" in detail

    # Changing workspace_id should allow creation
    payload2 = dict(payload)
    payload2["workspace_id"] = str(uuid.uuid4())
    r2 = client.post("/api/prompt-templates", json=payload2)
    assert r2.status_code == 201, r2.text

def test_check_duplicate_endpoint(client: TestClient):
    payload = make_template_payload()
    # Create once
    _ = create_and_expect_201(client, payload)
    # Check duplicate: should be exact_match True
    r = client.post("/api/prompt-templates/check-duplicate", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["exact_match"] is True
    assert body["template_id"]

def test_ensure_version_stubbed(client: TestClient, patch_version_service):
    payload = make_template_payload()
    created = create_and_expect_201(client, payload)
    template_id = created["id"]
    body = {
        "org_id": payload["org_id"],
        "workspace_id": payload["workspace_id"],
        "provider": payload["provider"],
        "model_id": payload["model_id"],
        "inference_params": {"max_tokens": 1}
    }
    r = client.post(f"/api/prompt-templates/{template_id}/ensure-version", json=body)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["version_id"] == "00000000-0000-0000-0000-000000000001"
    assert out["provider_version_key"] == "stub-pvk"

def test_run_route_creates_result(client: TestClient, patch_version_service):
    """Test that /run endpoint creates result with system_fingerprint for OpenAI"""
    payload = make_template_payload()
    created = create_and_expect_201(client, payload)
    template_id = created["id"]

    run_req = {
        "rendered_prompt": "Who are the top longevity brands?",
        "brand_name": "AVEA Life",
        "country": "US",
        "analysis_scope": "brand",
        "runtime_vars": {},
        "use_grounding": False
    }
    r = client.post(f"/api/prompt-templates/{template_id}/run", json=run_req)
    assert r.status_code == 200, r.text
    out = r.json()
    
    # Basic assertions
    assert out["result_id"]
    assert out["version_id"] == "00000000-0000-0000-0000-000000000001"
    assert out["provider_version_key"] == "stub-pvk"
    
    # NEW: Assert system_fingerprint is present for OpenAI
    # With the fake LLM, OpenAI returns fp_stub_<hash8>
    assert "system_fingerprint" in out
    assert out["system_fingerprint"] is not None
    assert out["system_fingerprint"].startswith("fp_stub_"), \
        f"Expected OpenAI fingerprint to start with 'fp_stub_', got: {out['system_fingerprint']}"

def test_metrics_endpoint_exists(client: TestClient):
    """Test that /metrics endpoint responds successfully"""
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers.get("content-type", "")
    
    # Check for key metrics
    metrics_text = r.text
    assert "starlette_requests_total" in metrics_text
    assert "prompter_probe_attempts_total" in metrics_text
    assert "prompter_prompt_results_insert_total" in metrics_text