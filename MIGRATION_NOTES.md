# Migration Notes - IMPORTANT

## ⚠️ PRE-UPGRADE CHECKPOINT - AUGUST 14, 2025

### System Status Before Prompter Upgrade
- **All features working**: ALS, Entity Strength, Brand Tracking
- **Committing stable system** before major changes
- **This is a safety checkpoint** in case rollback needed

## User Directive on Existing Data

**DATE**: August 14, 2025
**CRITICAL INSTRUCTION**: User has explicitly stated they DO NOT CARE about preserving existing prompts and results.

### Direct Quote
"I don't care about migration in terms of our existing saved prompts and results - if they all got deleted I would not care"

### Implications for Implementation

1. **NO MIGRATION NEEDED** for existing PROMPT data only
   - All 43 existing prompt templates can be deleted
   - All 200+ prompt results can be deleted  
   - No need for complex backfilling or version reconstruction
   - **CRITICAL: This ONLY applies to prompt_templates, prompt_runs, prompt_results tables**

2. **CLEAN SLATE FOR PROMPTER FEATURE ONLY**
   - Can rebuild ONLY the Prompter-related tables from scratch
   - **DO NOT TOUCH**: brands, entity_mentions, countries, or ANY ALS-related tables
   - **DO NOT TOUCH**: Any other feature tables (entity strength, brand analysis, etc.)
   - Only drop and recreate the specific prompt tracking tables

3. **SIMPLIFIED IMPLEMENTATION**
   - Remove Phase 4 (Migration & Cleanup) from implementation plan
   - No need for complex data transformation logic
   - No need to compute config_hash for legacy rows
   - No need to backfill prompt_versions from historical results

4. **GOING FORWARD ONLY**
   - Once new system is implemented, THEN enforce soft-delete only
   - But existing data prior to upgrade can be hard deleted
   - Future data (post-implementation) must be preserved with soft-delete

### What This Means for Development

✅ **DO**: 
- Feel free to drop existing tables and start fresh
- Implement the new schema without migration concerns
- Focus on getting the new system right

❌ **DON'T**:
- Waste time writing migration scripts for existing data
- Try to preserve historical prompt results
- Worry about data loss for pre-upgrade content

### Exception
While existing data can be deleted, once the new system is live:
- NEVER hard delete prompts or results
- Always use soft-delete with deleted_at timestamps
- Maintain full audit trail going forward

## Summary
This dramatically simplifies the implementation by removing all migration complexity. We can build the ideal system without being constrained by legacy data structure or preservation requirements.

## ⚠️ CRITICAL WARNINGS

### DO NOT MODIFY THESE FEATURES
1. **ALS (Ambient Location Signals)** - Working perfectly, mission-critical
2. **Entity Strength Analysis** - Fully operational
3. **Brand Tracking** - Functional
4. **Countries Tab** - 100% success rate

### ONLY MODIFY THESE TABLES
- `prompt_templates`
- `prompt_runs`
- `prompt_results`
- (New) `prompt_versions`

### PRESERVE ALL OTHER TABLES
Including but not limited to:
- `brands`
- `entity_mentions`
- `countries`
- All ALS-related data
- All other feature tables

## Checkpoint Commit
This document is part of the August 14, 2025 checkpoint commit before Prompter upgrade.
If issues arise, this commit can be used as a rollback point.