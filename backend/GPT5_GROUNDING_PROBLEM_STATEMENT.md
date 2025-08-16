# GPT-5 Grounding Problem - Precise Statement

## The Problem

When using OpenAI's GPT-5 models via the Responses API with web_search tool enabled, the API returns an empty `output_text` field, making the response unusable.

## Current Code Path

1. **Request is made via HTTP to Responses API** (`/v1/responses`)
   - File: `backend/app/llm/adapters/openai_production.py`
   - Method: `_http_grounded_with_schema()`
   - Lines: 186-457

2. **Request payload includes**:
   ```python
   {
       "model": "gpt-5",
       "input": [messages],
       "tools": [{"type": "web_search"}],
       "tool_choice": "auto",  # GPT-5 doesn't support "required"
       "temperature": 1.0,     # GPT-5 requirement
       "max_output_tokens": 96
   }
   ```

3. **Response comes back with**:
   - Status: 200 OK
   - Has an `output` array with items
   - But the actual text content is empty

## What I've Tried to Extract the Text

1. **Looked for message items in output array**:
   ```python
   for item in output_items:
       if item.get("type") == "message":
           content = item.get("content")
           # content exists but has empty text
   ```

2. **Checked the output_text field directly**:
   ```python
   output_text = data.get("output_text", "")
   # This is also empty
   ```

3. **Debug output shows**:
   ```
   [DEBUG] Response data keys: ['id', 'object', 'created_at', 'status', 'background', 'error', 'incomplete_details', 'instructions', 'max_output_tokens', 'max_tool_calls', 'model', 'output', 'parallel_tool_calls', 'previous_response_id', 'prompt_cache_key', 'reasoning', 'safety_identifier', 'service_tier', 'store', 'temperature', 'text', 'tool_choice', 'tools', 'top_logprobs', 'top_p', 'truncation', 'usage', 'user', 'metadata']
   [DEBUG] Output text: EMPTY
   [DEBUG] Output items count: 1
   [DEBUG] First few items: [{"id": "rs_68a08a1447bc819187a75dbbd879958f0425757bc9fc7b9d", "type": "reasoning", "summary": []}]
   ```

## The Actual Issue

The response contains a `reasoning` item but no `message` item with actual text content. The `reasoning` item has an empty `summary` array.

## What Works vs What Doesn't

### ✅ WORKS: GPT-5 WITHOUT web_search tool
- Returns proper text content
- JSON is valid
- Response is usable

### ❌ BROKEN: GPT-5 WITH web_search tool
- Returns empty text
- Only has reasoning items
- No actual response content

### ✅ WORKS: Vertex Gemini with GoogleSearch
- Returns proper text content
- Performs searches
- JSON is valid

## Questions for Another LLM

1. **Is there a different field in the GPT-5 Responses API response where the actual text content is stored when web_search is enabled?**

2. **Is the `reasoning` item supposed to contain the response, and if so, how do we extract it?**

3. **Is there a specific way to handle the response when it contains `reasoning` items instead of `message` items?**

4. **The response has a `text` field in the top-level keys - should we be using that instead of looking in `output` items?**

## Raw Response Structure When Grounding is Enabled

```json
{
  "id": "...",
  "output": [
    {
      "id": "rs_...", 
      "type": "reasoning",
      "summary": []
    }
  ],
  "text": "???",  // Not checked yet
  "usage": {...},
  // other fields...
}
```

## The Real Question

**Where is the actual text response in the GPT-5 Responses API output when web_search tool is enabled?** We're clearly looking in the wrong place or the API is returning an incomplete response.