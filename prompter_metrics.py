
# prompter_metrics.py
# Prometheus metrics for the Prompter API (V7) — FastAPI middleware + helpers
from __future__ import annotations

import os, time
from contextlib import contextmanager
from typing import Optional

from fastapi import APIRouter, Response, Request
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

ENV = os.getenv("METRICS_ENV", "dev")
SERVICE = os.getenv("METRICS_SERVICE", "prompter-api")

# -------- Core HTTP metrics (match Grafana panel names) --------
REQUEST_COUNT = Counter(
    "starlette_requests_total",
    "Total HTTP requests",
    labelnames=["service","env","method","route","status"],
)

REQUEST_LATENCY = Histogram(
    "starlette_requests_processing_seconds",
    "Request processing time in seconds",
    labelnames=["service","env","method","route"],
    # default buckets are fine; customize if needed
)

# -------- Domain metrics --------
PROBE_ATTEMPTS = Counter(
    "prompter_probe_attempts_total",
    "Total provider probe attempts",
    labelnames=["service","env","provider","model"],
)
PROBE_FAILURES = Counter(
    "prompter_probe_failures_total",
    "Total provider probe failures",
    labelnames=["service","env","provider","model"],
)

ENSURE_VERSION_SECONDS = Histogram(
    "prompter_ensure_version_seconds",
    "Ensure-version operation latency in seconds",
    labelnames=["service","env","provider"],
)

RESULTS_INSERT = Counter(
    "prompter_prompt_results_insert_total",
    "Number of prompt_results rows inserted",
    labelnames=["service","env"],
)

OPENAI_FP_PRESENT = Counter(
    "prompter_openai_fingerprint_present_total",
    "Count of results where OpenAI system_fingerprint is present",
    labelnames=["service","env"],
)

REDIS_UP = Gauge(
    "prompter_redis_up",
    "Redis health (1 ok, 0 down)",
    labelnames=["service","env"],
)

DB_UNIQUE_VIOLATION = Counter(
    "prompter_db_unique_violation_total",
    "Database unique-violation errors",
    labelnames=["service","env","table"],
)

# -------- FastAPI middleware --------
class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        method = request.method
        # Use route template if available (e.g., /api/prompt-templates/{template_id}/run)
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        status_code = 500
        try:
            response = await call_next(request)
            status_code = getattr(response, "status_code", 200)
            return response
        finally:
            elapsed = time.perf_counter() - start
            REQUEST_COUNT.labels(SERVICE, ENV, method, route_path, str(status_code)).inc()
            REQUEST_LATENCY.labels(SERVICE, ENV, method, route_path).observe(elapsed)

# -------- Router to expose /metrics --------
metrics_router = APIRouter()
@metrics_router.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

def setup_metrics(app):
    """Attach middleware and /metrics route to a FastAPI app."""
    app.add_middleware(PrometheusMiddleware)
    app.include_router(metrics_router)

# -------- Helper functions to use inside your code --------
def record_probe_attempt(provider: str, model: str) -> None:
    PROBE_ATTEMPTS.labels(SERVICE, ENV, provider, model).inc()

def record_probe_failure(provider: str, model: str) -> None:
    PROBE_FAILURES.labels(SERVICE, ENV, provider, model).inc()

@contextmanager
def ensure_version_timer(provider: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        ENSURE_VERSION_SECONDS.labels(SERVICE, ENV, provider).observe(time.perf_counter() - start)

def record_result_insert(has_openai_fp: bool) -> None:
    RESULTS_INSERT.labels(SERVICE, ENV).inc()
    if has_openai_fp:
        OPENAI_FP_PRESENT.labels(SERVICE, ENV).inc()

def set_redis_up(ok: bool) -> None:
    REDIS_UP.labels(SERVICE, ENV).set(1 if ok else 0)

def record_db_unique(table: str) -> None:
    DB_UNIQUE_VIOLATION.labels(SERVICE, ENV, table).inc()
