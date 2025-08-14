
# Observability Starters (Grafana + DataDog)

This folder contains importable starters for your V7 rollout.

## Files
- `grafana_prompter_rollout_dashboard.json` — Grafana dashboard using Prometheus.
- `datadog_prompter_rollout_dashboard.json` — DataDog ordered dashboard.

## How to use

### Grafana (Prometheus)
1. In Grafana → Dashboards → New → Import → Upload `grafana_prompter_rollout_dashboard.json`.
2. Select your Prometheus datasource for the `DS_PROM` variable.
3. Set dashboard vars: `env`, `service` (defaults to `prod`, `prompter-api`).

**Metric names used (adjust if different):**
- Requests/Latency: `starlette_requests_total`, `starlette_requests_processing_seconds_bucket`
- Probes: `prompter_probe_attempts_total`, `prompter_probe_failures_total`
- Ensure-version: `prompter_ensure_version_seconds_bucket`
- Results: `prompter_prompt_results_insert_total`, `prompter_openai_fingerprint_present_total`
- Celery: `celery_task_runtime_seconds_bucket`, `celery_task_retries_total`
- Redis: `prompter_redis_up`
- DB unique violations: `prompter_db_unique_violation_total`

If your exporter uses different names, edit each panel’s PromQL accordingly.

### DataDog
1. In DataDog → Dashboards → New Dashboard → Import JSON → paste `datadog_prompter_rollout_dashboard.json`.
2. Template variables: `env`, `svc` map to tags `env:<env>` and `service:<svc>`.

**Metric names (placeholders; adjust to your setup):**
- `prompter.http.requests` — counter (req count)
- `prompter.http.status.4xx`, `prompter.http.status.5xx` — counters
- `prompter.http.latency` — **distribution** (to enable `p95()`)
- `prompter.probe.attempts`, `prompter.probe.failures` — counters
- `prompter.ensure_version.latency` — **distribution**
- `celery.task.retries` — counter
- `prompter.results.insert.count` — counter
- `prompter.results.openai_fingerprint.present` — counter
- `prompter.redis.up` — gauge
- `prompter.db.unique_violation` — counter

> Tip: If you rely on APM, you can swap requests/latency panels to use `trace.http.request.hits` and `trace.http.request.duration` with `service:$svc` and `env:$env` tags.

### Alert lines to consider
- API 5xx rate ≥ 1% (critical), ≥ 0.5% (warn)
- Probe failure rate ≥ 10% (warn at 5%)
- Ensure-version p95 ≥ 3s
- Redis down (avg(prompter.redis.up) < 1) for 2m
- DB unique violations > N/min (choose N based on normal baseline)

---

These are starters — import, wire your datasource/tags, and tweak queries to your real metric names. 
