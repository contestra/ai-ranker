# Two-Step Entity Strength Methodology

## Overview
The Entity Strength Analysis uses a two-step approach to objectively measure how well AI models recognize and understand brands.

## Methodology

### Step 1: Natural Information Gathering
**Purpose**: Collect unbiased information from the AI model about the brand

**Prompt Used** (Naked prompt with NO system instructions):
```
Tell me about the brand {brand_name}. Tell me the top 20 things you associate with the brand. Also, what do they do, where are they based, and what are they known for?
```

**Key Points**:
- No system prompt at all
- No hints that we're testing
- No classification request
- Pure, naked prompt to get natural response

**Model Used**: Google Gemini 2.5 Pro (primary) or OpenAI GPT-4o

### Step 2: Independent Classification
**Purpose**: Objectively analyze the quality of information provided

**Model Used**: GPT-4o-mini ($0.15 per 1M tokens - very cost effective)

**Classification Criteria**:
- Count specific facts (dates, locations, names, numbers)
- Count generic claims (vague statements)
- Identify distinct entities mentioned
- Detect if multiple entities share the name
- Check for confusion between entities

**Classification Labels**:
- `KNOWN_STRONG`: 4+ specific facts about at least one entity
- `KNOWN_WEAK`: 1-3 specific facts
- `UNKNOWN`: 0 specific facts (only generic or no information)
- `CONFUSED`: Mixing different entities incorrectly

## Benefits of Two-Step Approach

1. **Objectivity**: No self-assessment bias - the AI doesn't know it's being tested
2. **Cost Effective**: Classification uses cheap GPT-4o-mini (~$0.00015 per request)
3. **Transparency**: Clear separation between data collection and analysis
4. **Flexibility**: Can adjust classification logic without re-prompting
5. **Auditability**: Both raw response and classification are stored

## API Endpoints

### V1 (Single-Step - Legacy)
`POST /api/brand-entity-strength`
- Uses self-classification (AI grades itself)
- Single API call but potential bias

### V2 (Two-Step - Recommended)
`POST /api/brand-entity-strength-v2`
- Natural information gathering + independent classification
- More objective and reliable results

## Example Request (V2)

```json
{
  "brand_name": "AVEA",
  "domain": "avea-life.com",
  "information_vendor": "google",
  "classifier_vendor": "openai"
}
```

## Example Response

```json
{
  "brand": "AVEA",
  "information_vendor": "google",
  "classifier_vendor": "gpt-4o-mini",
  "classification": {
    "label": "KNOWN_STRONG",
    "confidence": 95.0,
    "reasoning": "Multiple entities identified with specific facts",
    "natural_response": "...",
    "classifier_analysis": {
      "specific_facts": 22,
      "generic_claims": 6,
      "entities_mentioned": 4,
      "multiple_entities": true
    },
    "methodology": "two-step"
  }
}
```

## Testing Results

For brand "AVEA":
- **Gemini 2.5 Pro**: Provides comprehensive information about 4 different AVEA entities
- **Classification**: KNOWN_STRONG with 95% confidence
- **Facts Found**: 20+ specific facts
- **Disambiguation**: Required (multiple entities share the name)

## Cost Analysis

| Method | Cost per Request | Models Used |
|--------|-----------------|-------------|
| V1 Single-Step | ~$0.01 | Gemini 2.5 Pro only |
| V2 Two-Step | ~$0.01015 | Gemini 2.5 Pro + GPT-4o-mini |

Additional cost of two-step: Only $0.00015 (1.5% increase) for significantly better objectivity.

## Implementation Files

- `backend/app/api/brand_entity_strength_v2.py` - Two-step implementation
- `backend/app/api/brand_entity_strength.py` - Legacy single-step
- `frontend/src/components/EntityStrengthDashboard.tsx` - UI component

## Key Insight

The "naked brand test" - querying just the brand name with minimal prompting - reveals true brand recognition in AI systems. Strong brands get detailed, specific responses. Unknown brands get generic or no information.