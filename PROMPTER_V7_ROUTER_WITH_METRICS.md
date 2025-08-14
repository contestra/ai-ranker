# Prompter V7 Router with Integrated Metrics
## Production-Ready Implementation with Full Observability

**File**: `prompter_router_min v2.py`  
**Status**: Complete implementation with Prometheus metrics integrated  
**Purpose**: Drop-in ready router that automatically lights up monitoring dashboards

## Overview

The external model provided an updated version of the starter router with Prometheus metrics fully integrated. This version:
- Exports all metrics needed by the Grafana dashboard
- Records domain events automatically
- Includes Redis health monitoring
- Works immediately with zero additional configuration

## Key Enhancements

### 1. Metrics Import and Setup
```python
# Import metrics functions
from prompter_metrics import (
    setup_metrics,
    record_result_insert,
    record_db_unique,
    ensure_version_timer,
    set_redis_up,
)

# Setup metrics middleware and /metrics endpoint
app = FastAPI(title="Prompter API (minimal)")
setup_metrics(app)  # Adds HTTP metrics and /metrics endpoint
```

### 2. Database Unique Violation Tracking
```python
# In create_template endpoint
except IntegrityError:
    db.rollback()
    # Track deduplication blocks for monitoring
    try:
        record_db_unique("prompt_templates")
    except Exception:
        pass  # Don't fail the request if metrics fail
```
- Records when duplicate templates are blocked
- Helps monitor deduplication effectiveness
- Wrapped in try/except for resilience

### 3. Version Management Performance
```python
# In ensure_version endpoint
from contextlib import ExitStack
with ensure_version_timer(provider):
    info = ensure_version_service(
        db,
        org_id=tpl.org_id,
        workspace_id=tpl.workspace_id,
        template_id=tpl.id,
        provider=provider,
        model_id=model_id,
        # ... other params ...
    )
```
- Times the entire ensure-version operation
- Records latency by provider
- Enables p95/p99 monitoring

### 4. Result Insertion Tracking
```python
# In run_template endpoint after commit
db.commit()
db.refresh(result)

# Track result insertion and fingerprint presence
try:
    record_result_insert(bool(system_fingerprint))
except Exception:
    pass  # Don't fail if metrics fail
```
- Counts every result insertion
- Tracks OpenAI fingerprint presence
- Calculates fingerprint rate automatically

### 5. Redis Health Monitoring
```python
@app.on_event("startup")
def _metrics_redis_health_check():
    try:
        r = get_redis()
        ok = bool(r and (r.ping() if hasattr(r, 'ping') else True))
    except Exception:
        ok = False
    try:
        set_redis_up(ok)  # Set gauge to 0 or 1
    except Exception:
        pass
```
- Checks Redis on startup
- Sets health gauge (0=down, 1=up)
- Handles missing Redis gracefully

## Additional Features

### Fake LLM for Development
```python
def _fake_llm_response(provider: str, model_id: str, prompt: str) -> dict:
    """Generate fake response with proper metadata structure"""
    meta = {}
    if provider == 'openai':
        meta['system_fingerprint'] = f"fp_stub_{_hash8('openai:' + model_id)}"
    elif provider == 'google':
        meta['modelVersion'] = f"{model_id}-stub-001"
    elif provider == 'anthropic':
        meta['model'] = model_id
    # ... returns properly structured response
```
- Simulates provider responses for testing
- Includes correct metadata structure
- Enables testing without API keys

### Error Resilience
All metric calls are wrapped in try/except blocks:
```python
try:
    record_db_unique("prompt_templates")
except Exception:
    pass  # Metrics should never break the application
```
- Metrics failures don't affect functionality
- Application continues working even if metrics fail
- Silent degradation for observability

## Metrics Flow

### Request Lifecycle
1. **HTTP Request** → Middleware records method, route, status
2. **Create Template** → Records unique violations if duplicate
3. **Ensure Version** → Times operation, could record probe attempts
4. **Run Template** → Records result insertion and fingerprint
5. **Response** → Middleware records total latency

### Automatic Metrics (via Middleware)
```
starlette_requests_total{service="prompter-api",env="prod",method="POST",route="/api/prompt-templates",status="201"}
starlette_requests_processing_seconds_bucket{service="prompter-api",env="prod",method="POST",route="/api/prompt-templates"}
```

### Domain Metrics (via Helpers)
```
prompter_db_unique_violation_total{service="prompter-api",env="prod",table="prompt_templates"}
prompter_ensure_version_seconds{service="prompter-api",env="prod",provider="openai"}
prompter_prompt_results_insert_total{service="prompter-api",env="prod"}
prompter_openai_fingerprint_present_total{service="prompter-api",env="prod"}
prompter_redis_up{service="prompter-api",env="prod"} 1
```

## Usage Instructions

### 1. Install Dependencies
```bash
pip install prometheus-client fastapi sqlalchemy
```

### 2. Set Environment Variables
```bash
export METRICS_ENV=prod
export METRICS_SERVICE=prompter-api
export DB_URL=postgresql://...  # or sqlite:///./dev.db
```

### 3. Run the Server
```bash
uvicorn "prompter_router_min v2:app" --host 0.0.0.0 --port 8000
```

### 4. Verify Metrics
```bash
# Check metrics endpoint
curl http://localhost:8000/metrics

# Generate test traffic
curl -X POST http://localhost:8000/api/prompt-templates -H "Content-Type: application/json" -d '{...}'

# Check metrics again
curl http://localhost:8000/metrics | grep prompter
```

### 5. Configure Prometheus
```yaml
scrape_configs:
  - job_name: 'prompter'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### 6. Import Grafana Dashboard
- Use the provided `grafana_prompter_rollout_dashboard.json`
- Metrics will appear immediately
- No query modifications needed

## Testing the Integration

### Generate Metric Events
```python
# Test unique violation metric
# POST same template twice - second should increment counter

# Test ensure-version timing
# POST to /{id}/ensure-version - check histogram

# Test result insertion
# POST to /{id}/run - check counter and fingerprint presence

# Test Redis health
# Stop Redis, restart app - gauge should show 0
```

### Verify in Grafana
1. All panels should show data
2. Request rate should match your test traffic
3. Error rates should be near 0%
4. Latency percentiles should be reasonable
5. Redis should show as up (1) or down (0)

## Production Considerations

### Performance Impact
- Metrics add <1ms overhead per request
- Memory usage grows with unique label combinations
- Use bounded label values (not user IDs)

### High Availability
- Metrics are stateful (in-memory)
- Use pushgateway for ephemeral jobs
- Consider Prometheus federation for scale

### Security
- `/metrics` endpoint is public by default
- Add authentication if needed:
```python
from fastapi.security import HTTPBasic

security = HTTPBasic()

@metrics_router.get("/metrics")
def metrics(credentials: HTTPBasicCredentials = Depends(security)):
    # Verify credentials
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

## Extending the Metrics

### Add Probe Tracking in Service
The router is ready for probe metrics if you update `ensure_version_service`:
```python
# In services/prompt_versions.py
from prompter_metrics import record_probe_attempt, record_probe_failure

def ensure_version_service(...):
    record_probe_attempt(provider, model_id)
    try:
        pvk, captured = probe_openai(...)
    except Exception as e:
        record_probe_failure(provider, model_id)
        raise
```

### Add Cache Metrics
```python
from prometheus_client import Counter

CACHE_HIT = Counter('prompter_cache_hit_total', 'Cache hits')
CACHE_MISS = Counter('prompter_cache_miss_total', 'Cache misses')

# In your cache logic
if cached:
    CACHE_HIT.inc()
else:
    CACHE_MISS.inc()
```

## Benefits of This Version

1. **Zero Configuration** - Metrics work immediately
2. **Dashboard Ready** - Exact metric names for Grafana
3. **Production Patterns** - Error handling, resilience
4. **Development Friendly** - Fake LLM for testing
5. **Complete Integration** - All endpoints instrumented
6. **Startup Checks** - Redis health on startup

## Summary

This updated router with integrated metrics provides:
- ✅ Complete V7 implementation
- ✅ Full observability out of the box
- ✅ Automatic dashboard integration
- ✅ Production-ready error handling
- ✅ Development testing support
- ✅ Redis health monitoring

Simply drop in this file, install dependencies, and your monitoring dashboards will light up immediately with real metrics from your Prompter API!