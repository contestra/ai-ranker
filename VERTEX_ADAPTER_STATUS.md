# Vertex AI Adapter - Status Report
**Date**: August 17, 2025  
**Status**: ✅ PRODUCTION READY

## Executive Summary
Successfully implemented all of ChatGPT's hardening recommendations for the Vertex GenAI adapter. The adapter now properly handles grounding, citations are guaranteed to be dictionaries (no more string contamination), and all edge cases are covered.

## Key Problems Solved

### 1. ✅ Citation String Contamination (FIXED)
**Problem**: Citations were being passed as strings to Pydantic RunResult, causing validation errors.

**Root Cause**: 
- Vertex doesn't have a `citations` attribute in `grounding_metadata`
- Citations must be extracted from `grounding_chunks`
- SDK returns both camelCase and snake_case field names

**Solution**:
- Build citations EXCLUSIVELY from `grounding_chunks` 
- Never read `gm.citations` (doesn't exist reliably)
- Implemented `_gget()` helper to handle both camelCase/snake_case
- Citations deduplicated by URI
- All citations guaranteed to be dictionaries

### 2. ✅ JSON Schema + Grounding Conflict (FIXED)
**Problem**: Vertex AI cannot use JSON schema and GoogleSearch grounding simultaneously.

**Solution**:
- Separated grounding and schema modes completely
- When grounding ON → no response_schema, use text/plain
- When schema required → tools OFF
- Clear warning logged when both requested

### 3. ✅ Grounding Detection (FIXED)
**Problem**: Grounding was reported as False even when searches occurred.

**Root Cause**:
- Indentation bug in signal extraction
- Not checking all grounding evidence (chunks, queries)

**Solution**:
- Fixed indentation - grounding computation outside conditionals
- Evidence of grounding = chunks OR queries (not just citations)
- Proper tool_calls counting

## Implementation Details

### Core Files Modified
```
backend/app/llm/adapters/vertex_genai_adapter.py  # Main adapter implementation
backend/app/llm/vertex_genai_adapter.py           # Deprecation shim for backward compatibility
```

### Key Functions Added/Modified

#### 1. `_gget()` - Universal field accessor
```python
def _gget(obj: Any, names: List[str], default=None):
    """Get attr or key from obj trying several name variants (attr or dict)."""
    # Handles both camelCase and snake_case
    # Works with dicts and objects
```

#### 2. `_citations_from_chunks()` - Single source of truth
```python
def _citations_from_chunks(chunks) -> List[Dict[str, Any]]:
    """Build citations exclusively from grounding chunks (dedup by URI)"""
    # Returns guaranteed list[dict]
    # Deduplicates by URI
```

#### 3. `_vertex_grounding_signals()` - Robust extraction
```python
def _vertex_grounding_signals(resp) -> Dict[str, Any]:
    """Extract grounding signals from Vertex response"""
    # Handles camelCase/snake_case
    # Never raises exceptions
    # Returns normalized data
```

#### 4. `_assert_vertex_shape()` - Runtime validation
```python
def _assert_vertex_shape(signals: Dict[str, Any]) -> None:
    """Assert that grounding signals have correct shape"""
    # Blocks any string leak regressions
    # Called before RunResult construction
```

## Test Results

### Unit Tests ✅
- Mock data with camelCase fields: **PASS**
- Deduplication by URI: **PASS**
- All citations are dicts: **PASS**
- No grounding metadata handling: **PASS**

### Integration Tests ✅
- Real Vertex API with grounding: **PASS**
- Real Vertex API without grounding: **PASS**
- JSON schema output (without grounding): **PASS**
- REQUIRED vs PREFERRED modes: **PASS**

### Test Output Example
```
Testing with grounding:
  Found: 1 queries, 4 chunks, 4 unique citations
  Grounded: True
  Tool calls: 1
  Citations: 4
  All citations are dicts: True
  First citation type: dict
  First citation keys: ['uri', 'title', 'source']
```

## API Configuration

### Authentication
- **Method**: Application Default Credentials (ADC)
- **Project**: contestra-ai
- **Location**: europe-west4 (REQUIRED - other regions may fail)
- **Models**: gemini-2.0-flash (working), gemini-2.5-pro/flash (when available)

### Vendor Names
- **OpenAI**: Use vendor="openai" for GPT-5
- **Google/Vertex**: Use vendor="google" for Gemini via Vertex AI
- **Note**: Do NOT use vendor="vertex" - it's not recognized

## Current System State

### Frontend ✅
- Running on port 3001
- Accessible at http://localhost:3001

### Backend ✅
- Running on port 8000
- Health endpoint: http://localhost:8000/api/health
- Vertex status: "healthy" with WEF authentication

### Working Features
1. **Brand Entity Strength Analysis** - Uses Vertex for grounding
2. **Prompt Tracking** - Templates support Gemini models
3. **ALS (Ambient Location Signals)** - Working with all 8 countries
4. **Grounding** - Properly extracts citations from Vertex responses

## Production Checklist (from ChatGPT)

### ✅ Completed
- [x] Robust field access (camelCase/snake_case)
- [x] Citations from chunks only
- [x] Shape assertions before persistence
- [x] Deduplication by URI
- [x] JSON schema + grounding separation
- [x] Fail-closed for REQUIRED mode
- [x] Unit tests for extraction logic

### ⏳ Recommended Next Steps
- [ ] Add timeout and retry logic (currently in todo list)
- [ ] Add metrics for grounding effectiveness
- [ ] Log response_api, model_version, response_id
- [ ] Add frontend columns for grounding metadata
- [ ] Set up Analytics/BigQuery tracking

## Key Invariants Maintained

1. **Citations are ALWAYS dictionaries** - Never strings
2. **Grounding evidence** = chunks OR queries (not just citations field)
3. **Single source of truth** - Citations built only in `_vertex_grounding_signals()`
4. **No co-sending** - Never send JSON schema + GoogleSearch together
5. **Fail closed** - REQUIRED mode raises error if no grounding detected

## Known Limitations

1. **Vertex Constraint**: Cannot use JSON schema with GoogleSearch grounding
2. **Regional**: Must use europe-west4 (us-central1 returns 404s)
3. **Model Availability**: gemini-2.0-flash works, newer versions pending
4. **Token Usage**: Vertex doesn't expose token counts like OpenAI

## Test Commands

```bash
# Test extraction logic standalone
cd vertex-auth
python test_vertex_standalone_final.py

# Test API integration
python test_frontend_api.py

# Test with real Vertex
python test_vertex_grounding.py
```

## Summary
The Vertex adapter is now production-ready with all of ChatGPT's recommendations implemented. Citations are guaranteed to be dictionaries, grounding detection works reliably, and the JSON schema conflict is properly handled. The system correctly supports only OpenAI (GPT-5) and Google (Gemini via Vertex) as intended.