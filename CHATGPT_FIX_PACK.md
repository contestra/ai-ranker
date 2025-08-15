# ChatGPT's Production Fix Pack - August 15, 2025

**Purpose**: Make all production tests green and keep semantics clean

## 1. OpenAI (Responses) - Keep Grounding + JSON, Drop Seed

### What's Right
- Responses supports `web_search` AND structured JSON (via `text.format`)

### What to Change
- Don't pass `seed` to Responses (track in metadata only)
- Keep `tools=[{"type":"web_search"}]` for grounded; omit for ungrounded
- Keep structured output with `extra_body`

### Minimal Patch (adapter)
```python
# OpenAIResponsesAdapter.run(...)
kwargs = {
  "model": req.model_name,
  "input": self._mk_input(req.system_text, req.als_block, req.user_prompt),
  "temperature": req.temperature,
}
if req.grounding_mode in (GroundingMode.REQUIRED, GroundingMode.PREFERRED):
    kwargs["tools"] = [{"type": "web_search"}]
    kwargs["tool_choice"] = "auto"

# Do not send 'seed' to Responses; just persist it in metadata
kwargs["extra_body"] = {"text": {"format": {"type": "json_schema", "json_schema": schema}}}

resp = self.client.responses.create(**kwargs)
json_text = resp.output_text or ""  # schema-conformant
tool_call_count = sum(1 for it in getattr(resp, "output", []) if getattr(it, "type", "") == "web_search_call")
grounded_effective = tool_call_count > 0
if req.grounding_mode is GroundingMode.REQUIRED and not grounded_effective:
    raise RuntimeError("Grounded REQUIRED but no web_search tool was invoked")
```

Log `response_id = getattr(resp, "id", None)` and `model_version = getattr(resp, "model", None)` for reproducibility.

## 2. Vertex (Gemini) - Enforce Project/Region/Model & JSON

### Symptoms Found
- Wrong project being used
- Occasional non-JSON text

### Fixes
- Always pass intended project to client
- Normalize model IDs to publisher path
- Enforce JSON via `response_mime_type` and `response_schema`

### Minimal Patch (adapter)
```python
# __init__
self.client = genai.Client(vertexai=True, project=self.project, location=self.location)

# before call
model_name = req.model_name
if not model_name.startswith("publishers/"):
    model_name = f"publishers/google/models/{model_name}"

cfg = GenerateContentConfig(
    temperature=req.temperature,
    top_p=req.top_p or 1.0,
    response_mime_type="application/json",
    response_schema=self._to_schema(req.schema),
    **({"tools":[Tool(google_search=GoogleSearch())]} if req.grounding_mode in (GroundingMode.REQUIRED, GroundingMode.PREFERRED) else {})
)
if req.seed is not None:
    cfg.seed = req.seed  # Vertex supports seed

resp = self.client.models.generate_content(model=model_name, contents=contents, config=cfg)

# robust JSON extraction
text = getattr(resp, "text", None)
if not text:
    try:
        cand = resp.candidates[0]
        for part in cand.content.parts:
            if getattr(part, "text", None):
                text = part.text
                break
    except Exception:
        pass
if not text:
    raise RuntimeError("No JSON text in Vertex response")
json_obj = json.loads(text)

# grounding evidence (best-effort)
tool_call_count, grounded_effective, citations = 0, False, []
try:
    d = resp.to_dict() if hasattr(resp, "to_dict") else resp.__dict__
    gm = d.get("grounding_metadata") or (d.get("candidates", [{}])[0].get("grounding_metadata"))
    if gm:
        grounded_effective = True
        tool_call_count = 1
        citations = gm.get("citations") or []
except Exception:
    pass

if req.grounding_mode is GroundingMode.REQUIRED and not grounded_effective:
    raise RuntimeError("Grounded REQUIRED but no grounding metadata detected")
```

## 3. Ensure Vertex Uses the Right Project

### Runtime Assertion
```python
# preflight (run once at startup)
import google.auth
creds, detected = google.auth.default()
assert detected == "contestra-ai", f"ADC default project {detected} != contestra-ai"

# adapter guard
assert self.project == "contestra-ai", f"Vertex adapter misconfigured: project={self.project}"
```

## 4. Add `json_valid` to RunResult

Add to Pydantic model:
```python
class RunResult(BaseModel):
    ...
    json_valid: bool = Field(..., description="Whether JSON parsing succeeded")
```

## 5. Don't Degrade Semantics

For `grounding_mode=REQUIRED`:
- Remove fallback to Chat Completions entirely
- If Responses errors or doesn't search, **fail closed**
- Log `error_code`, `error_class`, `fallback_route=None`

## 6. Preflight Check

```python
def preflight():
    # Vertex: model exists in region?
    v = genai.Client(vertexai=True, project="contestra-ai", location="europe-west4")
    names = [m.name for m in v.models.list() if "gemini" in m.name]
    assert "publishers/google/models/gemini-1.5-pro-002" in names

    # Vertex: 1-token grounded smoke
    v.models.generate_content(
        model="publishers/google/models/gemini-1.5-pro-002",
        contents="{}",
        config=GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Schema(type=Type.OBJECT, properties={}),
            tools=[Tool(google_search=GoogleSearch())],
            temperature=0
        )
    )

    # OpenAI: Responses supports both web_search + json schema
    from openai import OpenAI
    client = OpenAI()
    client.responses.create(
        model="gpt-4o",
        input=[{"role":"user","content":"{}"}],
        tools=[{"type":"web_search"}],
        tool_choice="auto",
        extra_body={"text":{"format":{"type":"json_schema","json_schema":{"name":"x","schema":{"type":"object"},"strict":True}}}},
        temperature=0
    )
```

## 7. Production Test Expectations

### Expected Results for `test_production_architecture.py`

| Test | grounded_effective | tool_call_count | json_valid |
|------|-------------------|-----------------|------------|
| **OpenAI ungrounded** | False | 0 | True |
| **OpenAI grounded** | True | ≥1 | True |
| **Vertex ungrounded** | False | 0 | True |
| **Vertex grounded** | True | ≥1 | True |

## Implementation Checklist

- [ ] Remove seed from OpenAI Responses kwargs ✅ (already done)
- [ ] Add json_valid to RunResult model
- [ ] Fix Vertex project assertion
- [ ] Improve JSON extraction in Vertex adapter
- [ ] Remove Chat Completions fallback
- [ ] Add preflight checks
- [ ] Update test expectations

## Key Principles

1. **Fail Closed**: If grounding is REQUIRED and doesn't happen, raise exception
2. **No Degradation**: Don't fall back to less capable APIs
3. **Project Consistency**: Always use "contestra-ai" project
4. **JSON Enforcement**: Use native schema validation, not prompt hacks
5. **Proper Logging**: Track response_id, model_version for reproducibility