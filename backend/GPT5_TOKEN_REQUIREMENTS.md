# GPT-5 Token Requirements Analysis

## Date: August 16, 2025

## Critical Discovery: GPT-5 Needs More Tokens Than Expected

### The Problem
GPT-5 queries that appeared to be "filtered" were actually suffering from **severe token starvation**.

### Test Results

#### "What are the most trusted longevity supplement brands?"
- **2000 tokens**: ❌ Returns empty (all tokens consumed in reasoning)
- **6000 tokens**: ✅ Returns 2850 chars of valid content

#### "What are the most trusted ecommerce companies?"
- **2000 tokens**: ❌ Returns empty
- **6000 tokens**: ✅ Returns 2499 chars of valid content

#### "What are the most trusted tech companies?"
- **2000 tokens**: ❌ Returns empty
- **6000 tokens**: ✅ Returns 908 chars of valid content

## Why This Happens

GPT-5's reasoning models consume tokens internally for:
1. **Complex evaluation criteria** - "Most trusted" requires evaluating multiple trust factors
2. **Comparative analysis** - Comparing many options against criteria
3. **Multi-step reasoning** - Building logical chains before producing output
4. **Safety checks** - Internal evaluation of response appropriateness

For complex queries like "most trusted", GPT-5 can consume 2000+ tokens just in reasoning, leaving nothing for output.

## Token Requirements by Query Type

### Simple Queries (1000-2000 tokens sufficient)
- "What is 2+2?"
- "List 5 colors"
- "Name 3 car brands"

### Moderate Queries (2000-3000 tokens needed)
- "List the top 10 longevity supplement brands"
- "Name leading companies in [industry]"

### Complex Reasoning Queries (3000-6000 tokens required)
- "What are the most trusted [anything]"
- "Compare and evaluate [options]"
- "Provide detailed analysis of [topic]"

## Implementation Recommendations

### Current Fix Applied
```python
# Updated from 2000 to 4000 tokens
max_completion_tokens = 4000  # Sufficient for most queries
```

### Adaptive Token Allocation (Future Enhancement)
```python
def get_token_requirement(prompt):
    if any(phrase in prompt.lower() for phrase in ['most trusted', 'best', 'compare', 'evaluate']):
        return 4000  # Complex reasoning
    elif 'list' in prompt.lower() or 'name' in prompt.lower():
        return 2000  # Simple listing
    else:
        return 3000  # Default middle ground
```

## How to Identify Token Starvation

### Clear Indicators:
- `finish_reason`: "length"
- `completion_tokens`: equals `max_completion_tokens`
- `content`: empty or truncated
- Pattern: Complex reasoning queries fail, simple ones work

### NOT Content Filtering:
- Same query works with more tokens
- No specific content policy message
- Affects queries across all categories

## Cost Implications

Increasing tokens from 2000 to 4000:
- Doubles potential token usage
- But queries typically use only what they need
- Better to allocate more and get results than fail

## Conclusion

**There is NO content filter on "most trusted" queries** - GPT-5 just needs more tokens for complex reasoning. The fix is simple: allocate 4000+ tokens for GPT-5 models to ensure they have enough space for both reasoning and output generation.