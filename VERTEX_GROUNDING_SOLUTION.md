# Vertex Grounding Solution - Use Gemini 2.5

## The Problem
**Gemini 1.5 models DO NOT support Google Search grounding!**

## The Solution
Use **Gemini 2.5 Pro or Flash** which have full grounding support.

### Supported Models for Grounding
- ✅ `gemini-2.5-pro` - Full grounding support
- ✅ `gemini-2.5-flash` - Full grounding support  
- ✅ `gemini-2.0-flash` - Grounding support
- ❌ `gemini-1.5-pro-002` - NO grounding support
- ❌ `gemini-1.5-flash` - NO grounding support

### Required Configuration
```python
# 1. Use Gemini 2.5 model
model = "publishers/google/models/gemini-2.5-pro"

# 2. Temperature MUST be 1.0 for best grounding
temperature = 1.0

# 3. Attach GoogleSearch tool
tools = [Tool(google_search=GoogleSearch())]

# 4. Use prompts that require current info
prompt = "As of today, what's Singapore's GST rate? Include official source URL."
```

### How to Verify Grounding Happened
Look for these in the response:
- `grounding_metadata` field present
- `web_search_queries` array with search terms
- `grounding_attributions` with source citations
- `citations` with URLs

### Implementation Changes Needed
1. Update model from `gemini-1.5-pro-002` to `gemini-2.5-pro`
2. Ensure temperature is 1.0 for grounded tests
3. Check for grounding metadata in response
4. Only mark as grounded if metadata present

## Why This Matters
Without Gemini 2.5, the GoogleSearch tool is attached but **never invoked** because the model doesn't support it. This explains why our grounded tests were failing - we were using the wrong model version!