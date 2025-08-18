# Grounding and Routing Fix - Complete Summary

**Date**: August 17, 2025  
**Status**: ✅ FULLY RESOLVED  

## Critical Issues Fixed

### 1. Citation Validation Error ✅
**Problem**: Vertex AI returned citations as URL strings instead of dictionaries, causing Pydantic validation errors.

**Solution**: Added defensive `field_validator` to `RunResult` model that coerces strings to proper dictionary format:
```python
@field_validator("citations", mode="before")
def _coerce_citations(cls, v):
    # Converts list[str] → list[{"uri": ..., "title": ..., "source": ...}]
```

### 2. Model Routing Bug ✅
**Problem**: `gemini-2.5-pro` was being incorrectly routed to OpenAI API, causing "model does not exist" errors.

**Solution**: Created canonical model registry for single source of truth routing:
- `app/llm/model_registry.py` - Maps models to correct providers
- Updated `prompt_tracking.py` to use registry for routing decisions
- Added guards in adapters to prevent misrouting

### 3. Grounding Flag Propagation ✅
**Problem**: Templates with `grounding_mode="web"` were passing `use_grounding=False` to adapters.

**Solution**: Fixed grounding mode normalization and explicit boolean passing:
```python
needs_grounding = mode in ("WEB", "PREFERRED", "REQUIRED")
# Pass explicit boolean to adapters
use_grounding=needs_grounding
```

## Files Modified

1. **`backend/app/llm/adapters/types.py`**
   - Added citation coercion validator

2. **`backend/app/llm/model_registry.py`** (NEW)
   - Canonical model routing registry
   - Prevents ad-hoc string matching errors

3. **`backend/app/api/prompt_tracking.py`**
   - Uses model registry for routing
   - Fixed grounding flag propagation
   - Added routing logs for debugging

4. **`backend/app/llm/langchain_adapter.py`**
   - Added guards to prevent misrouting
   - Improved error messages

5. **`backend/app/llm/adapters/vertex_genai_adapter.py`**
   - Added gemini-2.0-flash to grounding-capable models
   - Fixed citation extraction from grounding_chunks

## Test Results

### Model Support Status
| Model | Provider | Grounding | Status |
|-------|----------|-----------|---------|
| gemini-2.5-pro | Vertex | ✅ Yes | ✅ WORKING |
| gemini-2.5-flash | Vertex | ✅ Yes | ✅ WORKING |
| gemini-2.0-flash | Vertex | ✅ Yes | ✅ WORKING |
| gpt-5 | OpenAI | ✅ Yes (Responses API) | ✅ WORKING |
| gpt-4o | OpenAI | ❌ No | ✅ WORKING |

### Frontend Testing
- **Templates Tab**: ✅ Create, edit, run templates
- **Results Tab**: ✅ View results with grounding metadata
- **Grounding**: ✅ Returns citations and web search results
- **Brand Detection**: ✅ Correctly identifies brand mentions

## Key Achievements

1. **No More Routing Errors**: Models always route to correct provider
2. **Grounding Works**: Web search returns citations for all capable models
3. **Production Ready**: All fixes are backward compatible, no migration needed
4. **Clear Error Messages**: Guards provide explicit errors if misrouting attempted

## Usage

### Creating Templates
```python
# Templates now work with all supported models
{
    "model_name": "gemini-2.5-pro",  # Correctly routes to Vertex
    "grounding_modes": ["web", "none"],  # Grounding properly activates
    "countries": ["US", "GB"],
    # ... other fields
}
```

### Running Templates
- Templates with `grounding_mode="web"` properly activate grounding
- Citations returned as dictionaries with uri, title, source
- Both Vertex (Gemini) and OpenAI (GPT-5) grounding work

## Deployment Notes

No database changes required - this is a code-only fix that's backward compatible.

## UI/UX Improvements (August 17, 2025)

### Grounding Mode Selection Fix
**Problem**: UI showed "Grounded (Auto)" and "Grounded (Required)" options for Gemini models, but Google's API doesn't support enforced grounding - the model always decides automatically.

**Solution**: Updated frontend to show model-appropriate grounding options:
- **Gemini models**: Only "Ungrounded (Off)" and "Grounded (On)" with explanatory note
- **OpenAI models**: Full options including "Auto" and "Required" modes

**Files Modified**:
- `frontend/src/components/PromptTracking.tsx` - Dynamic grounding options based on model selection

## Verification

To verify the fix:
1. Create new template with gemini-2.5-pro
2. Grounding options now show only "Off" and "On" (not "Auto"/"Required")
3. Run template with "On" selected
4. Check results show `grounded=True` with citations

The system is now fully operational with proper model routing, grounding support, and accurate UI.