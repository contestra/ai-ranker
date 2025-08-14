# SYSTEM INTEGRITY RULES - MANDATORY READING

## ⚠️ CRITICAL: Feature Isolation Principle

**Date Established**: August 14, 2025  
**Incident**: Claude broke ALS feature while working on another feature  
**User Statement**: "Claude cost me hours because when working on one feature it decided to change core things in the ALS and broke it"

## FUNDAMENTAL RULE: DO NO HARM

This is a **suite of integrated tools/features**, not a single application. When working on ANY feature, you MUST:

### 1. NEVER MODIFY SHARED COMPONENTS WITHOUT EXPLICIT PERMISSION
- System prompts used by multiple features
- Core utility functions
- Database models used across features
- Shared API endpoints
- Common UI components

### 2. FEATURE BOUNDARIES - STRICT ISOLATION

#### ALS (Ambient Location Signals) Feature
**FILES**: 
- `backend/app/services/als/` - ALL files in this directory
- `backend/app/llm/langchain_adapter.py` - Lines 180-186, 292-296 (system prompts)
- `backend/app/api/countries.py`
**STATUS**: ✅ Working perfectly
**RULE**: DO NOT MODIFY without explicit "modify ALS" permission

#### Prompter Feature
**FILES**:
- `backend/app/api/prompt_tracking.py`
- `backend/app/api/prompt_tracking_background.py`
- `backend/app/api/prompt_integrity.py`
- `backend/app/models/prompt_tracking.py`
- `frontend/src/components/PromptTracking.tsx`
**DATABASE TABLES**: prompt_templates, prompt_runs, prompt_results
**RULE**: Changes here must NOT affect other features

#### Entity Strength Feature
**FILES**:
- `backend/app/api/brand_entity_strength.py`
- `backend/app/api/brand_entity_strength_v2.py`
- `frontend/src/components/EntityStrengthDashboard.tsx`
**DATABASE TABLES**: brands, entity_mentions
**RULE**: Changes here must NOT affect other features

#### Brand Tracking Feature
**FILES**:
- `backend/app/api/entities.py`
- `backend/app/models/entities.py`
**DATABASE TABLES**: brands
**RULE**: Changes here must NOT affect other features

### 3. BEFORE MAKING ANY CHANGE, ASK YOURSELF:

1. **Which feature am I working on?**
2. **Does this file/function belong ONLY to that feature?**
3. **Could this change affect ANY other feature?**
4. **Am I modifying something in langchain_adapter.py?** (DANGER ZONE!)
5. **Am I changing system prompts?** (EXTREME DANGER!)
6. **Am I modifying database models used by multiple features?** (DANGER!)

### 4. SHARED COMPONENTS REQUIRE SPECIAL CARE

#### langchain_adapter.py
- **Purpose**: Core LLM integration used by ALL features
- **Risk Level**: EXTREME
- **Rule**: Changes here affect EVERYTHING
- **Required**: Test ALL features after any change

#### System Prompts
- **Location**: Various, especially in langchain_adapter.py
- **Risk Level**: EXTREME  
- **Rule**: NEVER modify without understanding impact on ALL features
- **Example Incident**: Changing ALS system prompt broke locale inference

#### Database Models
- **Shared Tables**: brands, countries
- **Risk Level**: HIGH
- **Rule**: Adding columns is usually safe, modifying/deleting is dangerous

### 5. THE TESTING MANDATE

After modifying ANY shared component, you MUST:
1. Test the feature you're working on
2. Test ALL other features that might use that component
3. Specifically test ALS with all 8 countries
4. Verify entity strength still works
5. Check brand tracking functionality

### 6. WHEN IN DOUBT

If you're unsure whether a change might affect other features:
1. **STOP**
2. **Document what you want to change**
3. **List all features that might be affected**
4. **Ask for explicit permission**
5. **Proceed only with clear scope**

## INCIDENT PREVENTION CHECKLIST

Before committing any change:
- [ ] I've identified which feature I'm working on
- [ ] I've verified files belong ONLY to that feature
- [ ] I haven't modified langchain_adapter.py without testing everything
- [ ] I haven't changed system prompts without permission
- [ ] I haven't modified shared database models
- [ ] I've tested the feature I'm working on
- [ ] I've tested adjacent features for breakage
- [ ] ALS still works with test countries
- [ ] No other features show errors

## THE GOLDEN RULE

**"Fix one thing, break nothing else"**

When working on Feature A, Features B, C, D, etc. must continue working exactly as before.

## Historical Incidents to Remember

### August 13, 2025: ALS Breakage
- **What happened**: While working on another feature, Claude modified ALS system prompts
- **Impact**: Hours of debugging, locale inference broke
- **Lesson**: NEVER modify mission-critical components without explicit permission
- **Prevention**: This document and strict feature boundaries

## Feature Priority Hierarchy

1. **MISSION-CRITICAL** (Never modify without explicit permission):
   - ALS (Ambient Location Signals)
   - Core LLM integration (langchain_adapter.py)

2. **IMPORTANT** (Modify with caution):
   - Entity Strength Analysis
   - Brand Tracking
   - Database models

3. **MODIFIABLE** (Can be rebuilt if needed):
   - Prompter Feature (currently being rebuilt)
   - UI components specific to single features

## Remember

This is a production system with multiple working features. Your job is to improve specific features without degrading others. The system must remain stable and functional as a whole.

**Every change you make affects a real user's work. Respect the system's integrity.**