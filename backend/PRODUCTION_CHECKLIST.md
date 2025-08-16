# Production Deployment Checklist

## 🚨 Ship-Blockers (Must Fix Before Deploy)

### 1. Persistence Invariants ✅
```python
# Database write path - NEVER allow REQUIRED with 0 searches to be "ok"
if requested_mode == "REQUIRED" and tool_call_count == 0:
    status = "failed"  # IMMUTABLE
    enforcement_passed = False  # IMMUTABLE
    # No downstream transform should ever flip these
```

### 2. Metadata Capture 🔧
**OpenAI**: Capture for reproducibility
- `system_fingerprint`: Model version identifier
- `model`: Exact model used
- `created_at`: Timestamp

**Gemini**: Capture for auditability
- `modelVersion`: Version string
- `responseId`: Unique response identifier  
- `groundingMetadata`: Search sources used

```python
# Add to response capture
metadata = {
    "openai": {
        "system_fingerprint": response.get("system_fingerprint"),
        "model": response.get("model"),
        "created": response.get("created")
    },
    "gemini": {
        "model_version": response.get("modelVersion"),
        "response_id": response.get("responseId"),
        "grounding_metadata": response.get("groundingMetadata")
    }
}
```

### 3. Capability Cache 🔧
```python
# Redis/Upstash capability cache
import redis
import json
from datetime import timedelta

redis_client = redis.from_url(os.environ["REDIS_URL"])

def get_capability(model: str, capability: str) -> Optional[bool]:
    key = f"cap:openai:{model}:{capability}"
    val = redis_client.get(key)
    if val:
        return json.loads(val)
    return None

def set_capability(model: str, capability: str, supported: bool):
    key = f"cap:openai:{model}:{capability}"
    redis_client.setex(
        key, 
        timedelta(hours=24),  # TTL 24 hours
        json.dumps(supported)
    )
    
    # Alert on capability changes
    if supported != get_capability(model, capability):
        logger.warning(f"CAPABILITY CHANGE: {model} {capability}={supported}")
```

### 4. Retry Policy 🔧
```python
# Celery retry configuration
from celery import Celery
from celery.exceptions import Retry

app = Celery('grounding')

@app.task(
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_jitter=True
)
def run_grounding_task(self, run_id: str, config: dict):
    idempotency_key = f"run:{run_id}"
    
    # Check idempotency
    if redis_client.exists(idempotency_key):
        return {"status": "duplicate", "run_id": run_id}
    
    try:
        result = run_openai_with_grounding(**config)
        
        # DO NOT retry enforcement failures
        if result.get("error_code") in [
            "no_tool_call_in_required",
            "no_tool_call_in_soft_required"
        ]:
            return result  # Accept as final
            
    except RateLimitError as exc:
        # Retry with exponential backoff + jitter
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    except ServerError as exc:
        # Retry 5xx errors
        raise self.retry(exc=exc)
    
    # Set idempotency marker
    redis_client.setex(idempotency_key, timedelta(hours=1), "1")
    return result
```

### 5. BigQuery Hygiene 🔧
```sql
-- Partitioned and clustered table
CREATE OR REPLACE TABLE `contestra.raw.runs`
PARTITION BY DATE(created_at)
CLUSTER BY provider, model_alias, requested_mode
AS SELECT * FROM existing_runs;

-- TTL for raw response blobs (90 days)
ALTER TABLE `contestra.raw.runs`
SET OPTIONS (
  partition_expiration_days=90
);

-- Move large blobs to GCS
CREATE OR REPLACE TABLE `contestra.raw.runs_optimized` AS
SELECT 
  * EXCEPT(raw_response),
  CASE 
    WHEN BYTE_LENGTH(TO_JSON_STRING(raw_response)) > 10000
    THEN CONCAT('gs://contestra-responses/', run_id, '.json')
    ELSE TO_JSON_STRING(raw_response)
  END as response_ref
FROM `contestra.raw.runs`;
```

## 📊 Analytics Polish

### New Measures to Add
```sql
-- Add to BigQuery view
SELECT
  -- Existing fields...
  enforcement_passed,  -- Already added ✅
  
  -- NEW: Citation counting
  ARRAY_LENGTH(
    REGEXP_EXTRACT_ALL(answer_text, r'https?://[^\s]+')
  ) as citations_count,
  
  -- NEW: Search quality metrics
  CASE 
    WHEN tool_call_count > 0 
    THEN JSON_EXTRACT_SCALAR(grounding_metadata, '$.confidence')
    ELSE NULL
  END as search_confidence
```

### Dashboard Additions
```lkml
# Add to Looker dashboard
element: line_soft_required_fail_trend {
  title: "Soft-Required Fail Rate (7-day MA)"
  type: looker_line
  explore: runs_metrics_v1
  dimensions: [runs_metrics_v1.created_date]
  measures: [runs_metrics_v1.soft_required_fail_rate]
  filters:
    runs_metrics_v1.is_gpt5: "Yes"
    runs_metrics_v1.requested_mode: "REQUIRED"
  query_timezone: "America/Los_Angeles"
  # 7-day moving average
  dynamic_fields: [{
    table_calculation: ma7_fail_rate,
    expression: "mean(offset_list(${runs_metrics_v1.soft_required_fail_rate},-3,7))",
    value_format_name: percent_1
  }]
}
```

## 🎨 Frontend UX Updates

### Run Detail Copy Variants
```tsx
// components/runs/RunDetailCard.tsx
const getFailureMessage = (run: Run) => {
  if (run.requested_mode !== "REQUIRED" || run.enforcement_passed) {
    return null;
  }
  
  const isGPT5 = /^gpt-5/i.test(run.model_alias);
  
  if (isGPT5 && run.enforcement_mode === "soft") {
    return {
      title: "Soft Enforcement Failed",
      message: "GPT-5 doesn't support tool_choice:'required'. The model declined to search despite the search-first directive.",
      detail: `0 searches performed. Error: ${run.error_code}`
    };
  } else {
    return {
      title: "Hard Enforcement Failed", 
      message: "No tool call occurred in REQUIRED mode.",
      detail: `Enforcement mode: ${run.enforcement_mode}. Error: ${run.error_code}`
    };
  }
};

// Retry button logic
const showRetry = run.budget_starved && !run.enforcement_passed;
const retryDisabled = !run.budget_starved && !run.enforcement_passed;
// If not starved but failed, it's a provider choice - don't retry
```

## 🧪 Test Coverage Additions

### Test: Tool Errors Don't Count
```python
def test_tool_error_not_counted_as_grounded():
    """Web search errors shouldn't count as grounding"""
    
    class _FakeClientWithError:
        class responses:
            @staticmethod
            def create(**kwargs):
                return {"output": [
                    {"type": "web_search_call", "status": "error"},  # ERROR status
                    {"type": "message", "content": [{"type": "output_text", "text": "answer"}]}
                ]}
    
    res = run_openai_with_grounding(
        client=_FakeClientWithError(),
        model="gpt-5",
        mode="REQUIRED",
        prompt="Test",
        strict_fail=True
    )
    
    assert res["tool_call_count"] == 0  # Error doesn't count
    assert res["grounded_effective"] is False
    assert res["status"] == "failed"
    assert res["enforcement_passed"] is False
```

### Test: Ungrounded Guard
```python
def test_ungrounded_fails_with_any_search():
    """UNGROUNDED must fail if ANY search occurs"""
    
    class _FakeClientWithSearch:
        class responses:
            @staticmethod
            def create(**kwargs):
                return {"output": [
                    {"type": "web_search_call", "status": "ok"},
                    {"type": "message", "content": [{"type": "output_text", "text": "answer"}]}
                ]}
    
    res = run_openai_with_grounding(
        client=_FakeClientWithSearch(),
        model="gpt-5",
        mode="UNGROUNDED",
        prompt="Test"
    )
    
    assert res["status"] == "failed"
    assert res["error_code"] == "tool_used_in_ungrounded"
    assert res["enforcement_passed"] is False
```

### Test: Capability Cache
```python
def test_capability_probe_caching(mocker):
    """First call probes, subsequent calls use cache"""
    
    mock_redis = mocker.patch('redis.Redis')
    mock_redis.get.side_effect = [None, '{"supported": false}']
    
    # First call - cache miss, probes
    adapter = OpenAIAdapter()
    result1 = adapter._get_capability("gpt-5", "force-tools")
    assert mock_redis.get.called
    assert mock_redis.setex.called
    
    # Second call - cache hit
    result2 = adapter._get_capability("gpt-5", "force-tools")
    assert result2 == {"supported": False}
    assert mock_redis.get.call_count == 2
```

## 📈 Ops & SRE

### Structured Logging
```python
# Structured log per run
import structlog

logger = structlog.get_logger()

def log_run(result: dict):
    logger.info(
        "grounding_run",
        run_id=result.get("run_id"),
        requested_mode=result.get("requested_mode"),
        enforcement_mode=result.get("enforcement_mode"),
        enforcement_passed=result.get("enforcement_passed"),
        tool_call_count=result.get("tool_call_count"),
        usage_reasoning_tokens=result.get("usage_reasoning_tokens"),
        budget_starved=result.get("budget_starved"),
        latency_ms=result.get("latency_ms"),
        error_code=result.get("error_code"),
        provider=result.get("provider"),
        model=result.get("model")
    )
```

### Alerts Configuration
```yaml
# prometheus alerts
groups:
  - name: grounding
    rules:
      - alert: HighSoftRequiredFailRate
        expr: |
          rate(grounding_runs_total{mode="REQUIRED",enforcement="soft",status="failed"}[5m]) 
          / rate(grounding_runs_total{mode="REQUIRED",enforcement="soft"}[5m]) > 0.3
        for: 10m
        annotations:
          summary: "Soft-required fail rate > 30%"
          
      - alert: ReasoningTokenSpike
        expr: |
          histogram_quantile(0.95, 
            rate(reasoning_tokens_bucket[5m])
          ) > 1000
        for: 5m
        annotations:
          summary: "P95 reasoning tokens > 1000"
          
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            rate(grounding_latency_seconds_bucket[5m])
          ) > 30
        for: 5m
        annotations:
          summary: "P95 latency > 30s"
```

### Rate Limiting
```python
# Centralized rate limiter
from ratelimit import limits, sleep_and_retry
import os

CALLS_PER_MINUTE = int(os.environ.get("OPENAI_RPM", 60))

@sleep_and_retry
@limits(calls=CALLS_PER_MINUTE, period=60)
def call_openai_api(client, **kwargs):
    return client.responses.create(**kwargs)

# Queue depth monitoring
def get_queue_depth():
    pending = redis_client.llen("grounding:queue")
    if pending > 100:
        logger.warning(f"Queue depth high: {pending}")
    return pending
```

## 🚀 Product/Science Next Steps

### 1. Directive A/B Testing
```python
DIRECTIVES = {
    "A": "Call web_search first for facts. Answer briefly.",  # Shorter
    "B": "Search before answering stable facts. Keep reasoning minimal.",  # Current
    "C": "web_search required for: VAT, plug, emergency. Then answer."  # Explicit
}

def run_directive_experiment(prompt: str, variant: str = "B"):
    directive = DIRECTIVES.get(variant, DIRECTIVES["B"])
    # Track: tool_call_count, usage_reasoning_tokens, latency_ms by variant
```

### 2. Expanded Probe Set
```python
PROBE_QUESTIONS = {
    "vat": "What is the federal VAT rate?",
    "emergency": "What is the emergency phone number?",
    "plug": "What type of electrical plug is used?",
    "voltage": "What is the mains voltage?",
    "currency": "What is the official currency code?",
    "language": "What is the official language?",
    "driving": "Which side of the road for driving?",
    "timezone": "What is the primary timezone?"
}
```

### 3. Locale Matrix Testing
```python
LOCALE_MATRIX = [
    ("CH", "de-CH"),  # Switzerland German
    ("CH", "fr-CH"),  # Switzerland French  
    ("AE", "ar-AE"),  # UAE Arabic
    ("AE", "en-AE"),  # UAE English
    ("SG", "en-SG"),  # Singapore
    ("US", "en-US"),  # United States
]

async def run_locale_matrix():
    results = []
    for country, locale in LOCALE_MATRIX:
        for mode in ["UNGROUNDED", "PREFERRED", "REQUIRED"]:
            result = await test_locale(country, locale, mode)
            results.append(result)
    
    # Chart: grounded_rate by locale × mode × provider
    return results
```

## 🔄 Continuous Monitoring

### Nightly Smoke Test
```python
# smoke_test.py - Run via cron/scheduler
import asyncio
from datetime import datetime

SMOKE_TESTS = [
    ("UNGROUNDED", "US", "What is the VAT rate?"),
    ("PREFERRED", "US", "What is the VAT rate?"),
    ("REQUIRED", "US", "What is the VAT rate?"),
    ("UNGROUNDED", "CH", "Was ist der MwSt-Satz?"),
    ("PREFERRED", "CH", "Was ist der MwSt-Satz?"),
    ("REQUIRED", "CH", "Was ist der MwSt-Satz?"),
]

async def run_smoke_tests():
    results = []
    for mode, country, prompt in SMOKE_TESTS:
        try:
            result = await test_grounding(mode, country, prompt)
            results.append({
                "test": f"{mode}_{country}",
                "passed": result["enforcement_passed"] if mode == "REQUIRED" else True,
                "tool_calls": result["tool_call_count"],
                "latency": result["latency_ms"]
            })
        except Exception as e:
            results.append({
                "test": f"{mode}_{country}",
                "passed": False,
                "error": str(e)
            })
    
    # Post to Slack
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "avg_latency": sum(r.get("latency", 0) for r in results) / len(results)
    }
    
    post_to_slack(summary)
    return results
```

### Slack Integration
```python
import requests

def post_to_slack(summary: dict):
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🔍 Grounding Smoke Test"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Total Tests:* {summary['total']}"},
                {"type": "mrkdwn", "text": f"*Passed:* {summary['passed']}"},
                {"type": "mrkdwn", "text": f"*Avg Latency:* {summary['avg_latency']:.0f}ms"},
                {"type": "mrkdwn", "text": f"*Time:* {summary['timestamp']}"}
            ]
        }
    ]
    
    if summary['passed'] < summary['total']:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "⚠️ Some tests failed. Check logs."}
        })
    
    requests.post(webhook_url, json={"blocks": blocks})
```

## Database Migration

### Alembic Migration for Missing Fields
```python
"""Add enforcement and telemetry fields

Revision ID: 20250816_001
Create Date: 2025-08-16
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add enforcement_passed
    op.add_column('runs', 
        sa.Column('enforcement_passed', sa.Boolean(), nullable=True)
    )
    
    # Add citations_count
    op.add_column('runs',
        sa.Column('citations_count', sa.Integer(), nullable=True)
    )
    
    # Add search_confidence
    op.add_column('runs',
        sa.Column('search_confidence', sa.Float(), nullable=True)
    )
    
    # Backfill enforcement_passed
    op.execute("""
        UPDATE runs 
        SET enforcement_passed = CASE
            WHEN requested_mode = 'REQUIRED' AND tool_call_count > 0 THEN TRUE
            WHEN requested_mode = 'REQUIRED' AND tool_call_count = 0 THEN FALSE
            WHEN requested_mode = 'UNGROUNDED' AND tool_call_count = 0 THEN TRUE
            WHEN requested_mode = 'UNGROUNDED' AND tool_call_count > 0 THEN FALSE
            ELSE TRUE
        END
    """)
    
    # Make non-nullable after backfill
    op.alter_column('runs', 'enforcement_passed', nullable=False)

def downgrade():
    op.drop_column('runs', 'enforcement_passed')
    op.drop_column('runs', 'citations_count')
    op.drop_column('runs', 'search_confidence')
```

## Implementation Priority

### P0 - Ship Blockers (Do Now)
1. ✅ Persistence invariants (already done)
2. 🔧 Add metadata capture
3. 🔧 Implement capability cache
4. 🔧 Configure retry policy
5. 🔧 Set up BigQuery partitioning

### P1 - First Week
1. Add new analytics measures
2. Deploy dashboard updates
3. Implement structured logging
4. Configure alerts
5. Set up smoke tests

### P2 - First Month  
1. A/B test directives
2. Expand probe questions
3. Run locale matrix
4. Optimize token usage
5. Build executive dashboard

## Deployment Checklist

- [ ] All ship-blockers resolved
- [ ] Database migration applied
- [ ] Redis cache configured
- [ ] Rate limiting in place
- [ ] Structured logging deployed
- [ ] Alerts configured
- [ ] Smoke tests running
- [ ] Dashboard updated
- [ ] Team trained on new metrics
- [ ] Runbook documented