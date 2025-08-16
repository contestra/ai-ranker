"""
Pytest suite for Contestra LLM adapters (OpenAI Responses + Vertex GenAI)
Following ChatGPT's production test patterns

Usage:
  pip install -U pytest
  pytest tests/test_adapters.py -v

This suite *mocks* provider SDKs; no network calls are made.
It validates REQUIRED vs OFF semantics, grounded detection, JSON enforcement,
and basic routing expectations.
"""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.llm.adapters.types import RunRequest, RunResult, GroundingMode
from app.llm.adapters.openai_production import OpenAIProductionAdapter
from app.llm.adapters.vertex_genai_adapter import VertexGenAIAdapter
from app.llm.orchestrator import LLMOrchestrator


# ------------------------------
# Helpers / Fakes (OpenAI)
# ------------------------------
class FakeOpenAIOutputItem:
    def __init__(self, type_: str):
        self.type = type_
        # Optional: mimic citations API if needed
        self.citations = []

class FakeOpenAIResponse:
    def __init__(self, output_items, output_text, system_fingerprint="fp_123"):
        self.output = output_items
        self.output_text = output_text
        self.system_fingerprint = system_fingerprint
        self.usage = MagicMock()
        self.usage.__dict__ = {"prompt_tokens": 100, "completion_tokens": 50}

class FakeResponsesAPI:
    def __init__(self, response_obj):
        self._response_obj = response_obj
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._response_obj

class FakeOpenAIClient:
    def __init__(self, response_obj):
        self.responses = FakeResponsesAPI(response_obj)


# ------------------------------
# Helpers / Fakes (Vertex)
# ------------------------------
class FakeVertexResp:
    """Minimal surface used by the adapter: .text and .to_dict()."""
    def __init__(self, text: str, grounded: bool):
        self.text = text
        self._grounded = grounded
        self.metadata = MagicMock()
        self.metadata.model_version = "gemini-1.5-pro-002_v1"
        self.metadata.response_id = "resp_123"

    def to_dict(self):
        if self._grounded:
            return {
                "candidates": [{
                    "grounding_metadata": {
                        "web_search_queries": ["test query"],
                        "grounding_attributions": [
                            {"source_uri": "https://example.com", "title": "Example"}
                        ]
                    }
                }]
            }
        return {"candidates": [{}]}

class FakeModels:
    def __init__(self, response_obj):
        self._response_obj = response_obj
        self.last_kwargs = None

    def generate_content(self, **kwargs):
        self.last_kwargs = kwargs
        return self._response_obj

class FakeVertexClient:
    def __init__(self, response_obj):
        self.models = FakeModels(response_obj)


# ------------------------------
# Fixtures
# ------------------------------
@pytest.fixture
def locale_schema():
    return {
        "name": "locale_probe",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "vat_percent": {"type": "string"},
                "plug": {"type": "array", "items": {"type": "string"}},
                "emergency": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["vat_percent", "plug", "emergency"],
        },
        "strict": True,
    }

@pytest.fixture
def base_req(locale_schema):
    return RunRequest(
        run_id="r1",
        client_id="TEST",
        provider="openai",
        model_name="gpt-4o",
        grounding_mode=GroundingMode.REQUIRED,
        system_text="Use ALS; output must match schema.",
        als_block="[ALS] Operating from Singapore; GST applies.",
        user_prompt=(
            "Return ONLY the JSON with vat_percent (e.g. '9%'), plug letters and emergency numbers."
        ),
        temperature=0.0,
        top_p=1.0,
        seed=123,
        schema=locale_schema,
    )


# ------------------------------
# OpenAI Responses adapter tests
# ------------------------------

def test_openai_grounded_required_success(base_req):
    """Test successful grounded request with web search"""
    adapter = OpenAIProductionAdapter()
    
    # Mock grounded response (one web_search_call) + valid JSON
    response = FakeOpenAIResponse(
        output_items=[FakeOpenAIOutputItem("web_search_call")],
        output_text=json.dumps({"vat_percent": "9%", "plug": ["G"], "emergency": ["999", "995"]}),
    )
    adapter.client = FakeOpenAIClient(response)

    res = adapter.run_sync(base_req)

    assert res.grounded_effective is True
    assert res.tool_call_count == 1
    assert res.json_obj["vat_percent"] == "9%"
    assert res.provider == "openai"
    assert res.system_fingerprint == "fp_123"
    assert res.json_valid is True


def test_openai_grounded_required_no_tool_raises(base_req):
    """Test that REQUIRED mode raises when no web search occurs"""
    adapter = OpenAIProductionAdapter()
    
    # No web_search_call → should raise in REQUIRED mode
    response = FakeOpenAIResponse(
        output_items=[],
        output_text=json.dumps({"vat_percent": "9%", "plug": ["G"], "emergency": ["999", "995"]}),
    )
    adapter.client = FakeOpenAIClient(response)

    with pytest.raises(RuntimeError, match="Grounding REQUIRED but no web search"):
        adapter.run_sync(base_req)


def test_openai_ungrounded_pass(base_req):
    """Test ungrounded mode works without tools"""
    adapter = OpenAIProductionAdapter()
    
    # Switch to OFF and ensure we still get JSON with no tool calls
    req = base_req.model_copy(update={"grounding_mode": GroundingMode.OFF})
    response = FakeOpenAIResponse(
        output_items=[],
        output_text=json.dumps({"vat_percent": "9%", "plug": ["G"], "emergency": ["999", "995"]}),
    )
    adapter.client = FakeOpenAIClient(response)

    res = adapter.run_sync(req)
    
    assert res.grounded_effective is False
    assert res.tool_call_count == 0
    assert res.json_obj["plug"] == ["G"]
    assert res.json_valid is True


def test_openai_invalid_json_raises(base_req):
    """Test that invalid JSON raises error in REQUIRED mode"""
    adapter = OpenAIProductionAdapter()
    
    # Provide invalid JSON
    response = FakeOpenAIResponse(
        output_items=[FakeOpenAIOutputItem("web_search_call")],
        output_text="NOT JSON"
    )
    adapter.client = FakeOpenAIClient(response)

    with pytest.raises(RuntimeError, match="JSON schema enforced but output invalid"):
        adapter.run_sync(base_req)


def test_openai_preferred_mode_fallback(base_req):
    """Test PREFERRED mode doesn't raise on missing grounding"""
    adapter = OpenAIProductionAdapter()
    
    req = base_req.model_copy(update={"grounding_mode": GroundingMode.PREFERRED})
    response = FakeOpenAIResponse(
        output_items=[],  # No web search
        output_text=json.dumps({"vat_percent": "9%", "plug": ["G"], "emergency": ["999", "995"]}),
    )
    adapter.client = FakeOpenAIClient(response)

    res = adapter.run_sync(req)
    
    # Should not raise, just return ungrounded
    assert res.grounded_effective is False
    assert res.tool_call_count == 0
    assert res.json_valid is True


# ------------------------------
# Vertex GenAI adapter tests
# ------------------------------

def test_vertex_grounded_required_success(locale_schema):
    """Test successful grounded Vertex request"""
    adapter = VertexGenAIAdapter(project="contestra-ai", location="europe-west4")
    
    req = RunRequest(
        run_id="r2",
        client_id="TEST",
        provider="vertex",
        model_name="publishers/google/models/gemini-1.5-pro-002",
        region="europe-west4",
        grounding_mode=GroundingMode.REQUIRED,
        system_text="",
        als_block="[ALS] Operating from Singapore; GST applies.",
        user_prompt="Return only the JSON.",
        temperature=0.0,
        top_p=1.0,
        seed=456,
        schema=locale_schema,
    )
    
    # Mock grounded response
    fake_resp = FakeVertexResp(
        text=json.dumps({"vat_percent": "9%", "plug": ["G"], "emergency": ["999", "995"]}),
        grounded=True,
    )
    adapter.client = FakeVertexClient(fake_resp)

    res = adapter.run(req)
    
    assert res.grounded_effective is True
    assert res.tool_call_count >= 1
    assert res.json_obj["emergency"] == ["999", "995"]
    assert res.provider == "vertex"
    assert res.system_fingerprint == "gemini-1.5-pro-002_v1"
    assert res.json_valid is True


def test_vertex_grounded_required_no_metadata_raises(locale_schema):
    """Test that REQUIRED mode raises when no grounding metadata"""
    adapter = VertexGenAIAdapter(project="contestra-ai", location="europe-west4")
    
    req = RunRequest(
        run_id="r3",
        client_id="TEST",
        provider="vertex",
        model_name="publishers/google/models/gemini-1.5-pro-002",
        grounding_mode=GroundingMode.REQUIRED,
        als_block="[ALS] Singapore",
        user_prompt="Return JSON",
        schema=locale_schema,
    )
    
    fake_resp = FakeVertexResp(
        text=json.dumps({"vat_percent": "9%", "plug": ["G"], "emergency": ["999", "995"]}),
        grounded=False,  # No grounding metadata
    )
    adapter.client = FakeVertexClient(fake_resp)

    with pytest.raises(RuntimeError, match="Grounding REQUIRED but no grounding metadata"):
        adapter.run(req)


def test_vertex_ungrounded_pass(locale_schema):
    """Test ungrounded Vertex request"""
    adapter = VertexGenAIAdapter(project="contestra-ai", location="europe-west4")
    
    req = RunRequest(
        run_id="r4",
        client_id="TEST",
        provider="vertex",
        model_name="publishers/google/models/gemini-1.5-pro-002",
        grounding_mode=GroundingMode.OFF,
        als_block="[ALS] Singapore",
        user_prompt="Return JSON",
        schema=locale_schema,
    )
    
    fake_resp = FakeVertexResp(
        text=json.dumps({"vat_percent": "9%", "plug": ["G"], "emergency": ["999", "995"]}),
        grounded=False,
    )
    adapter.client = FakeVertexClient(fake_resp)

    res = adapter.run(req)
    
    assert res.grounded_effective is False
    assert res.tool_call_count == 0
    assert res.json_valid is True


def test_vertex_invalid_json_raises(locale_schema):
    """Test that invalid JSON raises error"""
    adapter = VertexGenAIAdapter(project="contestra-ai", location="europe-west4")
    
    req = RunRequest(
        run_id="r5",
        client_id="TEST",
        provider="vertex",
        model_name="publishers/google/models/gemini-1.5-pro-002",
        grounding_mode=GroundingMode.REQUIRED,
        als_block="[ALS] Singapore",
        user_prompt="Return JSON",
        schema=locale_schema,
    )
    
    fake_resp = FakeVertexResp(text="NOT JSON", grounded=True)
    adapter.client = FakeVertexClient(fake_resp)

    with pytest.raises(RuntimeError, match="JSON schema enforced but output invalid"):
        adapter.run(req)


# ------------------------------
# Orchestrator tests
# ------------------------------

def test_orchestrator_routes_openai(locale_schema):
    """Test orchestrator routes to OpenAI adapter"""
    orch = LLMOrchestrator(gcp_project="contestra-ai", vertex_region="europe-west4")
    
    # Mock OpenAI adapter
    mock_result = RunResult(
        run_id="r6",
        provider="openai",
        model_name="gpt-4o",
        grounded_effective=False,
        tool_call_count=0,
        json_text="{}",
        json_obj={},
        json_valid=True,
        latency_ms=100,
    )
    
    with patch.object(orch.openai, 'run_sync', return_value=mock_result) as mock_run:
        req = RunRequest(
            run_id="r6",
            client_id="TEST",
            provider="openai",
            model_name="gpt-4o",
            grounding_mode=GroundingMode.OFF,
            user_prompt="test",
            schema=locale_schema,
        )
        
        res = orch.run(req)
        
        assert res.provider == "openai"
        assert res.run_id == "r6"
        mock_run.assert_called_once_with(req)


def test_orchestrator_routes_vertex(locale_schema):
    """Test orchestrator routes to Vertex adapter"""
    orch = LLMOrchestrator(gcp_project="contestra-ai", vertex_region="europe-west4")
    
    # Mock Vertex adapter
    mock_result = RunResult(
        run_id="r7",
        provider="vertex",
        model_name="gemini-1.5-pro-002",
        region="europe-west4",
        grounded_effective=True,
        tool_call_count=1,
        json_text="{}",
        json_obj={},
        json_valid=True,
        latency_ms=200,
    )
    
    with patch.object(orch.vertex, 'run', return_value=mock_result) as mock_run:
        req = RunRequest(
            run_id="r7",
            client_id="TEST",
            provider="vertex",
            model_name="gemini-1.5-pro-002",
            grounding_mode=GroundingMode.REQUIRED,
            user_prompt="test",
            schema=locale_schema,
        )
        
        res = orch.run(req)
        
        assert res.provider == "vertex"
        assert res.run_id == "r7"
        assert res.region == "europe-west4"
        mock_run.assert_called_once_with(req)


def test_orchestrator_unknown_provider_raises():
    """Test orchestrator raises for unknown provider"""
    orch = LLMOrchestrator(gcp_project="contestra-ai", vertex_region="europe-west4")
    
    req = RunRequest(
        run_id="r8",
        client_id="TEST",
        provider="anthropic",  # Unknown provider
        model_name="claude-3",
        grounding_mode=GroundingMode.OFF,
        user_prompt="test",
    )
    
    with pytest.raises(ValueError, match="Unknown provider: anthropic"):
        orch.run(req)


def test_orchestrator_validate_request():
    """Test request validation"""
    orch = LLMOrchestrator(gcp_project="contestra-ai", vertex_region="europe-west4")
    
    # Valid request
    req = RunRequest(
        run_id="r9",
        client_id="TEST",
        provider="openai",
        model_name="gpt-4o",
        grounding_mode=GroundingMode.OFF,
        user_prompt="test",
    )
    assert orch.validate_request(req) is True
    
    # Invalid provider
    req_bad = req.model_copy(update={"provider": "invalid"})
    with pytest.raises(ValueError, match="Unknown provider"):
        orch.validate_request(req_bad)
    
    # ALS block too long
    req_long = req.model_copy(update={"als_block": "x" * 400})
    with pytest.raises(ValueError, match="ALS block too long"):
        orch.validate_request(req_long)
    
    # Temperature out of range
    req_temp = req.model_copy(update={"temperature": 3.0})
    with pytest.raises(ValueError, match="Temperature out of range"):
        orch.validate_request(req_temp)


@pytest.mark.asyncio
async def test_orchestrator_async_routing():
    """Test async orchestrator routing"""
    orch = LLMOrchestrator(gcp_project="contestra-ai", vertex_region="europe-west4")
    
    # Mock async method
    mock_result = RunResult(
        run_id="r10",
        provider="openai",
        model_name="gpt-4o",
        grounded_effective=False,
        tool_call_count=0,
        json_text="{}",
        json_obj={},
        json_valid=True,
        latency_ms=100,
    )
    
    with patch.object(orch.openai, 'run_async', return_value=mock_result) as mock_run:
        req = RunRequest(
            run_id="r10",
            client_id="TEST",
            provider="openai",
            model_name="gpt-4o",
            grounding_mode=GroundingMode.OFF,
            user_prompt="test",
        )
        
        res = await orch.run_async(req)
        
        assert res.provider == "openai"
        assert res.run_id == "r10"
        mock_run.assert_called_once_with(req)