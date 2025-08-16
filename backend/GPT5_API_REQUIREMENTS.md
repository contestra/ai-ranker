# GPT-5 API Requirements - CRITICAL REFERENCE

## DO NOT CHANGE THESE RULES - They are based on actual API behavior

### GPT-5 Responses API Parameters

#### ❌ NEVER USE with GPT-5:
- `temperature` - Causes 400 error "Unsupported parameter"
- `top_p` - Causes 400 error "Unsupported parameter"
- `max_tokens` - Use `max_output_tokens` instead
- `response_format` - Not supported, use `text.format` instead

#### ✅ ALWAYS USE with GPT-5:
- `max_output_tokens` instead of `max_tokens`
- `input` instead of `messages` for Responses API
- `tool_choice: "auto"` (GPT-5 doesn't support "required" with web_search)

#### ✅ REQUIRED VALUES for GPT-5:
- `max_output_tokens`: Minimum 512 with tools, 1024 recommended
- `reasoning: {"effort": "low"}` when tools are present (reduces token burn)

### Model Detection Pattern
```python
_GPT5_ALIAS_RE = re.compile(r"^gpt-5", re.I)

def _is_gpt5(model: str) -> bool:
    return bool(_GPT5_ALIAS_RE.search(model or ""))
```
This catches: gpt-5, gpt-5o, gpt-5-mini, gpt-5-nano, etc.

### Correct Implementation
```python
# FOR GPT-5 MODELS:
kwargs = {
    "model": "gpt-5",
    "input": messages,  # NOT "messages"
    "max_output_tokens": 1024,  # NOT "max_tokens"
    # NO temperature
    # NO top_p
}

# FOR OTHER MODELS (GPT-4, etc):
kwargs = {
    "model": "gpt-4",
    "messages": messages,
    "max_tokens": 512,
    "temperature": 0,
    "top_p": 1,
}
```

### Token Starvation Prevention
GPT-5 with grounding REQUIRES at least 512 tokens, preferably 1024:
- 96 tokens: ALWAYS starves (all consumed by reasoning)
- 256 tokens: Often starves
- 512 tokens: Rarely starves
- 1024 tokens: Never starves

### Tool Choice Limitations
GPT-5 with web_search tool:
- ✅ `tool_choice: "auto"` - Works
- ❌ `tool_choice: "required"` - Returns 400 error
- ❌ `tool_choice: "none"` - Returns 400 error

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "Unsupported parameter: 'temperature'" | Using temperature with GPT-5 | Remove temperature parameter |
| "Unsupported parameter: 'top_p'" | Using top_p with GPT-5 | Remove top_p parameter |
| "Tool choices other than 'auto' not supported" | Using tool_choice:"required" | Use "auto" + provoker for soft-required |
| Empty output with reasoning item | Token starvation | Increase max_output_tokens to 512+ |
| "Unknown parameter: 'max_tokens'" | Using max_tokens with Responses API | Use max_output_tokens instead |

## Implementation Checklist

Before modifying ANY GPT-5 code:
- [ ] Check model with `_is_gpt5()` function
- [ ] Remove temperature/top_p for GPT-5
- [ ] Use max_output_tokens (not max_tokens)
- [ ] Set max_output_tokens >= 512 with tools
- [ ] Use tool_choice:"auto" (not "required")
- [ ] Add reasoning:{"effort":"low"} with tools
- [ ] Use "input" field (not "messages") for Responses API

## Historical Context

This file exists because the same mistakes keep being made:
1. Adding temperature to GPT-5 calls (causes 400 error)
2. Forgetting that GPT-5 needs high token limits with tools
3. Trying to use tool_choice:"required" with GPT-5
4. Using max_tokens instead of max_output_tokens

ALWAYS reference this file before modifying GPT-5 code.