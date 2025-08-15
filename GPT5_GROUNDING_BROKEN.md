# GPT-5 Grounding is COMPLETELY BROKEN - Documentation & Fix Plan

**Date**: August 15, 2025  
**Status**: CRITICAL BUG - UI shows grounding option that does nothing  
**Impact**: All GPT-5 "grounded" tests are actually ungrounded

## The Problem

The Templates section in our UI shows a "web" grounding option for GPT-5 models, but **IT DOES ABSOLUTELY NOTHING**. This is a serious bug that misleads users into thinking they're running grounded tests when they're not.

### What the UI Shows
```
Model: [GPT-5 ▼]
Grounding: [✓ none] [✓ web]  <-- This "web" option is a lie for GPT-5
```

### What Actually Happens

When you select "web" grounding for GPT-5:

1. **prompt_tracking.py** (line 531) calls:
   ```python
   response_data = await adapter.analyze_with_gpt4(
       full_prompt,
       model_name=request.model_name,
       temperature=temperature,
       seed=seed,
       context=context_message
   )
   # NOTE: No grounding parameter passed at all!
   ```

2. **langchain_adapter.py** `analyze_with_gpt4()` method:
   - Doesn't accept a grounding parameter
   - Doesn't configure any tools
   - Doesn't use the Responses API
   - Just calls the standard Chat Completions API

3. **Result**: "Grounded" and "ungrounded" GPT-5 tests are IDENTICAL

## Why This Happened

This appears to be a case of:
1. UI was built with the assumption that grounding would be implemented
2. Backend was never updated to support GPT-5's web search tools
3. No one noticed because GPT-5 often returns empty responses anyway

## What GPT-5 Actually Supports

OpenAI's GPT-5 models DO support native web search via the **Responses API**:

```python
# What we SHOULD be doing for grounded GPT-5:
import openai

response = openai.responses.create(
    model="gpt-5-chat-latest",
    input=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": als_block + prompt}
    ],
    tools=[{"type": "web_search"}],  # Native web search tool!
    tool_choice="auto",
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "locale_probe",
            "schema": {
                "type": "object",
                "properties": {
                    "vat_percent": {"type": "string"},
                    "plug": {"type": "array", "items": {"type": "string"}},
                    "emergency": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["vat_percent", "plug", "emergency"]
            }
        }
    },
    temperature=0
)
```

## Impact Analysis

### Tests Affected
- ALL GPT-5 "grounded" tests in Templates section
- Any historical data marked as "grounded" for GPT-5 is actually ungrounded
- Comparison metrics between GPT-5 and Gemini grounding are invalid

### User Trust Impact
- Users think they're testing grounded behavior but aren't
- Results showing "grounded" vs "ungrounded" differences for GPT-5 are spurious
- Any decisions made based on GPT-5 grounding performance are based on false data

## The Fix Plan

### 1. Immediate Actions
- Add warning to UI that GPT-5 grounding is not implemented
- Update documentation to reflect current broken state

### 2. Implementation Requirements

#### A. Update `langchain_adapter.py`
- Add new method `analyze_with_gpt5_responses()` using Responses API
- Support both grounded (with web_search tool) and ungrounded modes
- Implement structured JSON output for locale probes

#### B. Update `prompt_tracking.py`
- Route GPT-5 calls to new Responses API method when grounding enabled
- Pass grounding mode parameter properly
- Track tool_call_count for verification

#### C. Add Database Fields
```sql
ALTER TABLE prompt_results ADD COLUMN IF NOT EXISTS tool_call_count INTEGER DEFAULT 0;
ALTER TABLE prompt_results ADD COLUMN IF NOT EXISTS grounded_effective BOOLEAN DEFAULT FALSE;
ALTER TABLE prompt_results ADD COLUMN IF NOT EXISTS json_valid BOOLEAN DEFAULT TRUE;
ALTER TABLE prompt_results ADD COLUMN IF NOT EXISTS als_variant_id VARCHAR(50);
```

#### D. Update Frontend
- Show clear capability indicators for each model/mode combination
- Add validation that grounded tests actually used tools
- Display tool_call_count in results

### 3. Testing Requirements

Before declaring this fixed:
1. Verify GPT-5 ungrounded returns `tool_call_count = 0`
2. Verify GPT-5 grounded returns `tool_call_count > 0`
3. Verify structured JSON output works for locale probes
4. Run side-by-side comparison of grounded vs ungrounded for same prompts
5. Ensure grounded results actually differ from ungrounded

### 4. Validation Queries

```sql
-- Check if any GPT-5 "grounded" tests actually used tools
SELECT 
    model_name,
    grounding_mode,
    COUNT(*) as test_count,
    SUM(CASE WHEN tool_call_count > 0 THEN 1 ELSE 0 END) as actually_grounded
FROM prompt_results r
JOIN prompt_runs pr ON r.run_id = pr.id
WHERE model_name LIKE 'gpt-5%'
  AND grounding_mode = 'web'
GROUP BY model_name, grounding_mode;
-- Expected: actually_grounded should be 0 (proving it's broken)
```

## Why This Matters

1. **Data Integrity**: All historical GPT-5 "grounded" data is wrong
2. **User Trust**: The UI is lying about capabilities
3. **Comparison Validity**: Can't compare GPT-5 vs Gemini grounding if one doesn't work
4. **ALS Testing**: Can't properly test ALS efficacy without working grounding

## Semantic Consistency Requirements

When fixed, "grounded" must mean the same thing across all models:
- **The model itself triggers web search** (not manual retrieval)
- **Server-side execution** (not prompt injection)
- **Verifiable via tool_call_count** (not just trusting it worked)

## Code Locations to Fix

1. `backend/app/llm/langchain_adapter.py`
   - Add `analyze_with_gpt5_responses()` method
   - Support Responses API with tools

2. `backend/app/api/prompt_tracking.py`
   - Lines 529-537: Pass grounding parameter
   - Route to correct method based on grounding mode

3. `backend/app/llm/openai_adapter.py` (may need creation)
   - Implement Responses API client
   - Handle tool calls properly

4. `frontend/src/components/PromptTracking.tsx`
   - Add capability indicators
   - Show tool_call_count in results

## Recovery Plan for Historical Data

```sql
-- Mark all GPT-5 "grounded" tests as actually ungrounded
UPDATE prompt_results r
SET grounded_effective = FALSE,
    tool_call_count = 0
FROM prompt_runs pr
WHERE r.run_id = pr.id
  AND pr.model_name LIKE 'gpt-5%'
  AND pr.grounding_mode = 'web';

-- Add note to these records
UPDATE prompt_runs
SET notes = 'Grounding was not actually implemented for GPT-5 at time of test'
WHERE model_name LIKE 'gpt-5%'
  AND grounding_mode = 'web'
  AND DATE(created_at) < '2025-08-16';
```

## Definition of Done

This issue is fixed when:
1. ✅ GPT-5 grounded mode actually calls web search tools
2. ✅ Tool calls are tracked and verifiable
3. ✅ Structured JSON output works for locale probes
4. ✅ UI accurately reflects capabilities
5. ✅ Historical data is marked as incorrect
6. ✅ Documentation is updated
7. ✅ Tests prove grounded ≠ ungrounded for GPT-5

## Priority: CRITICAL

This is not a feature request - it's a **BUG FIX** for completely broken functionality that the UI claims exists.

---

**Remember**: "Grounded" without actual grounding is just lying to users.