# ChatGPT's Grounding Fix - Make Tools Actually Fire

## The Core Problem
Our current locale probe asks for **stable knowledge** (VAT rates, plug types, emergency numbers) which models can answer from training data. Neither OpenAI nor Vertex feel the need to search the web for this information.

## The Solution: Different Prompts for Grounded vs Ungrounded

### Ungrounded Tests (Keep Current Probe)
```json
{
  "prompt": "Return JSON with VAT rate, plug types, emergency numbers",
  "purpose": "Test pure model knowledge without web search"
}
```

### Grounded Tests (Force Current Information)
```json
{
  "prompt": "What is the current VAT rate in Singapore as of today? Return JSON and include an official source URL.",
  "purpose": "Force web search by requiring current verification"
}
```

## Implementation Changes

### 1. OpenAI Responses API - Force Tool Usage

```python
# CRITICAL: Use tool_choice="required" to force web search
resp = client.responses.create(
    model="gpt-4o",
    input=[{"role": "user", "content": "What is the current VAT rate in Singapore as of today? Include source URL."}],
    tools=[{"type": "web_search"}],
    tool_choice="required",  # <-- FORCES at least one tool call
    extra_body={"text": {"format": {"type": "json_schema", "json_schema": schema}}}
)

# Verify grounding happened
tool_call_count = sum(1 for item in resp.output if item.type == "web_search_call")
assert tool_call_count > 0, "Grounding REQUIRED but no web search performed"
```

### 2. Vertex Gemini - Provoke and Verify

```python
# Attach GoogleSearch tool
config = GenerateContentConfig(
    tools=[Tool(google_search=GoogleSearch())],
    temperature=1.0,  # Google recommends 1.0 for best grounding
    response_mime_type="application/json",
    response_schema=schema
)

# Use prompt that requires current info
response = client.models.generate_content(
    model=model_name,
    contents="What is the current VAT rate in Singapore as of today? Cite official sources.",
    config=config
)

# Verify grounding via metadata
grounding_metadata = response.candidates[0].grounding_metadata
assert grounding_metadata and grounding_metadata.web_search_queries, "No grounding detected"
```

## Test Matrix Update

| Test Type | Prompt Type | Tools | Expected |
|-----------|------------|-------|----------|
| **OpenAI Ungrounded** | Stable knowledge | None | Model answers from training |
| **OpenAI Grounded** | Current info + "as of today" | web_search + tool_choice="required" | Must perform web search |
| **Vertex Ungrounded** | Stable knowledge | None | Model answers from training |
| **Vertex Grounded** | Current info + "cite sources" | GoogleSearch() | Should search and cite |

## Grounding Trigger Phrases

### For OpenAI
- "as of today"
- "current [thing] in [location]"
- "latest official [data]"
- "verify from official sources"

### For Vertex
- "cite official sources"
- "include source URLs"
- "according to government websites"
- "latest published data"

## Verification Methods

### OpenAI Responses
```python
# Check output array for web_search steps
grounded = any(item.type == "web_search_call" for item in response.output)

# Extract citations
citations = []
for item in response.output:
    if item.type == "web_search_call" and hasattr(item, "citations"):
        citations.extend(item.citations)
```

### Vertex Gemini
```python
# Check grounding metadata
response_dict = response.to_dict()
grounding_metadata = response_dict.get("candidates", [{}])[0].get("grounding_metadata", {})

grounded = bool(
    grounding_metadata.get("web_search_queries") or 
    grounding_metadata.get("grounding_attributions")
)

# Extract citations
citations = grounding_metadata.get("grounding_attributions", [])
```

## Dashboard Instrumentation

Store these metrics:
- `tool_call_count`: Number of web searches performed
- `grounded_effective`: Boolean - did grounding actually happen?
- `citations`: Array of source URLs found
- `web_search_queries`: What searches were performed (Vertex)
- `grounding_confidence`: How confident the model is in grounded facts

## Quick Fixes if Still Not Working

1. **OpenAI not searching**: 
   - Ensure using Responses API, not Chat Completions
   - Set `tool_choice="required"`
   - Use model that supports web_search (gpt-4o, gpt-4o-mini)

2. **Vertex not searching**:
   - Temperature must be > 0 (use 1.0)
   - Prompt must request current/verifiable info
   - Check response for groundingMetadata field

3. **Both not searching**:
   - Prompts too generic - add "as of today", "current", "latest"
   - Request citations explicitly
   - Ask for information that changes frequently