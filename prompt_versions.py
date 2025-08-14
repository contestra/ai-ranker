
# services/prompt_versions.py
# Ensure-version service with probe idempotency + Prometheus metrics (attempt/failure)
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

# ORM model (align with your models module)
from prompter.models import PromptVersion

# Optional Redis type import (ok if not available at runtime)
try:
    from redis import Redis  # type: ignore
except Exception:  # pragma: no cover
    Redis = None  # type: ignore

# Metrics: count probe attempts and failures
try:
    from prompter_metrics import record_probe_attempt, record_probe_failure
except Exception:  # pragma: no cover
    def record_probe_attempt(provider: str, model: str) -> None:  # type: ignore
        pass
    def record_probe_failure(provider: str, model: str) -> None:  # type: ignore
        pass

# Your provider probe function; must return (provider_version_key: str, captured_at: datetime)
def _default_probe(provider: str, model_id: str, *, system_instructions: Optional[str], inference_params: Dict[str, Any]) -> tuple[str, dt.datetime]:
    # Import locally to avoid circular imports
    from services.provider_probe import probe_provider_version  # type: ignore
    return probe_provider_version(provider=provider, model_id=model_id, system_instructions=system_instructions, inference_params=inference_params)

def _probe_key(org_id: str, workspace_id: str, template_id: str, provider: str, model_id: str, bucket: str) -> str:
    return f"probe:{org_id}:{workspace_id}:{template_id}:{provider}:{model_id}:{bucket}"

def ensure_version_service(
    db: Session, *, org_id: str, workspace_id: str, template_id: str,
    provider: str, model_id: str,
    system_instructions: Optional[str] = None,
    inference_params: Optional[Dict[str, Any]] = None,
    probe_func=None, redis: Optional["Redis"] = None, ttl_sec:int = 3600,
) -> Dict[str, Any]:
    """UPSERT a PromptVersion keyed by provider_version_key.

    - Invokes a provider probe (idempotent per hour via Redis NX/EX if provided).
    - Records Prometheus metrics: attempt and failure counts.
    - Returns {version_id, provider_version_key, captured_at}.
    """
    probe = probe_func or _default_probe

    # Optional idempotency: throttle redundant probes per hour-bucket
    if redis is not None:
        bucket = dt.datetime.utcnow().strftime("%Y%m%d%H")
        try:
            redis.set(_probe_key(org_id, workspace_id, template_id, provider, model_id, bucket), "1", nx=True, ex=ttl_sec)
        except Exception:
            # Redis issues shouldn't prevent version capture
            pass

    # Probe for provider version key, with metrics
    record_probe_attempt(provider, model_id)
    try:
        provider_version_key, captured_at = probe(
            provider=provider, model_id=model_id,
            system_instructions=system_instructions, inference_params=inference_params or {}
        )
    except Exception:
        record_probe_failure(provider, model_id)
        raise

    # Upsert PromptVersion by (org_id, workspace_id, template_id, provider_version_key)
    existing = db.execute(
        select(PromptVersion).where(
            PromptVersion.org_id == org_id,
            PromptVersion.workspace_id == workspace_id,
            PromptVersion.template_id == template_id,
            PromptVersion.provider_version_key == provider_version_key,
        )
    ).scalars().first()

    if existing:
        existing.last_seen_at = captured_at
        if not existing.fingerprint_captured_at:
            existing.fingerprint_captured_at = captured_at
        db.commit()
        return {"version_id": existing.id, "provider_version_key": provider_version_key, "captured_at": captured_at}

    ver = PromptVersion(
        org_id=org_id, workspace_id=workspace_id, template_id=template_id,
        provider=provider, provider_version_key=provider_version_key,
        model_id=model_id, fingerprint_captured_at=captured_at,
        first_seen_at=captured_at, last_seen_at=captured_at,
    )
    db.add(ver)
    try:
        db.commit(); db.refresh(ver)
        return {"version_id": ver.id, "provider_version_key": provider_version_key, "captured_at": captured_at}
    except IntegrityError:
        db.rollback()
        # A concurrent insert won; fetch the winner and bump timestamps
        winner = db.execute(
            select(PromptVersion).where(
                PromptVersion.org_id == org_id,
                PromptVersion.workspace_id == workspace_id,
                PromptVersion.template_id == template_id,
                PromptVersion.provider_version_key == provider_version_key,
            )
        ).scalars().first()
        if not winner:
            raise
        if winner.last_seen_at is None or captured_at > winner.last_seen_at:
            winner.last_seen_at = captured_at
        if not winner.fingerprint_captured_at:
            winner.fingerprint_captured_at = captured_at
        db.commit()
        return {"version_id": winner.id, "provider_version_key": provider_version_key, "captured_at": captured_at}
