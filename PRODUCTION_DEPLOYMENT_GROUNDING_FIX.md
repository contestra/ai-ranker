# Production Deployment: Vertex Adapter Grounding Fix

**Date**: August 17, 2025  
**Status**: ✅ Ready for Production  
**Risk Level**: Low (adapter-level only, no DB changes)

## What Changed (High-Impact Bits)

* **Single source of truth for citations:** Build citations **only from `grounding_chunks` URIs** (dedup), ignore `gm.citations`. This matches our spec for Gemini grounding.
* **Robust field access:** `_gget`/equivalent logic handles **camelCase & snake_case** (`webSearchQueries`/`web_search_queries`, `groundingChunks`/`grounding_chunks`).
* **Two-step discipline:** When GoogleSearch is attached, **don't** send `response_schema`; do a second pass to format JSON.
* **Grounded/Required policy:** Fail-closed if no grounding signals (queries/chunks).
* **Pydantic guard:** `RunResult` validator coerces any stray `list[str]` → `list[{"uri": ...}]`, preventing outages from future refactors. (Adapter still emits dicts.)

## Scope / Risk

* **No DB schema changes** (SQLite/PG unaffected).
* **Unified adapter path**: keep canonical file at `app/llm/adapters/vertex_genai_adapter.py`; legacy path is a shim only.
* **Model gating:** Allow grounding on **`gemini-2.5-pro` / `gemini-2.5-flash` / `gemini-2.0-flash`**; others raise.

## Files Modified

1. **`backend/app/llm/adapters/types.py`**
   - Added `field_validator` for citation coercion
   - Prevents production breakage from string citations

2. **`backend/app/llm/adapters/vertex_genai_adapter.py`**
   - Added `gemini-2.0-flash` to grounding-capable models
   - Maintains single source of truth for citations from chunks

3. **`backend/app/api/prompt_tracking.py`**
   - Fixed grounded_effective field mapping
   - Added grounding_metadata to response
   - Checks both "grounded_effective" and "grounded" for compatibility

## Rollout Checklist (PROD / Postgres)

### Config & Identity
- [x] Confirm region: `VERTEX_LOCATION=europe-west4`
- [x] Project: `contestra-ai`
- [x] Authentication: Application Default Credentials (ADC)
- [ ] Verify SA/WIF has: `roles/aiplatform.user`, `roles/serviceusage.serviceUsageConsumer`

### Adapter Invariants
- [x] Grounded call: **GoogleSearch tool attached, no schema**
- [x] Formatting pass: **no tools, response_schema on**
- [x] Required mode: throw if `grounded_effective=False`
- [x] Keep canonical adapter import; shim stays logic-free

### Logging & Observability
- [x] Log `model_version`/`response_id`, `project/location/model`
- [x] Frontend shows: grounded status, citations count, web queries
- [x] Backend logs validation errors for debugging

## Smoke Tests for Production

### 1) Ungrounded (ALS-only)
```bash
curl -X POST https://ai-ranker.fly.dev/api/prompt-tracking/run \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 14,
    "brand_name": "AVEA",
    "grounding_mode": "none"
  }'
```
**Expect**: `grounded_effective=false`, `tool_call_count=0`, `citations=[]`

### 2) Grounded (Web Search)
```bash
curl -X POST https://ai-ranker.fly.dev/api/prompt-tracking/run \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 14,
    "brand_name": "Tesla",
    "grounding_mode": "web"
  }'
```
**Expect**: `grounded_effective=true`, `tool_call_count>=1`, `citations` as **list of dicts**

### 3) Test Results Comparison

| Environment | Model | Grounded | Citations | Response Time | Status |
|------------|-------|----------|-----------|---------------|---------|
| [LOCAL/SQLite] | gemini-2.0-flash | ✅ True | 4 dicts | 16.3s | ✅ PASS |
| [PROD/Postgres] | gemini-2.0-flash | TBD | TBD | TBD | PENDING |

## PR Description

**Title:** fix: Vertex adapter citations validation and grounding support

**Summary**
- Build citations exclusively from `grounding_chunks` URIs (dedup)
- Handle camelCase/snake_case fields with `_gget` helper
- Enforce two-step for GoogleSearch + schema
- Required mode fail-closed if no signals
- Add `RunResult.citations` validator for defensive coercion

**Risk:** None to DB; adapter-level only. Shim unchanged.

**Validation**
- [LOCAL] ✅ Passed: Ungrounded / Auto / Required (Gemini 2.0-flash, 2.5-pro)
- [PROD] 🔄 To run: smoke tests above; verify `citations_len>0` and dict shape

**Testing Evidence**
```
[LOCAL] Result: grounded_effective=True, tool_call_count=2, citations_len=4, json_valid=N/A
Model/Region: gemini-2.0-flash / europe-west4
Notes: Citations properly formatted as dicts with uri/title/source
```

## Changelog Entry

### v1.x.x - Vertex Grounding Fix (2025-08-17)

**Fixed**
- Vertex: citations now derived from `grounding_chunks` (dicts, dedup)
- Enforce **no schema with GoogleSearch** (two-step pipeline)
- Required mode: fail when no grounding signals
- Pydantic: added `citations` coercion validator to harden boundary
- Unified adapter path; legacy import remains a shim

**Added**
- Support for `gemini-2.0-flash` with grounding in europe-west4
- Grounding metadata included in template run responses
- Field compatibility for both `grounded` and `grounded_effective`

## Notable Warnings Cleaned Up

If you still see Pydantic's "`schema` shadows BaseModel attr" warning, future fix:
```python
class RunRequest(BaseModel):
    response_schema: dict | None = Field(default=None, alias="schema")
    model_config = {"populate_by_name": True}
```

## Deployment Commands

```bash
# Deploy to Fly.io
cd backend
flyctl deploy

# Verify deployment
curl https://ai-ranker.fly.dev/api/health

# Run production smoke test
python test_production_grounding.py
```

## Monitoring Post-Deployment

1. Check logs for any validation errors: `flyctl logs`
2. Monitor grounding success rate in Templates tab
3. Verify citation format in Results tab
4. Check response times (expect 15-30s with grounding)

## Rollback Plan

If issues occur:
```bash
# Rollback to previous version
flyctl releases
flyctl deploy --image registry.fly.io/ai-ranker:v[PREVIOUS_VERSION]
```

---

**Sign-off**: Ready for production deployment. All LOCAL tests passing, defensive validation in place.