# Prompter V7 Observability Dashboards
## Production Monitoring for Grafana and DataDog

**Status**: Complete dashboard templates ready for import  
**Purpose**: Monitor V7 rollout health, performance, and adoption metrics  
**Files Provided**:
- `grafana_prompter_rollout_dashboard.json` - Grafana dashboard using Prometheus
- `datadog_prompter_rollout_dashboard.json` - DataDog ordered dashboard
- `observability_readme.md` - Quick setup guide

## Overview

The external model provided production-ready observability dashboards for monitoring the V7 Prompter rollout. These dashboards track:
- API health and performance
- Provider probe success rates
- Version management latency
- Database deduplication effectiveness
- Worker queue performance
- Redis availability
- Result insertion metrics

## Grafana Dashboard (Prometheus)

### Key Features
- **Multi-environment support** via template variables
- **Service isolation** for multi-tenant deployments
- **Time-series panels** for trend analysis
- **Alert thresholds** pre-configured
- **Responsive layout** optimized for operations

### Metrics Tracked

#### API Health
```promql
# Request rate
rate(starlette_requests_total{env="$env",service="$service"}[5m])

# Error rates (4xx, 5xx)
rate(starlette_requests_total{env="$env",status=~"4.."}[5m])
rate(starlette_requests_total{env="$env",status=~"5.."}[5m])

# Latency percentiles
histogram_quantile(0.95, 
  rate(starlette_requests_processing_seconds_bucket{env="$env"}[5m])
)
```

#### Provider Probes
```promql
# Probe attempts
rate(prompter_probe_attempts_total{env="$env"}[5m])

# Probe failures
rate(prompter_probe_failures_total{env="$env"}[5m])

# Failure rate
100 * (
  rate(prompter_probe_failures_total[5m]) / 
  rate(prompter_probe_attempts_total[5m])
)
```

#### Version Management
```promql
# Ensure-version latency (p50, p95, p99)
histogram_quantile(0.95,
  rate(prompter_ensure_version_seconds_bucket{env="$env"}[5m])
)

# Version cache hit rate
rate(prompter_version_cache_hits_total[5m]) /
rate(prompter_version_lookups_total[5m])
```

#### Database Operations
```promql
# Unique constraint violations (dedup working)
rate(prompter_db_unique_violation_total{env="$env"}[5m])

# Result insertions
rate(prompter_prompt_results_insert_total{env="$env"}[5m])

# OpenAI fingerprint presence
rate(prompter_openai_fingerprint_present_total[5m]) /
rate(prompter_prompt_results_insert_total[5m])
```

#### Infrastructure
```promql
# Redis availability
prompter_redis_up{env="$env"}

# Celery task performance
histogram_quantile(0.95,
  rate(celery_task_runtime_seconds_bucket{queue="prompter"}[5m])
)

# Task retry rate
rate(celery_task_retries_total{queue="prompter"}[5m])
```

### Installation

1. **Import Dashboard**
   ```
   Grafana → Dashboards → New → Import
   Upload: grafana_prompter_rollout_dashboard.json
   ```

2. **Configure Datasource**
   - Select your Prometheus instance for `DS_PROM`
   - Ensure metrics are being scraped

3. **Set Template Variables**
   - `env`: Environment (prod, staging, dev)
   - `service`: Service name (prompter-api)

4. **Adjust Metric Names** (if different)
   ```javascript
   // Edit panel queries if your exporters use different names
   // Example: change 'starlette_requests_total' to 'http_requests_total'
   ```

## DataDog Dashboard

### Key Features
- **APM Integration** ready
- **Distribution metrics** for accurate percentiles
- **Tag-based filtering** for multi-tenant
- **Ordered layout** for incident response
- **Mobile-responsive** design

### Metrics Configuration

#### Core Metrics (Counters)
```
prompter.http.requests         # Total request count
prompter.http.status.4xx       # 4xx responses
prompter.http.status.5xx       # 5xx responses
prompter.probe.attempts        # Provider probe attempts
prompter.probe.failures        # Provider probe failures
prompter.results.insert.count  # Results inserted
prompter.db.unique_violation   # Dedup blocks
celery.task.retries            # Worker retries
```

#### Distribution Metrics (for percentiles)
```
prompter.http.latency          # API latency
prompter.ensure_version.latency # Version check latency
```

#### Gauge Metrics
```
prompter.redis.up              # Redis availability (0/1)
```

### Dashboard Widgets

1. **Health Overview**
   - API requests/sec
   - 4xx error rate %
   - 5xx error rate %
   - p95 latency

2. **Provider Probes**
   - Probe attempts/min
   - Probe failure rate %
   - Provider breakdown

3. **Version Management**
   - Ensure-version calls/min
   - p95 latency
   - Cache hit rate

4. **Database Performance**
   - Unique violations/min (healthy dedup)
   - Result insertions/min
   - OpenAI fingerprint presence %

5. **Infrastructure**
   - Redis availability
   - Celery queue depth
   - Task retry rate

### Installation

1. **Import Dashboard**
   ```
   DataDog → Dashboards → New Dashboard → Import JSON
   Paste: datadog_prompter_rollout_dashboard.json
   ```

2. **Configure Template Variables**
   - `env`: Maps to tag `env:<value>`
   - `svc`: Maps to tag `service:<value>`

3. **Verify Metrics**
   ```bash
   # Check metrics are flowing
   datadog metric list --filter "prompter"
   ```

4. **Adjust for APM** (optional)
   ```javascript
   // Replace custom metrics with APM traces
   trace.http.request.hits{service:$svc}
   trace.http.request.duration{service:$svc}
   ```

## Alert Recommendations

### Critical Alerts

1. **API 5xx Rate > 1%**
   ```yaml
   condition: avg(last_5m) > 0.01
   message: "Prompter API error rate critical: {{value}}%"
   ```

2. **Redis Down**
   ```yaml
   condition: avg(last_2m) < 1
   message: "Prompter Redis unavailable"
   ```

3. **Probe Failure Rate > 10%**
   ```yaml
   condition: avg(last_5m) > 0.10
   message: "Provider probe failures high: {{value}}%"
   ```

### Warning Alerts

1. **API 5xx Rate > 0.5%**
   ```yaml
   condition: avg(last_5m) > 0.005
   message: "Prompter API errors elevated"
   ```

2. **Ensure-version p95 > 3s**
   ```yaml
   condition: p95(last_5m) > 3000
   message: "Version management slow"
   ```

3. **Unique Violations Spike**
   ```yaml
   condition: change(last_10m) > 100
   message: "Deduplication blocks spiking"
   ```

## Rollout Monitoring Strategy

### Phase 1: Canary (5% traffic)
Monitor closely:
- Error rates (should match baseline)
- Latency (no degradation)
- Probe success (>90%)
- Unique violations (expected initially)

### Phase 2: Expansion (25% traffic)
Watch for:
- Scale effects on latency
- Redis connection pool saturation
- Database connection limits
- Worker queue depth

### Phase 3: Full Rollout (100% traffic)
Focus on:
- Steady-state performance
- Cost metrics (API calls to providers)
- Cache effectiveness
- Long-term trends

## Custom Metrics Implementation

### Python (Prometheus)
```python
from prometheus_client import Counter, Histogram, Gauge

# Counters
probe_attempts = Counter('prompter_probe_attempts_total', 
                         'Provider probe attempts',
                         ['provider', 'env'])
probe_failures = Counter('prompter_probe_failures_total',
                         'Provider probe failures', 
                         ['provider', 'env'])

# Histogram for latency
ensure_version_latency = Histogram('prompter_ensure_version_seconds',
                                   'Ensure version latency',
                                   ['env'])

# Gauge for Redis
redis_up = Gauge('prompter_redis_up', 'Redis availability', ['env'])

# Usage
probe_attempts.labels(provider='openai', env='prod').inc()
with ensure_version_latency.labels(env='prod').time():
    ensure_version_service(...)
redis_up.labels(env='prod').set(1 if redis_healthy else 0)
```

### Python (DataDog)
```python
from datadog import statsd

# Counters
statsd.increment('prompter.probe.attempts', tags=['provider:openai'])
statsd.increment('prompter.probe.failures', tags=['provider:openai'])

# Distribution (for percentiles)
statsd.distribution('prompter.ensure_version.latency', latency_ms)

# Gauge
statsd.gauge('prompter.redis.up', 1 if redis_healthy else 0)

# With timing decorator
@statsd.timed('prompter.ensure_version.latency')
def ensure_version_service(...):
    ...
```

## Troubleshooting

### Missing Metrics
1. Verify exporter is running
2. Check scrape configuration (Prometheus)
3. Verify DataDog agent configuration
4. Check metric naming conventions

### High Cardinality
1. Limit label values (don't use user IDs)
2. Use template variables for filtering
3. Aggregate at query time, not collection

### Performance Impact
1. Use sampling for high-volume metrics
2. Adjust scrape intervals (Prometheus)
3. Use metric aggregation (DataDog)

## Best Practices

### Dashboard Design
1. **Top-down layout** - Overview → Details
2. **Consistent time ranges** - All panels aligned
3. **Color coding** - Red=bad, Yellow=warning, Green=good
4. **Annotations** - Mark deployments and incidents
5. **Mobile-friendly** - Test on small screens

### Metric Naming
```
prompter.{component}.{metric}.{unit}
prompter.api.requests.total
prompter.probe.latency.seconds
prompter.cache.hits.count
```

### Tagging Strategy
```yaml
Required tags:
- env: prod|staging|dev
- service: prompter-api
- provider: openai|google|anthropic

Optional tags:
- workspace_id: for multi-tenant
- version: for A/B testing
- region: for geo-distribution
```

## Integration with Existing Monitoring

### Combine with Business Metrics
- Brand analysis completion rate
- AI model response quality scores
- User engagement with results
- Cost per analysis

### Link to Infrastructure Monitoring
- Database connection pools
- Redis memory usage
- Kubernetes pod metrics
- Network latency to providers

### Connect to Incident Management
- PagerDuty integration for critical alerts
- Slack notifications for warnings
- Runbook links in alert descriptions
- Automatic ticket creation

## Summary

These observability dashboards provide:
- ✅ **Complete visibility** into V7 rollout health
- ✅ **Production-ready** alert thresholds
- ✅ **Multi-environment** support
- ✅ **Easy import** with minimal configuration
- ✅ **Extensible design** for custom metrics
- ✅ **Best practices** built-in

The dashboards are designed to give operations teams confidence during the V7 rollout and ongoing operations. They focus on the metrics that matter most for system health and user experience.