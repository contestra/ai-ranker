# ⚠️ CRITICAL: Model Requirements - DO NOT DEVIATE

## The ONLY Supported Models

### OpenAI (via Responses API)
```python
models = ["gpt-5", "gpt-5-mini", "gpt-5-nano"]
```

### Google Vertex AI
```python
models = ["gemini-2.5-pro", "gemini-2.5-flash"]
```

## NEVER Use These Models
- ❌ **GPT-4o** - Not supported, use GPT-5
- ❌ **GPT-4o-mini** - Not supported, use GPT-5-mini
- ❌ **Gemini 1.5 Pro** - No grounding support
- ❌ **Gemini 1.5 Flash** - No grounding support
- ❌ **Gemini 2.0 Flash** - Limited grounding, use 2.5

## Why This Matters

1. **GPT-5** is the current production model with web search
2. **Gemini 2.5** is the ONLY Gemini version with GoogleSearch grounding
3. Using wrong models will break grounding tests
4. Customer expects GPT-5 and Gemini 2.5 Pro specifically

## Code That Must Use Correct Models

- `test_grounding_with_current_info.py`
- `test_production_architecture.py`
- `app/api/grounding_test.py`
- `frontend/src/components/GroundingTestGrid.tsx`
- Any new test files

## Remember

When in doubt:
- OpenAI = GPT-5 (not GPT-4o)
- Google = Gemini 2.5 Pro (not 1.5 or 2.0)

This is not a suggestion - it's a requirement.