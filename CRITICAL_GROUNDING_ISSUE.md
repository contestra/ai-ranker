# CRITICAL: Grounding Not Working from Templates Tab

## Executive Summary
**GROUNDING IS COMPLETELY BROKEN** when running templates through the Prompt Tracking API. This is a **CRITICAL ISSUE** because grounding (web search) is essential for getting current information about brands. Without it, the entire Templates feature is severely limited.

## The Problem - Exact Symptoms

### What Should Happen
1. User creates template with `grounding_modes=["web"]`
2. User runs template
3. Vertex AI performs Google Search grounding
4. Results contain:
   - `grounded_effective=True`
   - `citations` array with search results
   - `web_search_queries` showing what was searched
   - Current, web-sourced information in response

### What Actually Happens
1. User creates template with `grounding_modes=["web"]` ✅
2. User runs template ✅
3. **NO GROUNDING OCCURS** ❌
4. Results show:
   - `grounded_effective=False` 
   - `citations=[]` (empty)
   - `web_search_queries=[]` (empty)
   - Only training data in response (no current info)

## Test Evidence

```python
# Running template ID 14 with grounding_mode="web"
Result for US/web:
    Brand mentioned: None
    Confidence: 0
    Grounding successful: False  # <-- SHOULD BE TRUE!
    Web queries made: 0          # <-- SHOULD BE >0!
    Citations found: 0           # <-- SHOULD HAVE CITATIONS!
```

## The Call Chain (Where It's Breaking)

```
1. Frontend/API calls: POST /api/prompt-tracking/run
   └─> prompt_tracking.py::run_template()
       ├─> Checks grounding_mode == "web" → TRUE ✅
       └─> Calls adapter.analyze_with_gemini(
             prompt,
             grounding_mode == "web",  # Passes True ✅
             model_name="gemini-2.0-flash",
             ...
           )
           └─> langchain_adapter.py::analyze_with_gemini()
               ├─> use_grounding parameter = True ✅
               └─> SOMEWHERE HERE IT FAILS TO ACTIVATE GROUNDING ❌
                   └─> Returns response with NO grounding metadata
```

## Critical Code Locations

### 1. Where grounding flag is passed (prompt_tracking.py:526)
```python
if model_name in ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]:
    response_data = await adapter.analyze_with_gemini(
        full_prompt,
        grounding_mode == "web",  # THIS SHOULD BE True when grounding_mode="web"
        model_name=model_name,
        temperature=temperature,
        seed=seed,
        context=context_message
    )
```

### 2. Where grounding should be activated (langchain_adapter.py:analyze_with_gemini)
```python
async def analyze_with_gemini(self, prompt, use_grounding=False, model_name="gemini-2.5-pro", ...):
    # use_grounding=True should trigger Vertex grounding
    # BUT IT'S NOT WORKING!
```

### 3. Where Vertex adapter should be called
The analyze_with_gemini method should:
- If use_grounding=True → Use VertexGenAIAdapter with grounding
- If use_grounding=False → Use direct Gemini API

## Suspected Root Causes

### Theory 1: Wrong Adapter Being Used
- When use_grounding=True, it might still be using direct Gemini API instead of Vertex
- Direct Gemini API doesn't support GoogleSearch grounding
- Check: Is VertexGenAIAdapter actually being instantiated and called?

### Theory 2: Fallback Silently Failing
- VertexGenAIAdapter might be failing (auth/region issues)
- Code falls back to direct API without grounding
- No error is raised, just silently degrades to no grounding

### Theory 3: Model Name Incompatibility
- gemini-2.0-flash might not support grounding in europe-west4
- Or the model name format is wrong for Vertex

### Theory 4: Grounding Flag Not Propagating
- The use_grounding=True might not be reaching the actual Vertex call
- Check the entire chain from analyze_with_gemini → VertexGenAIAdapter.run()

## What Works (For Comparison)

### Direct Vertex Test - WORKS ✅
```python
# Direct call to Vertex adapter
adapter = VertexGenAIAdapter()
req = RunRequest(
    grounding_mode=GroundingMode.REQUIRED,
    user_prompt="What is the current VAT rate in Germany?",
    ...
)
result = adapter.run(req)
# Result: grounded=True, citations present ✅
```

### Direct Google GenAI SDK - WORKS ✅
```python
client = genai.Client(vertexai=True, project="contestra-ai", location="europe-west4")
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="What is the current VAT rate?",
    config=GenerateContentConfig(
        tools=[Tool(google_search=GoogleSearch())]  # Grounding enabled
    )
)
# Result: Returns grounding_chunks with citations ✅
```

## Debug Steps for Next LLM

1. **Add logging in langchain_adapter.py::analyze_with_gemini()**
   - Log: "use_grounding={use_grounding}"
   - Log: "About to call Vertex" or "About to call Direct API"
   - Log: What adapter is actually being used

2. **Check if VertexGenAIAdapter is being instantiated**
   - Is the code path reaching VertexGenAIAdapter?
   - Or is it always using direct Gemini API?

3. **Trace the grounding flag**
   - From prompt_tracking.py (grounding_mode == "web")
   - Through analyze_with_gemini (use_grounding parameter)
   - To actual Vertex call (GroundingMode.REQUIRED or Tool(google_search=...))

4. **Check for silent fallbacks**
   - Look for try/except blocks that might be swallowing errors
   - Check if there's a fallback from Vertex to direct API

5. **Verify model compatibility**
   - Test if gemini-2.0-flash supports grounding
   - Try with gemini-2.5-pro instead

## The Fix Priority

This is **PRIORITY 1** - Without grounding:
- Templates can't get current information
- Brand detection uses only training data (outdated)
- The entire value proposition of "web-grounded brand analysis" is broken
- Users expect web search when they select grounding_mode="web"

## Files to Examine

1. `backend/app/llm/langchain_adapter.py` - The analyze_with_gemini method
2. `backend/app/api/prompt_tracking.py` - Lines 520-530 where it calls analyze_with_gemini
3. `backend/app/llm/adapters/vertex_genai_adapter.py` - The working Vertex adapter
4. Check for any fallback logic that bypasses Vertex when grounding is requested

## Success Criteria

When fixed, running a template with grounding_mode="web" should:
1. Return `grounded_effective=True`
2. Have non-empty `citations` array with dict entries
3. Show `web_search_queries` with actual search queries
4. Provide current web-based information in the response
5. Take longer to run (30-60s) due to web search overhead

---

**CRITICAL**: This is not a nice-to-have. Grounding is ESSENTIAL for the Templates feature to work as designed. Without it, the system cannot provide current information about brands.