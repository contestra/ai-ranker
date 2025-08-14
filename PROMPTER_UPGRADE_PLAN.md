# Prompter Upgrade Plan - Final Implementation Approach

## ⚠️ CRITICAL: Pre-Upgrade Checkpoint
**Date**: August 14, 2025  
**Status**: System fully operational, committing before Prompter rebuild  
**Scope**: ONLY Prompter feature - NO changes to ALS or other features

## Problem Statement
The Prompter feature currently allows unlimited duplicate prompts with different names, resulting in:
- 17+ functionally identical prompts that produce identical results
- No tracking of model fingerprints/versions
- Inability to distinguish between wasteful duplicates and legitimate re-tests after model updates
- Confused users and wasted storage

## Solution Overview
Implement intelligent deduplication that:
1. Blocks exact duplicates (same config + same model version)
2. Allows re-testing when model version changes (tracked via fingerprint)
3. Makes model versions visible to users
4. Maintains complete audit trail with soft-delete

## Implementation Approach - Clean Slate

### What Will Be Changed
**Tables to DROP and recreate**:
- `prompt_templates`
- `prompt_runs` 
- `prompt_results`
- (Optional) `prompt_versions` - new table

### What Will NOT Be Changed
**Tables to PRESERVE completely**:
- `brands`
- `entity_mentions`
- `countries`
- All ALS-related tables
- All entity strength tables
- All other feature tables

## Technical Architecture

### Core Concepts
1. **Templates** = Unique prompt configurations (without fingerprint)
2. **Versions** = Template + provider version key (discovered at runtime)
3. **Results** = Execution results tied to specific versions

### Uniqueness Definition
A unique prompt is defined by the **config hash** of:
- `system_instructions` (normalized)
- `user_prompt_template` (normalized)
- `country_set` (sorted ISO-3166-1 codes)
- `model_id` (e.g., gpt-4o, gemini-2.5-pro)
- `inference_params` (temperature, top_p, max_tokens, etc.)
- `tools_spec` (preserving order - critical!)
- `response_format` (including schema if used)
- `grounding_profile` (profile_id, snapshot, retrieval params)
- Pre/post processing pipeline IDs

### Provider Version Keys
- **OpenAI**: `system_fingerprint` (from response only)
- **Gemini**: `modelVersion` or `Model.version`
- **Anthropic**: Model ID itself (already versioned)

## Database Schema (Fresh Start)

```sql
-- Templates (no fingerprint here)
CREATE TABLE prompt_templates (
  id UUID PRIMARY KEY,
  org_id UUID NOT NULL,  -- if multi-tenant
  name TEXT NOT NULL,
  system_instructions TEXT NOT NULL,
  user_prompt_template TEXT NOT NULL,
  country_set TEXT[] NOT NULL,
  model_id TEXT NOT NULL,
  inference_params JSONB NOT NULL,
  tools_spec JSONB NOT NULL,
  response_format JSONB NOT NULL,
  grounding_profile_id UUID,
  config_hash TEXT NOT NULL,
  config_canonical_json JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  deleted_at TIMESTAMPTZ  -- for soft delete
);

-- Unique within org (or globally if single-tenant)
CREATE UNIQUE INDEX ux_templates_confighash 
ON prompt_templates (config_hash) 
WHERE deleted_at IS NULL;

-- Versions (one per provider version)
CREATE TABLE prompt_versions (
  id UUID PRIMARY KEY,
  template_id UUID REFERENCES prompt_templates(id),
  provider TEXT NOT NULL,
  provider_version_key TEXT NOT NULL,
  fingerprint_captured_at TIMESTAMPTZ,
  first_seen_at TIMESTAMPTZ DEFAULT now(),
  last_seen_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (template_id, provider_version_key)
);

-- Results
CREATE TABLE prompt_results (
  id UUID PRIMARY KEY,
  template_id UUID REFERENCES prompt_templates(id),
  version_id UUID REFERENCES prompt_versions(id),
  provider_version_key TEXT,
  system_fingerprint TEXT,  -- raw value
  request JSONB NOT NULL,
  response JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

## API Changes

### 1. Template Creation
**POST /api/prompt-templates**
- Compute config_hash server-side
- Check for duplicates
- Return 409 if exact match exists
- Store canonical JSON for debugging

### 2. Version Management
**POST /api/prompt-templates/{id}/ensure-version**
- Run 1-token probe to capture fingerprint
- UPSERT version record
- Return version_id

### 3. Duplicate Detection
**GET /api/prompt-templates/check-duplicate**
- Real-time checking during form input
- Returns exact matches and similar prompts

## Frontend Changes

### Template Creation Form
- Debounced duplicate detection (500ms)
- Traffic light indicators:
  - 🔴 Red: Exact duplicate exists (block)
  - 🟡 Amber: Template exists, newer model available
  - 🟢 Green: New unique template
- "Use Existing" button for duplicates
- "Test with Latest Model" for version updates

### Template List View
- Show model fingerprint badges
- Group versions under templates
- Version timeline visualization
- Performance comparison across versions

## Implementation Phases

### Phase 1: Database (2 hours)
- Drop existing Prompter tables
- Create new schema with proper constraints
- Add soft-delete support

### Phase 2: Backend API (3 hours)
- Canonicalization utility
- Duplicate detection endpoints
- Version management
- Update execution flow

### Phase 3: Frontend UI (4 hours)
- Duplicate detection in forms
- Version badges and timeline
- Traffic light system
- Library view with deduplication

### Phase 4: Clean Slate (30 minutes)
- Drop old tables
- Create new tables
- No migration needed!

## Testing Strategy

### Unit Tests
- Config hash stability
- Canonicalization rules
- Version creation logic

### Integration Tests
- Duplicate blocking
- Version tracking
- Provider fingerprint capture

### UI Tests
- Traffic light states
- Form validation
- Version navigation

## Success Metrics
- Zero exact duplicates allowed
- Model fingerprints visible everywhere
- Clear user understanding of when re-testing is allowed
- 80% reduction in duplicate templates
- Complete audit trail maintained

## Risk Mitigation

### Data Loss
- User explicitly stated existing prompt data can be deleted
- No migration complexity
- Fresh start reduces bugs

### Feature Isolation
- ONLY touching Prompter tables
- ALS and other features completely isolated
- Clear table boundaries

### Rollback Plan
- Database backup before changes
- Can restore old tables if needed
- Feature flag for gradual rollout

## Timeline
**Total: ~11.5 hours**
- Phase 1: 2 hours
- Phase 2: 3 hours  
- Phase 3: 4 hours
- Phase 4: 30 minutes
- Testing: 2 hours

## Post-Implementation
1. Monitor for any issues
2. Gather user feedback
3. Consider adding similarity search
4. Plan for prompt library features

## Notes
- This is a clean slate rebuild - no migration needed
- User confirmed existing prompt data can be deleted
- Focus on getting it right from the start
- Maintain soft-delete for future data only