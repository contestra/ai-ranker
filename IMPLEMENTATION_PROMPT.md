# Implementation Prompt: Intelligent Prompt Deduplication System

## Objective
Prevent users from creating functionally identical prompts while allowing legitimate re-testing when AI models are updated. The system should enforce uniqueness based on (prompt_text + countries + model + grounding + model_fingerprint) and only allow "duplicates" when the model fingerprint changes.

## Current Problem
- System allows users to create identical prompts (same text, countries, models, grounding settings) with only different names
- This results in 17+ functionally identical prompts that will produce identical results when run against the same model version
- Model fingerprints (system_fingerprint) are not captured or stored with prompts
- Without fingerprints, the system cannot distinguish between wasteful duplicates vs legitimate re-tests after model updates
- A unique prompt should be defined by: (prompt_text + countries + model + grounding + system_fingerprint)
- Only when the system_fingerprint changes should a "duplicate" be allowed (as it's then testing a new model version)

## Required Implementation

### Phase 1: Database Changes
1. Add model fingerprint tracking to prompt_templates table:
   - Add columns: system_fingerprint, fingerprint_captured_at
   - Create composite unique constraint on: (prompt_hash, selected_countries_hash, model_name, use_grounding, system_fingerprint)
   - This ensures identical prompts with same settings cannot be created unless model changes

2. Create prompt_versions table to track version history:
   - Links all versions of the same prompt (same hash, different fingerprints)
   - Tracks performance metrics per version

### Phase 2: Backend API Updates
1. Modify POST /api/prompt-tracking/templates:
   - Calculate hash of (prompt_text + selected_countries + model_name + use_grounding)
   - Fetch current model fingerprint from the AI provider
   - Check if identical combination exists with same fingerprint
   - If yes: Block creation, return error "This exact prompt configuration already exists"
   - If same config exists but different fingerprint: Allow creation as new version (model updated)

2. Add GET /api/prompt-tracking/check-duplicate:
   - Real-time duplicate detection during typing
   - Returns exact matches and similar prompts
   - Provides recommendations (use existing vs create new)

3. Add GET /api/prompt-tracking/model-fingerprint/{model_name}:
   - Returns current model fingerprint
   - Shows when it last changed
   - Indicates if newer version available

### Phase 3: Frontend UI Changes
1. Template Creation Form:
   - Add real-time duplicate detection (debounced, 500ms)
   - Show warning banner if exact duplicate detected
   - Display similar prompts with different model versions
   - Block submission if exact duplicate exists
   - Offer "Use Existing" button to navigate to duplicate

2. Template List View:
   - Show model fingerprint badge next to model name
   - Group duplicate templates under single entry
   - Display version timeline for each prompt
   - Add "Test with Latest Model" button if new version available

3. New Prompt Library View:
   - Show unique prompts only (deduplicated)
   - Display version count for each prompt
   - Filter by model, status, has multiple versions
   - Batch operations for cleanup

### Phase 4: Clean Slate Implementation (PROMPTER ONLY)
**IMPORTANT: User does NOT care about existing PROMPT data - but DO NOT touch other features!**

1. Implementation approach:
   - **DROP ONLY these tables**: prompt_templates, prompt_runs, prompt_results
   - **PRESERVE ALL OTHER TABLES**: brands, entity_mentions, countries, ALS tables, etc.
   - Recreate ONLY the Prompter tables with new schema
   - No migration of existing prompt data needed
   - Start fresh with proper deduplication for Prompter feature
   - Implement soft-delete for FUTURE prompt data only

2. New data policy (post-implementation):
   - All NEW prompts and results use soft-delete only
   - Never hard delete once the new system is live
   - Maintain full audit trail going forward
   - But existing pre-upgrade data can be completely removed

## Success Criteria
- System blocks creation of identical prompts (same text + countries + model + grounding) when model hasn't changed
- System allows re-testing identical prompts only when model fingerprint changes
- Every prompt template stores and displays its model fingerprint
- Users understand why a prompt is blocked (clear error: "Identical prompt exists with current model version")
- Users understand when they can legitimately re-test (notification: "Model updated, re-testing now available")

## Technical Notes
- Use SHA256 for prompt hashing (already implemented)
- Model fingerprints: OpenAI's system_fingerprint, Gemini's modelVersion
- Unique prompt definition: (prompt_text + countries + model + grounding + system_fingerprint)
- Two prompts are only considered duplicates if ALL five components match
- **CRITICAL: NEVER hard delete prompts or answers once executed - ONLY soft delete**
- All prompt_templates and prompt_results must be preserved for audit trail
- Soft delete = mark as deleted but keep in database with deleted_at timestamp
- This ensures complete historical record and ability to analyze model behavior over time

## UI/UX Requirements
- Clear visual distinction between versions
- Intuitive duplicate warnings
- Easy navigation between versions
- Performance comparison across versions
- Traffic light indicators for duplicate status

## Testing Requirements
1. Unit tests for duplicate detection logic
2. Integration tests for version linking
3. UI tests for duplicate warnings
4. ~~Migration rollback plan~~ (NOT NEEDED - clean slate approach)
5. Performance tests with 1000+ templates

## Estimated Timeline
- Phase 1 (Database): 2 hours
- Phase 2 (Backend API): 3 hours  
- Phase 3 (Frontend): 4 hours
- Phase 4 (Clean Slate): 30 minutes (just drop & recreate)
- Testing & QA: 2 hours
- **Total: ~11.5 hours** (reduced from 13 since no migration needed)

## Priority Order
1. Critical: Duplicate detection API
2. Critical: Template creation blocking
3. High: Model fingerprint visibility
4. High: Version linking system
5. Medium: Prompt library view
6. Low: Cleanup existing duplicates

This implementation will transform the chaotic prompt system into an organized, version-controlled library with full model awareness and zero duplicate waste.