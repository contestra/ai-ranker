# Grounding Implementation - Final Status

## Current Results: 75% Success Rate

| Model | Ungrounded | Grounded | Status |
|-------|------------|----------|--------|
| **GPT-5** | ✅ Pass | ✅ Pass | Fully working with web search |
| **Gemini 2.5 Pro** | ✅ Pass | ❌ Fail | Not triggering GoogleSearch |

## What's Working

### GPT-5 Grounding ✅
- Successfully performs web searches
- Returns official source URLs (IRAS.gov.sg)
- JSON responses properly formatted
- Tool choice set to "auto" (GPT-5 doesn't support "required")

### Vertex Improvements ✅
- JSON markdown fences handled correctly
- Bulletproof grounding detection implemented
- Model capability checking added
- Proper error messages for unsupported models

## Remaining Issue: Gemini 2.5 Pro Not Grounding

Despite all the fixes from ChatGPT:
- ✅ Using Gemini 2.5 Pro (supports grounding)
- ✅ Temperature set to 1.0
- ✅ Asking for "current" information "as of today"
- ✅ Requesting official sources
- ❌ Still not triggering GoogleSearch tool

## Code Improvements Applied

### 1. Fence Stripper
```python
def _strip_code_fences(s: str) -> str:
    """Remove markdown code fences and preamble"""
    if "```" in s:
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', s, re.DOTALL)
        if match:
            return match.group(1).strip()
    return s.strip()
```

### 2. Grounding Detection
```python
def _vertex_grounding_signals(resp) -> Dict[str, Any]:
    """Extract grounding signals from Vertex response"""
    # Checks for citations and web_search_queries
    # Returns grounded=True only if metadata present
```

### 3. Model Capability Check
```python
def _assert_grounding_capable(model_name: str):
    """Ensure model supports grounding"""
    allowed = {"gemini-2.5-pro", "gemini-2.5-flash"}
    if short_name not in allowed:
        raise RuntimeError("Model not configured for GoogleSearch")
```

## Lessons Learned

1. **GPT-5 Limitation**: Can't use `tool_choice="required"` with web_search
2. **JSON in Prompts**: Don't mention "return JSON" - let schema handle it
3. **Grounding Detection**: Must check metadata, not just response content
4. **Model Versions**: Only Gemini 2.5 supports grounding (not 1.5 or 2.0)

## Next Steps

The system is 75% functional with GPT-5 fully working. Gemini 2.5 Pro may need:
- Different prompt phrasing to trigger search
- Possible API configuration issue
- May need to contact Google support about GoogleSearch not activating

## Success Metrics

- ✅ GPT-5 grounding complete
- ✅ JSON handling robust
- ✅ Error messages clear
- ✅ Model validation implemented
- ⚠️ Gemini grounding still not activating