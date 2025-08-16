# GPT-5 Output Token Starvation - Root Cause & Fix

## Root Cause Identified
**The GPT-5 empty output issue is caused by output token starvation, not a missing field or API bug.**

When `max_output_tokens: 96` is set with GPT-5 + web_search tools, the model exhausts its token budget on reasoning before producing the final message. This explains why we only see a `reasoning` item with no `message` in the output.

## Evidence
- Debug logs show only `reasoning` items, no `message` items
- The `reasoning` item appears but with empty summary
- 96 tokens is consumed entirely by reasoning phase
- No tokens left for tool calls or final answer

## The Fix

### 1. Increase Output Token Budget
```python
# BEFORE (starves the output)
"max_output_tokens": 96  

# AFTER (gives room for reasoning + tools + answer)
"max_output_tokens": 512  # or higher for complex queries
```

### 2. Add Reasoning Configuration for GPT-5
```python
# Reduce reasoning token consumption
"reasoning": {"effort": "low"}  # Only for GPT-5 with tools
```

### 3. Current Constants Need Update
File: `backend/app/llm/adapters/openai_production.py`
```python
# Current (too small)
RESPONSES_MAX_OUTPUT_TOKENS_DEFAULT = 96  

# Should be
RESPONSES_MAX_OUTPUT_TOKENS_DEFAULT = 512  # Minimum for GPT-5 with tools
RESPONSES_MAX_OUTPUT_TOKENS_GROUNDED_GPT5 = 1024  # When grounding is enabled
```

## Why This Happens

GPT-5 reasoning models emit output in this order:
1. **Reasoning item** - Internal thinking (counts against output tokens)
2. **Tool call items** - Web searches (if applicable)
3. **Message item** - Final answer with output_text

With only 96 tokens, GPT-5:
- Spends all tokens on step 1 (reasoning)
- Never reaches step 2 or 3
- Returns incomplete response with no message

## Mode Integrity Principle

**CRITICAL**: Never change grounding mode mid-execution. The three modes (UNGROUNDED, PREFERRED, REQUIRED) are the experiment itself.

### Invariants That Must Be Maintained:
1. **Mode immutability**: The requested mode never changes during execution
2. **Tool configuration per mode**:
   - UNGROUNDED: `tools=None`
   - PREFERRED: `tools=[{"type":"web_search"}]`, `tool_choice="auto"`
   - REQUIRED: Same as PREFERRED for GPT-5 (soft-required), then fail if no search

### What NOT to Do:
- ❌ Fall back to UNGROUNDED if grounded mode fails
- ❌ Retry with different mode
- ❌ Change tool configuration based on response

### What TO Do:
- ✅ Retry with same mode but higher token limit
- ✅ Fail the run if acceptance criteria not met
- ✅ Log the failure reason accurately

## Implementation Changes Needed

### File: `backend/app/llm/adapters/openai_production.py`

1. **Update token limits**:
```python
# Line 19-23
RESPONSES_MAX_OUTPUT_TOKENS_DEFAULT = 512  # Was 96
RESPONSES_MAX_OUTPUT_TOKENS_MIN = 16
RESPONSES_TEMPERATURE_DEFAULT = 0
RESPONSES_TEMPERATURE_GPT5 = 1.0
RESPONSES_MAX_OUTPUT_TOKENS_GPT5_GROUNDED = 1024  # New constant
```

2. **Update `_http_grounded_with_schema` method** (around line 220):
```python
# Determine token budget based on model and mode
if _is_gpt5(req.model_name) and needs_grounding:
    max_output_tokens = RESPONSES_MAX_OUTPUT_TOKENS_GPT5_GROUNDED
else:
    max_output_tokens = RESPONSES_MAX_OUTPUT_TOKENS_DEFAULT

body = {
    "model": req.model_name,
    "input": self._build_input_messages(...),
    "tools": tools,
    "tool_choice": tool_choice,
    "temperature": ...,
    "max_output_tokens": max_output_tokens,
}

# Add reasoning config for GPT-5 with tools
if _is_gpt5(req.model_name) and needs_grounding:
    body["reasoning"] = {"effort": "low"}
```

3. **Add retry logic for token starvation**:
```python
# After initial call, check if we got reasoning but no message
has_reasoning = any(item.get("type") == "reasoning" for item in output_items)
has_message = any(item.get("type") == "message" for item in output_items)

if has_reasoning and not has_message and max_output_tokens < 2048:
    # Token starvation detected, retry with double the tokens
    logger.warning(f"Token starvation detected, retrying with {max_output_tokens * 2} tokens")
    body["max_output_tokens"] = max_output_tokens * 2
    # Make second attempt with same mode/tools
    response = await client.post(url, headers=headers, json=body)
    # Re-parse response...
```

## Telemetry to Add

For debugging and monitoring:
- `reasoning_tokens`: From `usage.output_tokens_details.reasoning_tokens`
- `output_tokens`: From `usage.output_tokens`
- `token_starved`: Boolean flag when reasoning exists but no message
- `retry_count`: Number of retries due to token starvation
- `final_max_tokens`: The token limit that actually worked

## Expected Outcomes After Fix

1. **GPT-5 UNGROUNDED**: Already works (no change needed)
2. **GPT-5 PREFERRED**: Will start returning text with tool calls
3. **GPT-5 REQUIRED**: Will search and return text (soft-required enforcement)

## Testing After Implementation

Run the same test matrix:
```python
# All three modes should now work
("openai", "gpt-5", GroundingMode.OFF)       # Already works
("openai", "gpt-5", GroundingMode.PREFERRED)  # Should work with 512+ tokens
("openai", "gpt-5", GroundingMode.REQUIRED)   # Should work with soft-required
```

## References
- [OpenAI Cookbook - Reasoning Models](https://cookbook.openai.com/examples/responses_api/reasoning_items)
- [OpenAI Cookbook - Web Search](https://cookbook.openai.com/examples/responses_api/responses_example)