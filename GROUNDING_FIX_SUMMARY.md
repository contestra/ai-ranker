# Grounding Fix Summary - Citation Validation Error

## Issue Status: RESOLVED ✅
**Date**: August 17, 2025  
**Environment Impact**: Both LOCAL (SQLite) and PRODUCTION (PostgreSQL)  
**Fix Type**: Code-level defensive validation

## Problem
Citations from Vertex AI were sometimes returned as URL strings instead of dictionary objects, causing Pydantic validation errors when constructing `RunResult`. This prevented grounding from working in the Templates feature.

## Root Cause
The Vertex AI API response format varies - sometimes `grounding_metadata.citations` contains bare URL strings rather than structured citation objects. The adapter expected only dictionaries, causing validation failures.

## Solution Implemented

### 1. Added Defensive Field Validator
**File**: `backend/app/llm/adapters/types.py`

Added a `field_validator` to the `RunResult` model that coerces string citations to proper dictionary format:

```python
@field_validator("citations", mode="before")
@classmethod
def _coerce_citations(cls, v):
    """Defensive validator: coerce list[str] → list[{"uri": ...}] to prevent production breakage"""
    if not v: 
        return []
    out = []
    for x in (v if isinstance(v, list) else [v]):
        if isinstance(x, dict): 
            out.append(x)
        elif isinstance(x, str): 
            out.append({"uri": x, "title": "No title", "source": "web_search"})
        else: 
            out.append({"note": str(x)})
    return out
```

### 2. Enabled gemini-2.0-flash for Grounding
**File**: `backend/app/llm/adapters/vertex_genai_adapter.py`

Added `gemini-2.0-flash` to the list of grounding-capable models (it does support grounding in europe-west4).

### 3. Fixed grounded_effective Field Mapping
**File**: `backend/app/api/prompt_tracking.py`

Updated to check both `grounded_effective` and `grounded` fields for compatibility between different adapter versions.

## Test Results

### [LOCAL] Environment Test
```
Model: gemini-2.0-flash
Region: europe-west4
Result: grounded_effective=True, citations_len=4, citations_are_dicts=True
Response: Contains current web information about electric vehicles
```

### [PROD] Environment Impact
The fix will work identically in production because:
1. The validation error occurred BEFORE database interaction
2. The field_validator handles the variance at the Pydantic model level
3. No database schema changes required

## Deployment Notes

1. **No Migration Required**: This is a code-only fix
2. **Backward Compatible**: The validator handles both string and dict citations
3. **Production Safe**: Defensive validation prevents future breakage

## Files Modified
- `backend/app/llm/adapters/types.py` - Added field_validator for citation coercion
- `backend/app/llm/adapters/vertex_genai_adapter.py` - Added gemini-2.0-flash to allowed models
- `backend/app/api/prompt_tracking.py` - Fixed grounded field mapping and added grounding_metadata to response

## Verification Steps
1. Run template with grounding_mode="web"
2. Check response includes:
   - `grounded=True`
   - `citations` array with dictionary entries
   - Current web information in response
3. Verify no Pydantic validation errors in logs