# Vertex Grounding Final Fix - ChatGPT's Solution

## Problem 1: JSON Wrapped in Markdown Fences

**Root Cause**: Telling the model to "return JSON" in the prompt makes it add markdown code fences.

**Solution**: 
- Keep `response_mime_type="application/json"` and `response_schema`
- REMOVE "return JSON" from prompts - let the schema enforce it
- Add fence stripper as defensive measure

## Problem 2: Grounding Detection Not Reliable

**Root Cause**: Not checking the right metadata fields.

**Solution**: Check for `grounding_metadata.citations` or `web_search_queries` presence.

## Implementation

### 1. Code Fence Stripper
```python
def _strip_code_fences(s: str) -> str:
    """Remove markdown code fences if present"""
    if not s: 
        return s
    s = s.strip()
    if s.startswith("```"):
        s = s.strip("`")
        # handle ```json ... ```
        s = s.split("\n", 1)[1] if "\n" in s else s
    return s.strip()
```

### 2. Grounding Detection Helper
```python
def _vertex_grounding_signals(resp) -> dict:
    """Return grounding signals from Vertex response"""
    grounded, tc = False, 0
    citations, queries = [], []
    try:
        d = resp.to_dict() if hasattr(resp, "to_dict") else resp.__dict__
        # Root or first-candidate metadata
        gm = (d.get("grounding_metadata") or 
              (d.get("candidates", [{}])[0].get("grounding_metadata")) or 
              {})
        citations = gm.get("citations") or []
        queries = gm.get("web_search_queries") or gm.get("search_queries") or []
        if citations or queries:
            grounded, tc = True, 1
    except Exception:
        pass
    return {
        "grounded": grounded, 
        "tool_calls": tc, 
        "citations": citations, 
        "queries": queries
    }
```

### 3. Model Capability Check
```python
def _assert_grounding_capable(model_name: str):
    """Ensure model supports grounding"""
    allowed = {
        "publishers/google/models/gemini-2.5-pro",
        "publishers/google/models/gemini-2.5-flash",
    }
    if model_name not in allowed:
        raise RuntimeError(
            f"Model '{model_name}' not configured for GoogleSearch. "
            "Use gemini-2.5-pro or gemini-2.5-flash."
        )
```

## Key Changes to Make

1. **Remove "Return as JSON" from prompts** - Let schema handle it
2. **Add fence stripper** to handle any remaining markdown
3. **Use grounding signals helper** for reliable detection
4. **Assert model capability** before attempting grounding
5. **Use temperature=1.0** for grounded requests

## Test Prompts That Work

### Ungrounded (Stable Knowledge)
```
"Return VAT rate, plug types, and emergency numbers"
```

### Grounded (Forces Search)
```
"What is the current GST rate in Singapore as of today? Include official source URL"
```

## Success Criteria

- **Ungrounded**: `tool_call_count == 0` AND valid JSON
- **Grounded**: `grounded_effective == true` AND valid JSON