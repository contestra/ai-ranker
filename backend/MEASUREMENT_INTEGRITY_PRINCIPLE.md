# Measurement Integrity Principle

## Core Principle
**Never change experimental conditions mid-run.** The grounding measurement framework exists to observe and compare how different providers behave under identical conditions across three modes: UNGROUNDED, PREFERRED, and REQUIRED.

## The Problem We're Solving
GPT-5 reasoning models can experience token starvation when grounding is enabled - they consume all available tokens on reasoning before producing a message. This causes empty outputs that break the measurement.

## The Solution: Preemptive Allocation + Telemetry

### 1. Preemptive Token Allocation
- **Auto-raise `max_output_tokens` to 512** when:
  - Model is GPT-5 variant (gpt-5, gpt-5o, gpt-5-mini, etc.)
  - Tools are present (PREFERRED or REQUIRED mode)
  - No explicit override provided
- **Configurable via environment**: `OPENAI_GPT5_TOOLS_MAX_OUTPUT_TOKENS=768`
- **Applied BEFORE the run**, not as a retry

### 2. Comprehensive Usage Telemetry
Track token consumption patterns without changing the experiment:
```json
{
  "usage_input_tokens": 4526,
  "usage_output_tokens": 286,
  "usage_total_tokens": 4812,
  "usage_reasoning_tokens": 256,  // NEW: reasoning burn
  "budget_starved": false,         // NEW: starvation flag
  "effective_max_output_tokens": 512  // NEW: what was actually used
}
```

### 3. Budget Starvation Detection
- **`budget_starved: true`** when:
  - Reasoning items exist in output
  - But no message items produced
- **Allows post-hoc analysis** without contaminating results
- **Maintains mode integrity** - doesn't change REQUIRED to PREFERRED

## Why This Preserves Measurement Integrity

### What We DON'T Do:
- ❌ Retry with different mode (e.g., REQUIRED → PREFERRED)
- ❌ Change tool configuration mid-run
- ❌ Modify grounding requirements after seeing results
- ❌ Hide failures by automatic fallbacks

### What We DO:
- ✅ Set appropriate resources BEFORE the run starts
- ✅ Log detailed telemetry for analysis
- ✅ Flag problematic runs with `budget_starved`
- ✅ Maintain identical experimental conditions

## Benefits for A/B Testing

1. **Clean Comparisons**: UNGROUNDED vs PREFERRED vs REQUIRED remain distinct
2. **Failure Transparency**: Budget starvation is visible, not hidden
3. **Root Cause Analysis**: Reasoning token burn reveals why outputs fail
4. **Reproducibility**: Same conditions = same results

## Example Analysis Queries

### Find all budget-starved runs:
```sql
SELECT 
  model,
  requested_mode,
  COUNT(*) as starved_runs,
  AVG(usage_reasoning_tokens) as avg_reasoning_burn
FROM grounding_runs
WHERE budget_starved = TRUE
GROUP BY model, requested_mode
```

### Compare reasoning burn across modes:
```sql
SELECT 
  requested_mode,
  AVG(usage_reasoning_tokens) as avg_reasoning,
  AVG(usage_output_tokens - usage_reasoning_tokens) as avg_message_tokens,
  AVG(CASE WHEN budget_starved THEN 1 ELSE 0 END) as starvation_rate
FROM grounding_runs
WHERE model LIKE 'gpt-5%'
GROUP BY requested_mode
```

### Success rate by token allocation:
```sql
SELECT 
  effective_max_output_tokens,
  COUNT(*) as total_runs,
  SUM(CASE WHEN budget_starved THEN 1 ELSE 0 END) as starved_runs,
  AVG(tool_call_count) as avg_searches
FROM grounding_runs
WHERE model LIKE 'gpt-5%' AND requested_mode = 'PREFERRED'
GROUP BY effective_max_output_tokens
```

## Implementation Notes

1. **Default of 512 tokens** is based on empirical testing:
   - 96 tokens: Always starves
   - 256 tokens: Sometimes starves
   - 512 tokens: Rarely starves
   - 1024 tokens: Never starves (but slower)

2. **Reasoning effort "low"** reduces token consumption:
   - Applied only for GPT-5 + tools
   - Reduces reasoning burn by ~30-40%
   - Still maintains response quality

3. **No retry logic** by design:
   - Single attempt per run
   - Failures are real data points
   - Retries would create selection bias

## Summary

This approach solves the practical problem (empty outputs) while maintaining scientific rigor. By allocating resources preemptively and tracking detailed telemetry, we can:
- Prevent most failures
- Identify remaining failures
- Analyze root causes
- Compare providers fairly

The `budget_starved` flag is your key to understanding which runs hit limits without contaminating your A/B test results between grounding modes.