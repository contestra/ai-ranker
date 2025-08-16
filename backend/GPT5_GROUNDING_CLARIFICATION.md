# GPT-5 Grounding Clarification - What Actually Works

## Executive Summary
After comprehensive testing with OpenAI's SDK Responses API, here's what actually works with GPT-5:

### ✅ What Works
1. **GPT-5 DOES support web search** via the Responses API with `tools:[{"type":"web_search"}]`
2. **GPT-5 DOES search and return content** when using `tool_choice:"auto"`
3. **The SDK path works correctly** - `client.responses.create()` returns valid output
4. **Web search calls are properly counted** as `web_search_call` items in response.output

### ⚠️ Limitation
- **GPT-5 does NOT support `tool_choice:"required"`** - Returns 400 error: "Tool choices other than 'auto' are not supported with model 'gpt-5' and the following tool types: 'web_search_preview'"

## Test Results

### Successful Test with tool_choice:"auto"
```python
from openai import OpenAI
client = OpenAI()

resp = client.responses.create(
    model='gpt-5',
    input='What is the current weather in London? Search for latest information.',
    tools=[{'type': 'web_search'}],
    tool_choice='auto',  # MUST use auto, not required
    temperature=1.0
)

# Results:
# - Output items: 4
# - Web search calls: 1 (successfully searched!)
# - Message text: "Current weather in London, UK: Cloudy, 68°F..."
```

### Failed Test with tool_choice:"required"
```python
# Same as above but with tool_choice='required'
# Result: 400 Bad Request
# Error: "Tool choices other than 'auto' are not supported..."
```

## Implementation Strategy for REQUIRED Mode

Since GPT-5 doesn't support `tool_choice:"required"`, here's how to handle REQUIRED mode:

```python
def handle_gpt5_required(req: RunRequest):
    # Step 1: Try with auto + provoker prompt
    provoker = "\n\nSearch for current information and cite sources."
    enhanced_prompt = req.user_prompt + provoker
    
    # Use tool_choice:"auto" (only option for GPT-5)
    resp = client.responses.create(
        model='gpt-5',
        input=enhanced_prompt,
        tools=[{'type': 'web_search'}],
        tool_choice='auto',
        temperature=1.0
    )
    
    # Step 2: Count web_search_call items
    search_calls = [o for o in resp.output if o.type == 'web_search_call']
    
    # Step 3: Enforce REQUIRED semantics
    if len(search_calls) == 0:
        # Retry with stronger provoker or fail closed
        raise RuntimeError("REQUIRED mode: No search performed despite provoker")
    
    return resp
```

## Key Findings

1. **The previous "empty output" issue was from the HTTP path**, not the SDK path
2. **The SDK path works perfectly** when using supported configurations
3. **GPT-5's limitation is ONLY with tool_choice:"required"**, not with web search itself
4. **The measurement framework correctly reveals this provider difference**

## Correct Documentation

### Truth Table Update
| Provider | Mode | Tool Choice | Actual Behavior |
|----------|------|-------------|-----------------|
| GPT-5 | UNGROUNDED | none | ✅ Works, returns content |
| GPT-5 | PREFERRED | auto | ✅ Works, searches when needed |
| GPT-5 | REQUIRED | auto + provoker | ⚠️ Workaround, not guaranteed |
| GPT-4o | REQUIRED | required | ✅ Works, forces search |

## References
- [OpenAI Cookbook: Web Search with Responses API](https://cookbook.openai.com/examples/responses_api/responses_example)
- [OpenAI Platform: GPT-5 Model](https://platform.openai.com/docs/models/gpt-5)
- [OpenAI API Reference: Responses](https://platform.openai.com/docs/api-reference/responses)

## Conclusion

GPT-5 **does** support web search via the Responses API, but with the limitation that it cannot use `tool_choice:"required"`. The workaround is to use `tool_choice:"auto"` with a provoker prompt and verify that searches occurred. This is a known provider behavior that the measurement framework successfully reveals.