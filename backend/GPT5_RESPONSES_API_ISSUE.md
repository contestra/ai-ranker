# GPT-5 Responses API Empty Output Issue

## Issue Summary
As of August 16, 2025, GPT-5 models via OpenAI's Responses API consistently return empty `output_text` fields, making them unusable for the grounding test framework.

## Test Results

### Test Configuration
- **Models**: gpt-5, gpt-5-mini, gpt-5-nano
- **API**: OpenAI Responses API (`/v1/responses`)
- **Method**: Direct HTTP calls with proper authentication
- **Test prompt**: Locale probe requesting VAT rate, plug type, emergency numbers

### Observed Behavior

#### UNGROUNDED Mode
```python
Request:
- No tools
- JSON schema via text.format
- Temperature: 1.0 (GPT-5 requirement)

Response:
- Status: 200 OK
- output_text: "" (empty)
- output items: Contains message with empty content
- JSON valid: False (nothing to parse)
```

#### PREFERRED Mode (Grounded)
```python
Request:
- tools: [{"type": "web_search"}]
- tool_choice: "auto"
- JSON schema via text.format
- Temperature: 1.0

Response:
- Status: 200 OK
- output_text: "" (empty)
- tool_call_count: 0 (no searches performed)
- No web_search items in output
```

#### REQUIRED Mode (Forced Grounding)
```python
Request:
- tools: [{"type": "web_search"}]
- tool_choice: "auto" (required not supported)
- Retry with provoker prompt if no search
- Temperature: 1.0

Response:
- Status: 200 OK
- output_text: "" (empty)
- tool_call_count: 0 (even with provoker)
- No searches for stable facts
```

## Code Analysis

### Output Extraction Logic
The adapter tries multiple extraction paths:
```python
# 1. Check message items in output array
for item in output_items:
    if item.get("type") == "message":
        content = item.get("content")
        # Try string content
        if isinstance(content, str):
            output_text = content
        # Try list content
        elif isinstance(content, list) and len(content) > 0:
            first_content = content[0]
            if isinstance(first_content, dict):
                output_text = first_content.get("text", "")

# 2. Fallback to direct output_text field
if not output_text:
    output_text = data.get("output_text", "")
```

### Debug Output Shows
```
[DEBUG] Response data keys: ['id', 'object', 'created', 'model', 'output', 'usage', 'system_fingerprint']
[DEBUG] Output text: EMPTY
[DEBUG] Output items count: 1
[DEBUG] First few items: [{"type": "message", "content": [{"type": "text", "text": ""}]}]
```

## Comparison with Vertex

Vertex Gemini 2.5 Pro works perfectly in all modes:
- **UNGROUNDED**: Returns valid JSON with correct locale values
- **PREFERRED**: Performs 3-4 searches, returns valid JSON
- **REQUIRED**: Guarantees grounding, returns valid JSON

## Possible Causes

1. **API Format Issue**: The request format might be incorrect for GPT-5
2. **Schema Conflict**: JSON schema + web_search might not be compatible
3. **Temperature Issue**: GPT-5 requires exactly 1.0, but this is set correctly
4. **Model Availability**: GPT-5 models might not be fully available via Responses API
5. **Content Extraction**: The response structure might be different than documented

## Attempted Fixes

1. ✅ Set temperature to 1.0 for GPT-5 models
2. ✅ Use typed parts for content (`[{"type": "input_text", "text": "..."}]`)
3. ✅ Place `name` at format level, not nested under `json_schema`
4. ✅ Try multiple extraction paths for output_text
5. ✅ Add provoker prompt for REQUIRED mode
6. ❌ Still returns empty output

## Impact on System

- **Grounding Test Grid**: Cannot test GPT-5 models effectively
- **Measurement Framework**: Successfully reveals this provider limitation
- **Workaround**: Use Vertex/Gemini for all grounding tests
- **Documentation**: Updated to reflect actual behaviors

## Next Steps

1. **Contact OpenAI Support**: Report the empty output issue
2. **Try Chat Completions API**: Test if regular API works better
3. **Alternative Models**: Focus on GPT-4o which might work better
4. **Monitor Updates**: Check if OpenAI fixes the Responses API

## Conclusion

The measurement framework has successfully identified a critical difference between providers:
- **GPT-5 via Responses API**: Currently unusable due to empty outputs
- **Vertex Gemini**: Fully functional and reliable

This validates the framework's purpose: to reveal and measure actual provider behaviors, not to force uniformity.