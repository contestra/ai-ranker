
# How to wire Prometheus metrics (V7)

## 1) Install dependency
```bash
pip install prometheus-client
```

## 2) Mount middleware and /metrics
In your app entry (e.g., `prompter_router_min.py`), add:
```python
from prompter_metrics import setup_metrics
setup_metrics(app)  # after app = FastAPI(...)
```

## 3) Record domain metrics

### a) Results insert (in `/{template_id}/run` after DB commit)
```python
from prompter_metrics import record_result_insert
has_fp = bool(system_fingerprint)  # OpenAI only
record_result_insert(has_fp)
```

### b) Unique-violation handling (create template IntegrityError)
```python
from prompter_metrics import record_db_unique
# inside `except IntegrityError:` block before raising 409
record_db_unique("prompt_templates")
```

### c) Ensure-version timing + provider probes
Wrap the code in your ensure-version service or router:
```python
from prompter_metrics import ensure_version_timer, record_probe_attempt, record_probe_failure

with ensure_version_timer(provider):
    record_probe_attempt(provider, model_id)
    try:
        provider_version_key, captured_at = probe_func(...)
    except Exception:
        record_probe_failure(provider, model_id)
        raise
```

### d) Redis health (e.g., on startup or periodic task)
```python
from prompter_metrics import set_redis_up
try:
    r = get_redis()
    ok = bool(r and r.ping())
except Exception:
    ok = False
set_redis_up(ok)
```

## 4) Scrape endpoint
Configure Prometheus to scrape `http://<host>:<port>/metrics`.

**Env tags**
Optionally set:
```bash
export METRICS_ENV=prod
export METRICS_SERVICE=prompter-api
```
They appear as labels on all metrics and match the provided Grafana queries.
