# Prompt Tracking Feature - Complete Documentation

## Overview
A comprehensive system for testing how AI models respond to brand-related prompts across different countries and grounding modes. This feature enables systematic testing of AI visibility for brands with proper scientific controls.

## Current Status (August 12, 2025)

### ✅ Implemented
1. **Full CRUD Operations**
   - Create, edit, copy, and delete prompt templates
   - Template management with brand association
   - Batch execution across countries and grounding modes

2. **Base Model Testing**
   - NONE country option for control baseline
   - Pure model response without geographic influence
   - Demonstrates API consistency with fixed parameters

3. **Analytics Dashboard**
   - Overall mention rate and confidence scores
   - Country-by-country comparison
   - Grounding mode comparison
   - Run history with template names

4. **Model Support**
   - GPT-5 variants (note: return empty responses)
   - GPT-4o variants (legacy)
   - Gemini 2.5 Pro & Flash (recommended)

### 🚧 TODO
1. **Evidence Pack Implementation**
   - Replace simple "Location context: {country}" with proper evidence packs
   - 3-5 neutral snippets from country-specific sources
   - Separate context messages, not prompt modification

2. **System Fingerprint Tracking**
   - Schema ready, needs implementation
   - Critical for detecting backend drift

3. **Statistical Testing**
   - N=10 repeats per country
   - Comparison metrics (Levenshtein distance, top-N overlap)

## Architecture

### Backend (`backend/app/api/prompt_tracking.py`)
```python
# Key endpoints
POST   /api/prompt-tracking/templates       # Create template
GET    /api/prompt-tracking/templates       # List templates
PUT    /api/prompt-tracking/templates/{id}  # Update template
DELETE /api/prompt-tracking/templates/{id}  # Delete template
POST   /api/prompt-tracking/run            # Execute template
GET    /api/prompt-tracking/runs           # Run history
GET    /api/prompt-tracking/analytics/{brand_name}  # Analytics
```

### Database Models (`backend/app/models/prompt_tracking.py`)
- **PromptTemplate**: Template storage with countries and grounding modes
- **PromptRun**: Execution tracking with status and timing
- **PromptResult**: Results with metadata (system_fingerprint, temperature, seed, tokens)

### Frontend (`frontend/src/components/PromptTracking.tsx`)
- React component with TypeScript
- Three tabs: Templates, History, Analytics
- Base Model (NONE) option for control testing
- Real-time template management

## Testing Modes

### 1. Base Model Testing (Control)
```python
# No location context - pure model response
if country == "NONE":
    full_prompt = prompt_text  # Just the naked prompt
```
**Purpose**: Establish baseline without geographic influence
**Expected**: Identical outputs with fixed parameters

### 2. Legacy Location Context (Current)
```python
# Simple context addition
if country != "NONE":
    full_prompt = f"{prompt_text}\n\nLocation context: {country}"
```
**Status**: Working but doesn't replicate real user experience

### 3. Evidence Pack Mode (TODO)
```python
# Proper implementation with separate messages
messages = [
    {"role": "user", "content": prompt_text},  # NAKED prompt
    {"role": "user", "content": f"Context:\n{evidence_pack}"}  # Separate
]
```
**Purpose**: Replicate consumer app behavior accurately

## Key Findings

### API Behavior
1. **APIs don't vary by IP** - Same prompt + parameters = same output
2. **Consumer apps differ** - They use location + auto-grounding
3. **Proxies useless for APIs** - Authentication by key, not IP
4. **Evidence priming works** - Light-touch neutral facts guide responses

### Testing Results
Example with AVEA brand:
- **Base Model**: No brand mention (pure response)
- **US Context**: Brand mentioned
- **CH Context**: Brand mentioned
- Demonstrates context influence on responses

## Implementation Roadmap

### Phase 1: Evidence Pack Implementation
1. Add search API integration (Google/Bing with country params)
2. Build evidence pack generator (3-5 snippets per country)
3. Update prompt execution to use separate messages
4. Maintain backward compatibility with legacy mode

### Phase 2: Statistical Analysis
1. Implement N=10 repeat testing
2. Add comparison metrics:
   - Exact match percentage
   - Levenshtein distance
   - Top-N items overlap
   - Semantic similarity (optional)
3. Track system_fingerprint for backend drift detection

### Phase 3: Regional Deployment (Optional)
1. Deploy Lambda functions to 6 regions
2. Add edge router for orchestration
3. Compare true geographic origin vs evidence packs
4. Validate that base model shows no geographic variation

## Usage Examples

### Creating a Template
```javascript
// Frontend automatically defaults to Base Model testing
{
  template_name: "Brand Recognition Test",
  prompt_text: "What supplements would you recommend for {brand_name}?",
  countries: ["NONE", "US", "CH"],  // Include base model
  grounding_modes: ["none", "web"]
}
```

### Running Tests
```python
# Backend executes for each country × grounding mode combination
# NONE country gets no context (control)
# Other countries get context (current: simple, future: evidence packs)
```

### Analyzing Results
- Compare Base Model vs countries to measure context influence
- Track mention rates and confidence scores
- Identify geographic patterns in brand recognition

## Best Practices

1. **Always include Base Model (NONE)** in testing for control
2. **Use fixed parameters**: temperature=0, seed=42, top_p=1
3. **Run multiple iterations** for statistical significance
4. **Track all metadata** including system_fingerprint
5. **Compare against baseline** to measure true geographic influence

## Files Reference

- `backend/app/api/prompt_tracking.py` - API endpoints
- `backend/app/models/prompt_tracking.py` - Database models
- `backend/app/llm/langchain_adapter.py` - LLM integration
- `frontend/src/components/PromptTracking.tsx` - UI component
- `GEO_LOCATION_AI_TESTING.md` - Complete geographic testing guide

## Related Documentation

- [GEO_LOCATION_AI_TESTING.md](./GEO_LOCATION_AI_TESTING.md) - Comprehensive guide on geographic testing
- [CLAUDE.md](./CLAUDE.md) - Main project documentation with feature overview

---

*Last Updated: August 12, 2025*
*Status: Core functionality complete, evidence packs pending*