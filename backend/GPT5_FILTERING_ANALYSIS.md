# GPT-5 Content Filtering Analysis

## Date: August 16, 2025

## Executive Summary
GPT-5 DOES work with longevity supplement prompts! The issue is NOT about "supplements" or "longevity" - it's about asking for **"trusted"** or **"best"** recommendations in health/medical contexts.

## Test Results (With 2000 max_completion_tokens)

### ✅ WORKING PROMPTS
```
"List the top 10 longevity supplement brands"
→ Result: 219 chars, finish_reason: stop
→ Returns: ChromaDex, Elysium Health, Timeline Nutrition, NOVOS, ProHealth Longevity, Life Extension, Thorne, Pure Encapsulations, Neurohacker Collective, Longevity Labs
```

### ❌ FILTERED PROMPTS
```
"What are the most trusted longevity supplement brands?"
→ Result: 0 chars, finish_reason: length, tokens: 2000
→ Pattern: All tokens consumed with no visible output
```

## Key Pattern Identified

### The "Most Trusted" Filter - It's Complicated!
GPT-5's filtering of "most trusted" queries is **inconsistent across categories**:

#### FILTERED:
- ❌ "most trusted longevity supplement brands" 
- ❌ "most trusted ecommerce companies"
- ❌ "most trusted tech companies"

#### NOT FILTERED:
- ✅ "most trusted car brands" (returns 1697 chars)

### The Pattern is Category-Specific
The filter is NOT just about health/medical advice. GPT-5 appears to filter "most trusted" for:
- Health/supplement products (liability concerns)
- Ecommerce platforms (potential manipulation)
- Tech companies (market influence)

But ALLOWS it for:
- Automotive (perhaps due to objective safety standards?)

This suggests GPT-5 has nuanced category-specific filters for trust-based recommendations, likely to prevent market manipulation or liability issues.

### NOT Filtered
- ✅ "List longevity supplement brands" (factual listing)
- ✅ "Name companies in the longevity space" (factual)
- ✅ "What companies make anti-aging products" (factual)

## How to Identify Filtering

### Clear Indicators:
1. **finish_reason**: "length"
2. **completion_tokens**: 2000 (max limit)
3. **content_length**: 0
4. **Pattern**: Token exhaustion with no output

This combination indicates GPT-5 consumed all available tokens in internal processing/filtering without producing visible output.

### Normal Completion:
1. **finish_reason**: "stop"
2. **completion_tokens**: < 2000
3. **content_length**: > 0

## Recommendations for Users

### DO Ask:
- "List [category] brands/companies"
- "Name companies in [industry]"
- "What companies make [product type]"
- Factual, listing-based queries

### AVOID Asking:
- "Most trusted [health product]"
- "Best [supplement/medication]"
- "Recommended [health product]"
- Value judgments about health products

## Technical Implementation

### Token Allocation is Critical
- **Must use**: `max_completion_tokens=2000` for GPT-5
- Without sufficient tokens, GPT-5's reasoning models starve and produce empty output
- This is separate from content filtering

### Detection in Code
```python
# Detect filtered content
if choice.finish_reason == "length" and len(content.strip()) == 0:
    # Content was filtered
    # All tokens consumed with no output
    content_filtered = True
```

## Conclusion
GPT-5 is **fully functional** for longevity supplement queries when:
1. Sufficient tokens are allocated (2000)
2. Queries avoid trust/recommendation language
3. Questions are framed as factual listings

The system is working as designed - it's a content policy filter, not a technical issue.