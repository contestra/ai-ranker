# Prompter V6 Rollout Checklist
## Production Deployment Guide for Prompt De-dup + Provider Versioning

**Version**: V6 Bulletproof  
**Date**: August 14, 2025  
**Stack**: Fly.io, FastAPI, PostgreSQL (prod) / SQLite (dev), Redis (optional), LangChain

---

## 0) Pre-Flight Checklist (Once)

### Configuration
- [ ] **Code freeze**: V6 schema, API contracts, and utilities are stable in main
- [ ] **Secrets available**:
  - [ ] `OPENAI_API_KEY` (for GPT models)
  - [ ] `GOOGLE_API_KEY` (for Gemini)
  - [ ] `ANTHROPIC_API_KEY` (if using Claude)
  - [ ] `DB_URL` (PostgreSQL for prod, SQLite for dev)
  - [ ] `REDIS_URL` or `UPSTASH_REDIS_URL` (optional for idempotency)
  - [ ] `FLY_API_TOKEN` (for deployment)

### Feature Controls
- [ ] **Feature flag**: `PROMPTER_V6_ENABLED=true` (gates UI features)
- [ ] **Kill switch**: `PROMPTER_PROBE_DISABLED=true` (skip provider probes if needed)
- [ ] **ALS protection**: Verify `SYSTEM_INTEGRITY_RULES.md` is understood by team

### Safety Verification
- [ ] Confirm ALS files untouched: `backend/app/services/als/`
- [ ] Verify langchain_adapter.py lines 180-186, 292-296 unchanged
- [ ] Check brands table is READ-ONLY in new code

---

## 1) Database Migration

### Development (SQLite)
```bash
# Run idempotent schema
cd backend
python db/sqlite_bootstrap.py

# Verify indexes created
sqlite3 ai_ranker.db "SELECT name FROM sqlite_master WHERE type='index';"
# Should see: ux_templates_org_ws_confighash_active, ux_versions_org_ws_tpl_providerkey, etc.
```

### Staging (PostgreSQL)
```bash
# 1. Backup staging database
pg_dump $STAGING_DB_URL > staging_backup_$(date +%Y%m%d).sql

# 2. Run Alembic migration
alembic upgrade head

# 3. Verify partial unique index
psql $STAGING_DB_URL -c "
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename='prompt_templates' 
AND indexdef LIKE '%WHERE deleted_at IS NULL%';
"

# 4. Verify version uniqueness
psql $STAGING_DB_URL -c "\d+ prompt_versions;"
# Expect: UNIQUE(org_id, workspace_id, template_id, provider_version_key)
```

---

## 2) Application & Services Setup

### API Server
- [ ] FastAPI starts with environment variables set
- [ ] Router mounted: `/api/prompt-templates`
- [ ] Health endpoint responds: `/api/prompt-templates/health`

### Redis (Optional)
```bash
# Test Redis connection
redis-cli -u $REDIS_URL PING
# Expect: PONG

# Test TTL
redis-cli -u $REDIS_URL SET test:key "1" EX 60
redis-cli -u $REDIS_URL TTL test:key
# Expect: ~59
```

### Idempotency Keys Format
- Probe: `probe:{org}:{workspace}:{template}:{provider}:{model}:{YYYYMMDDHH}`
- Run: `run:{org}:{workspace}:{template}:{version}:{country}:{YYYYMMDDHH}`

---

## 3) Staging Smoke Tests

### A. Template Creation (Dedup by Brand)
```bash
# First create → 201
curl -X POST $API_URL/api/prompt-templates \
  -H 'Content-Type: application/json' \
  -d '{
    "org_id": "default",
    "workspace_id": "workspace-avea-001",
    "name": "AVEA Brand Analysis",
    "system_instructions": "Be concise and accurate",
    "user_prompt_template": "What is AVEA known for?",
    "country_set": ["CH", "US"],
    "model_id": "gpt-4o",
    "inference_params": {"temperature": 0.7, "max_tokens": 1000}
  }'
# Save returned template_id

# Duplicate in same workspace → 409
# (Same request again should return 409 Conflict)

# Different workspace → 201 (allowed)
# (Change workspace_id to "workspace-other-001" → should succeed)
```

### B. Duplicate Detection
```bash
curl -X POST $API_URL/api/prompt-templates/check-duplicate \
  -H 'Content-Type: application/json' \
  -d '{ ...same payload as above... }'
  
# Expect: {"exact_match": true, "template_id": "..."}
```

### C. Version Capture (All Providers)

#### OpenAI (GPT-4o)
```bash
curl -X POST $API_URL/api/prompt-templates/{template_id}/ensure-version \
  -H 'Content-Type: application/json' \
  -d '{
    "org_id": "default",
    "workspace_id": "workspace-avea-001",
    "provider": "openai",
    "model_id": "gpt-4o",
    "inference_params": {"temperature": 0, "max_tokens": 1}
  }'
# Expect: provider_version_key like "fp_abc123..."
```

#### Modern OpenAI Models (o3, omni)
```bash
# Test with o3
curl -X POST $API_URL/api/prompt-templates/{template_id}/ensure-version \
  -d '{"model_id": "o3", ...}'
# Should correctly identify as OpenAI

# Test with omni-vision
curl -X POST $API_URL/api/prompt-templates/{template_id}/ensure-version \
  -d '{"model_id": "omni-vision", ...}'
# Should correctly identify as OpenAI
```

#### Gemini
```bash
curl -X POST $API_URL/api/prompt-templates/{template_id}/ensure-version \
  -d '{
    "provider": "google",
    "model_id": "gemini-2.0-flash",
    ...
  }'
# Expect: provider_version_key like "gemini-2.0-flash-001"
```

#### Anthropic
```bash
curl -X POST $API_URL/api/prompt-templates/{template_id}/ensure-version \
  -d '{
    "provider": "anthropic",
    "model_id": "claude-3-opus-20240229",
    ...
  }'
# Expect: provider_version_key = model_id
```

### D. Concurrency Testing
```bash
# Run in parallel (use GNU parallel or similar)
parallel -j 5 curl -X POST $API_URL/api/prompt-templates \
  -H 'Content-Type: application/json' \
  -d '{ ...identical payload... }' ::: {1..5}

# Expect: Exactly 1 success (201), 4 conflicts (409)
```

### E. Result Persistence
```bash
# Execute a template run
curl -X POST $API_URL/api/prompt-templates/{template_id}/run \
  -H 'Content-Type: application/json' \
  -d '{
    "country": "CH",
    "brand_name": "AVEA Life",
    "rendered_prompt": "What supplements does AVEA Life offer?",
    "use_grounding": false,
    "analysis_scope": "brand+products"
  }'

# Verify in database:
# - prompt_results has new row
# - request/response JSONs populated
# - provider_version_key set
# - system_fingerprint present (for OpenAI)
# - rendered_prompt_sha256 calculated
# - analysis_config contains scope and timestamp
```

---

## 4) Canary Deployment on Fly.io

### Deploy Canary
```bash
# Set environment for canary
flyctl secrets set PROMPTER_V6_ENABLED=true --app ai-ranker-canary
flyctl secrets set PROMPTER_PROBE_DISABLED=false --app ai-ranker-canary

# Deploy single canary instance
flyctl deploy --app ai-ranker-canary --strategy canary

# Monitor logs
flyctl logs --app ai-ranker-canary
```

### Abort Conditions (Stop if any occur)
- [ ] Probe failure rate > 10% for 5 minutes
- [ ] API 5xx rate > 1% for 5 minutes
- [ ] Database unique violations causing 500s (should be 409s)
- [ ] ALS endpoints showing any errors

---

## 5) Observability Setup

### Structured Log Fields
```json
{
  "org_id": "...",
  "workspace_id": "...",
  "template_id": "...",
  "version_id": "...",
  "provider": "openai|google|anthropic",
  "model_id": "gpt-4o|gemini-2.0|claude-3",
  "provider_version_key": "fp_xxx|gemini-xxx|claude-xxx",
  "status": "success|error",
  "latency_ms": 123,
  "action": "create_template|ensure_version|run_template"
}
```

### Key Metrics Dashboard
- **API Health**:
  - Requests/sec by endpoint
  - P95 latency
  - 4xx/5xx rates
  - 409 rate (duplicate blocks)

- **Provider Health**:
  - Success rate by provider
  - Fingerprint capture rate
  - "Unknown" provider percentage
  - Probe timeouts

- **Database Health**:
  - Inserts/sec per table
  - Unique constraint violations
  - Query latency P95

- **Results Quality**:
  - Results created/min
  - % with system_fingerprint (OpenAI)
  - % with valid provider_version_key

---

## 6) Production Alerts

### Critical Alerts (Page immediately)
- [ ] API 5xx rate ≥ 1% (5-min window)
- [ ] Results write failures > 1/min
- [ ] ALS endpoints returning errors
- [ ] Database deadlocks > 3/min

### Warning Alerts (Notify team)
- [ ] Probe failure rate ≥ 10% per provider
- [ ] Ensure-version latency P95 ≥ 3s
- [ ] Redis unreachable > 2 min
- [ ] "Unknown" provider > 10% of requests
- [ ] Missing fingerprints for OpenAI > 20%

---

## 7) Quick Fix Runbooks

### A. Provider Probe Failures
```bash
# Option 1: Disable probes temporarily
flyctl secrets set PROMPTER_PROBE_DISABLED=true --app ai-ranker

# Option 2: Switch to stable model
# Change gpt-4o to gpt-4o-mini if issues

# Option 3: Check provider status
# Visit: status.openai.com, status.anthropic.com
```

### B. High 5xx Rate
```bash
# Check logs for stack traces
flyctl logs --app ai-ranker | grep ERROR

# Common fixes:
# - JSON serialization issues (SQLite vs PostgreSQL)
# - Missing imports
# - Database connection pool exhausted

# Emergency: Disable V6 features
flyctl secrets set PROMPTER_V6_ENABLED=false --app ai-ranker
```

### C. High 409 Rate
- This is NORMAL if users are creating duplicates
- Verify UI is showing duplicate warnings
- Consider adding user education tooltips

### D. Redis Down
```bash
# System continues without idempotency guards
# Monitor for duplicate version captures
# Consider temporary in-memory cache
```

### E. Database Contention
```bash
# Check for lock waits
psql $DB_URL -c "SELECT * FROM pg_stat_activity WHERE wait_event_type = 'Lock';"

# Reduce concurrency if needed
# Add connection pooling limits
```

---

## 8) Production Rollout Steps

### Phase 1: Database
1. [ ] Run Alembic migration on production
2. [ ] Verify indexes created successfully
3. [ ] Take database snapshot for rollback

### Phase 2: Canary (Day 1)
1. [ ] Deploy 1 canary instance with V6
2. [ ] Route 5% traffic to canary
3. [ ] Monitor for 2 hours
4. [ ] Check all smoke tests pass

### Phase 3: Gradual Rollout (Day 2-3)
1. [ ] Increase to 25% traffic (4 hours)
2. [ ] Increase to 50% traffic (4 hours)
3. [ ] Full rollout to 100%
4. [ ] Keep alerts heightened for 48 hours

### Phase 4: Validation (Day 4)
1. [ ] Verify dedup working across brands
2. [ ] Check all providers capturing versions
3. [ ] Confirm results persistence complete
4. [ ] Review metrics dashboard

---

## 9) Post-Deploy Validation

### Functional Tests
- [ ] Create template in Brand A → 201
- [ ] Create same config in Brand B → 201
- [ ] Create duplicate in Brand A → 409
- [ ] Modern models work (o3, omni-vision)
- [ ] Gemini fallbacks work (modelVersion → model → model_name)
- [ ] Results have full audit trail

### Performance Tests
- [ ] API P95 latency < 500ms
- [ ] Version capture < 2s
- [ ] No memory leaks after 24 hours
- [ ] Database connections stable

### ALS Verification (CRITICAL)
- [ ] Test all 8 countries in ALS
- [ ] Verify locale inference unchanged
- [ ] Check system prompts intact

---

## 10) Rollback Plan

### Quick Rollback (< 5 min)
```bash
# Option 1: Feature flag
flyctl secrets set PROMPTER_V6_ENABLED=false --app ai-ranker

# Option 2: Redeploy previous version
flyctl deploy --image ai-ranker:v5 --app ai-ranker
```

### Database Rollback (if needed)
```bash
# Migrations are additive, but if needed:
alembic downgrade -1

# Or restore from snapshot
pg_restore -d $DB_URL production_backup_pre_v6.sql
```

---

## 11) Special Considerations

### Modern Model Support
- **o3, o4, omni-*** models now properly detected as OpenAI
- Test with latest model releases before they go GA

### Gemini Response Variations
- Adapter may return modelVersion, model, or model_name
- V6 handles all three with fallback chain

### Azure OpenAI
- May not return system_fingerprint
- Falls back to "unknown" - this is expected
- Document for support team

### SQLite Dev Environment
- Indexes are idempotent (IF NOT EXISTS)
- Can safely re-run schema multiple times
- UUID strings ensure dev/prod parity

---

## 12) Success Criteria

### Day 1 Success
- [ ] Zero ALS errors
- [ ] < 1% 5xx rate
- [ ] Dedup working (409s for duplicates)
- [ ] All providers capturing versions

### Week 1 Success
- [ ] 17 duplicate prompts eliminated
- [ ] Version history visible in UI
- [ ] No performance degradation
- [ ] No increase in support tickets

### Month 1 Success
- [ ] Historical version tracking established
- [ ] Cost savings from reduced duplicate API calls
- [ ] Ready for alias system integration
- [ ] Team confident in system stability

---

## Sign-offs

- [ ] Engineering Lead: _______________ Date: _______________
- [ ] DevOps Lead: _______________ Date: _______________
- [ ] Product Owner: _______________ Date: _______________
- [ ] On-call Engineer: _______________ Date: _______________

---

## Emergency Contacts

- **On-call Engineer**: [Phone/Slack]
- **Database Admin**: [Phone/Slack]
- **Provider Support**:
  - OpenAI: support.openai.com
  - Google Cloud: cloud.google.com/support
  - Anthropic: support.anthropic.com
- **Fly.io Support**: fly.io/docs/about/support

---

*Last Updated: August 14, 2025*  
*Version: V6 Bulletproof*  
*Status: Ready for Production Rollout*