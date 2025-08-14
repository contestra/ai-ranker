# Prompter V7 Prometheus Metrics Module
## Plug-and-Play Metrics for Instant Dashboard Integration

**Status**: Complete metrics implementation ready to wire  
**Purpose**: Export exact metrics that Grafana dashboard expects  
**Files**:
- `prompter_metrics.py` - Complete Prometheus metrics module
- `METRICS_INTEGRATION_PATCH.md` - Wiring instructions

## Overview

The external model provided a complete Prometheus metrics module that:
- Exports the exact metric names used in the Grafana dashboard
- Provides FastAPI middleware for automatic HTTP metrics
- Includes helper functions for domain-specific metrics
- Creates a `/metrics` endpoint for Prometheus scraping
- Works immediately with the provided Grafana dashboard

## Metrics Exported

### HTTP Metrics (Automatic via Middleware)

#### Request Counter
```python
starlette_requests_total{service,env,method,route,status}
```
- Counts all HTTP requests
- Labels include service, environment, method, route, status code
- Automatically incremented by middleware

#### Request Latency Histogram
```python
starlette_requests_processing_seconds_bucket{service,env,method,route}
```
- Tracks request processing time
- Provides percentiles (p50, p95, p99)
- Automatically recorded by middleware

### Domain-Specific Metrics

#### Provider Probes
```python
prompter_probe_attempts_total{service,env,provider,model}
prompter_probe_failures_total{service,env,provider,model}
```
- Track provider API probe attempts and failures
- Calculate failure rate: failures/attempts
- Labels include provider (openai, google, anthropic) and model

#### Version Management
```python
prompter_ensure_version_seconds{service,env,provider}
```
- Histogram of ensure-version operation latency
- Useful for tracking performance degradation
- Provides percentiles for SLA monitoring

#### Result Tracking
```python
prompter_prompt_results_insert_total{service,env}
prompter_openai_fingerprint_present_total{service,env}
```
- Count result insertions
- Track OpenAI fingerprint presence (version tracking effectiveness)
- Calculate fingerprint rate: fingerprint_present/results_insert

#### Infrastructure Health
```python
prompter_redis_up{service,env}  # Gauge: 1=up, 0=down
prompter_db_unique_violation_total{service,env,table}
```
- Redis availability gauge
- Database unique constraint violations (deduplication working)

## Installation

### 1. Install Dependencies
```bash
pip install prometheus-client
```

### 2. Add to Requirements
```python
# requirements.txt
prometheus-client>=0.19.0
```

## Integration Steps

### 1. Basic Setup
```python
# In your main app file (e.g., prompter_router_min.py)
from fastapi import FastAPI
from prompter_metrics import setup_metrics

app = FastAPI(title="Prompter API")

# Add metrics middleware and /metrics endpoint
setup_metrics(app)

# Your routes...
app.include_router(router)
```

### 2. Record Result Insertions
```python
# In run_template endpoint after inserting result
from prompter_metrics import record_result_insert

@router.post("/{template_id}/run")
def run_template(template_id: str, req: RunTemplateRequest):
    # ... create result ...
    db.add(result)
    db.commit()
    
    # Record metrics
    has_openai_fp = bool(system_fingerprint)  # Only for OpenAI
    record_result_insert(has_openai_fp)
    
    return RunTemplateOut(...)
```

### 3. Track Unique Violations
```python
# In create_template endpoint
from prompter_metrics import record_db_unique

@router.post("")
def create_template(req: CreateTemplateRequest):
    try:
        db.add(row)
        db.commit()
    except IntegrityError:
        db.rollback()
        record_db_unique("prompt_templates")  # Track dedup block
        raise HTTPException(409, ...)
```

### 4. Monitor Ensure-Version Performance
```python
# In ensure_version_service function
from prompter_metrics import (
    ensure_version_timer,
    record_probe_attempt,
    record_probe_failure
)

def ensure_version_service(db, provider, model_id, **kwargs):
    with ensure_version_timer(provider):
        record_probe_attempt(provider, model_id)
        try:
            # Call provider probe
            pvk, captured_at = probe_openai(model_id, **kwargs)
        except Exception as e:
            record_probe_failure(provider, model_id)
            raise
        
        # ... rest of logic ...
```

### 5. Monitor Redis Health
```python
# In startup or health check
from prompter_metrics import set_redis_up

@app.on_event("startup")
async def startup_event():
    # Check Redis
    try:
        r = get_redis()
        ok = bool(r and r.ping())
    except Exception:
        ok = False
    set_redis_up(ok)

# Or in a periodic task
@repeat_every(seconds=30)
def check_redis_health():
    try:
        r = get_redis()
        set_redis_up(bool(r and r.ping()))
    except:
        set_redis_up(False)
```

## Environment Configuration

### Set Service Labels
```bash
# These appear as labels on all metrics
export METRICS_ENV=prod          # or staging, dev
export METRICS_SERVICE=prompter-api
```

### Docker Configuration
```dockerfile
ENV METRICS_ENV=prod
ENV METRICS_SERVICE=prompter-api
```

### Kubernetes ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prompter-config
data:
  METRICS_ENV: "prod"
  METRICS_SERVICE: "prompter-api"
```

## Prometheus Configuration

### Scrape Configuration
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'prompter'
    static_configs:
      - targets: ['prompter-api:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Service Discovery (Kubernetes)
```yaml
scrape_configs:
  - job_name: 'prompter'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        regex: prompter-api
        action: keep
```

## Testing Metrics

### 1. Verify Endpoint
```bash
# Check metrics are exposed
curl http://localhost:8000/metrics

# Expected output (sample):
# HELP starlette_requests_total Total HTTP requests
# TYPE starlette_requests_total counter
starlette_requests_total{env="dev",method="POST",route="/api/prompt-templates",service="prompter-api",status="201"} 5.0
```

### 2. Generate Test Traffic
```python
# test_metrics.py
import requests

# Create template (should increment counters)
r = requests.post("http://localhost:8000/api/prompt-templates", json={...})

# Check metrics
metrics = requests.get("http://localhost:8000/metrics").text
assert "starlette_requests_total" in metrics
assert "prompter_db_unique_violation_total" in metrics  # if duplicate
```

### 3. Verify in Grafana
1. Import the provided dashboard
2. Select your Prometheus datasource
3. Metrics should appear immediately
4. Generate some test traffic to see graphs

## Advanced Usage

### Custom Buckets for Histograms
```python
# For different latency ranges
from prometheus_client import Histogram

CUSTOM_LATENCY = Histogram(
    "prompter_custom_latency_seconds",
    "Custom operation latency",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)  # seconds
)
```

### Multi-Process Mode (Gunicorn)
```python
# For multi-worker deployments
from prometheus_client import multiprocess
from prometheus_client import generate_latest
from prometheus_client import CollectorRegistry
from prometheus_client import CONTENT_TYPE_LATEST

@metrics_router.get("/metrics")
def metrics():
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    return Response(
        generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST
    )
```

### Rate Limiting Metrics
```python
# Track rate limit hits
RATE_LIMIT_HIT = Counter(
    "prompter_rate_limit_hit_total",
    "Rate limit violations",
    labelnames=["service","env","endpoint"]
)

# In rate limit middleware
if rate_limited:
    RATE_LIMIT_HIT.labels(SERVICE, ENV, endpoint).inc()
```

## Performance Considerations

### Metric Cardinality
- Keep label values bounded (don't use user IDs)
- Use route templates, not raw paths
- Limit provider/model combinations

### Memory Usage
- Each unique label combination creates a time series
- Monitor Prometheus memory usage
- Use recording rules for complex queries

### Scrape Interval
- Default 15s is usually fine
- Increase for high-volume services
- Decrease for critical metrics

## Troubleshooting

### Metrics Not Appearing
1. Check `/metrics` endpoint is accessible
2. Verify Prometheus can reach the service
3. Check firewall/security group rules
4. Review Prometheus logs for scrape errors

### High Memory Usage
1. Check metric cardinality
2. Review label combinations
3. Consider aggregation at query time
4. Use recording rules

### Incorrect Values
1. Ensure helpers are called in right places
2. Check exception handling (metrics in finally blocks)
3. Verify label values are consistent

## Benefits

### Instant Dashboard Integration
- Metrics match Grafana dashboard exactly
- No query modifications needed
- Works out of the box

### Production Ready
- Battle-tested metric names
- Proper label structure
- Efficient implementation

### Easy to Extend
- Clear helper functions
- Well-organized by domain
- Simple to add new metrics

## Complete Integration Example

```python
# prompter_router_min.py with full metrics integration
from fastapi import FastAPI
from prompter_metrics import (
    setup_metrics,
    record_result_insert,
    record_db_unique,
    ensure_version_timer,
    record_probe_attempt,
    record_probe_failure,
    set_redis_up
)

app = FastAPI()
setup_metrics(app)  # Add middleware and /metrics

@router.post("")
def create_template(req: CreateTemplateRequest, db: Session = Depends(get_db)):
    try:
        # ... create template ...
        db.commit()
    except IntegrityError:
        db.rollback()
        record_db_unique("prompt_templates")  # Track dedup
        raise HTTPException(409, ...)
    return TemplateOut(...)

@router.post("/{template_id}/ensure-version")
def ensure_version(template_id: str, body: EnsureVersionIn):
    with ensure_version_timer(provider):  # Time the operation
        record_probe_attempt(provider, model_id)
        try:
            # ... probe provider ...
        except Exception:
            record_probe_failure(provider, model_id)
            raise
    return EnsureVersionOut(...)

@router.post("/{template_id}/run")
def run_template(template_id: str, req: RunTemplateRequest):
    # ... run template and create result ...
    db.commit()
    
    # Track result metrics
    has_fp = bool(system_fingerprint) if provider == "openai" else False
    record_result_insert(has_fp)
    
    return RunTemplateOut(...)

# Health check with Redis monitoring
@app.on_event("startup")
async def startup():
    try:
        r = get_redis()
        set_redis_up(bool(r and r.ping()))
    except:
        set_redis_up(False)
```

## Summary

This Prometheus metrics module provides:
- ✅ **Exact metric names** matching Grafana dashboard
- ✅ **Automatic HTTP metrics** via middleware
- ✅ **Domain-specific helpers** for easy integration
- ✅ **Production-ready** implementation
- ✅ **Zero configuration** needed for basic setup
- ✅ **Instant dashboard** functionality

Simply wire it in and your Grafana dashboard will light up immediately with real metrics!