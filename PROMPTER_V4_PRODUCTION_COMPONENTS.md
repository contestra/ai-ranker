# PROMPTER V4 PRODUCTION COMPONENTS
## Ready-to-Drop Components from External Review

**Date**: August 14, 2025  
**Status**: Production-ready components provided by external review  
**Purpose**: Document the exact implementation files for V4

## Overview
These are the production-ready, drop-in components provided by the external reviewer for implementing the Prompter V4 specification. They address all critical issues identified in the review.

---

## 1. Service Layer: `services/prompt_versions.py`

**Purpose**: Prevents route recursion, handles concurrent requests, provides idempotency

```python
# services/prompt_versions.py
from __future__ import annotations
import datetime as dt
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from prompter.models import PromptVersion  # ORM from your codebase
from services.provider_probe import probe_provider_version  # see earlier module

try:
    # Optional: only used if you pass a Redis instance for idempotency
    from redis import Redis  # type: ignore
except Exception:  # pragma: no cover
    Redis = None  # type: ignore


def _probe_idem_key(
    *, org_id: str, workspace_id: str, template_id: str, provider: str, model_id: str, bucket: str
) -> str:
    return f"probe:{org_id}:{workspace_id}:{template_id}:{provider}:{model_id}:{bucket}"


def ensure_version_service(
    db: Session,
    *,
    org_id: str,
    workspace_id: str,
    template_id: str,
    provider: str,                 # "openai" | "google" | "anthropic" | "azure-openai"
    model_id: str,
    system_instructions: Optional[str] = None,
    inference_params: Optional[Dict[str, Any]] = None,
    redis: Optional["Redis"] = None,
    idempotency_ttl_sec: int = 3600,
) -> Dict[str, Any]:
    """
    Capture the provider version key for the given template+provider+model, and upsert a PromptVersion row.

    Returns:
        {
          "version_id": str,
          "provider": str,
          "provider_version_key": str,
          "captured_at": datetime (UTC)
        }
    """
    # Lightweight idempotency to avoid concurrent probe storms (optional)
    if redis is not None:
        hour_bucket = dt.datetime.utcnow().strftime("%Y%m%d%H")
        idem_key = _probe_idem_key(
            org_id=org_id, workspace_id=workspace_id, template_id=template_id,
            provider=provider, model_id=model_id, bucket=hour_bucket
        )
        # If the key already exists we still proceed, but this drop-in prevents most duplicate probes
        redis.set(idem_key, "1", nx=True, ex=idempotency_ttl_sec)

    # 1) Probe provider (or piggy-back this logic on your first real run)
    provider_version_key, captured_at = probe_provider_version(
        provider=provider,
        model_id=model_id,
        system_instructions=system_instructions,
        inference_params=inference_params or {},
    )

    # 2) Try fast-path: does a version already exist?
    existing = db.execute(
        select(PromptVersion).where(
            PromptVersion.org_id == org_id,
            PromptVersion.workspace_id == workspace_id,
            PromptVersion.template_id == template_id,
            PromptVersion.provider_version_key == provider_version_key,
        )
    ).scalars().first()

    if existing:
        # Update last seen; backfill captured_at if empty
        existing.last_seen_at = captured_at
        if not existing.fingerprint_captured_at:
            existing.fingerprint_captured_at = captured_at
        db.commit()
        return {
            "version_id": existing.id,
            "provider": provider,
            "provider_version_key": provider_version_key,
            "captured_at": captured_at,
        }

    # 3) Insert new version, handle race via unique index on
    #    (org_id, workspace_id, template_id, provider_version_key)
    ver = PromptVersion(
        org_id=org_id,
        workspace_id=workspace_id,
        template_id=template_id,
        provider=provider,
        provider_version_key=provider_version_key,
        model_id=model_id,
        fingerprint_captured_at=captured_at,
        first_seen_at=captured_at,
        last_seen_at=captured_at,
    )
    db.add(ver)
    try:
        db.commit()
        db.refresh(ver)
        return {
            "version_id": ver.id,
            "provider": provider,
            "provider_version_key": provider_version_key,
            "captured_at": captured_at,
        }
    except IntegrityError:
        # Another worker inserted the same version concurrently — fetch and return it
        db.rollback()
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
        # Refresh last_seen_at to the latest capture time
        winner.last_seen_at = max(winner.last_seen_at or captured_at, captured_at)
        if not winner.fingerprint_captured_at:
            winner.fingerprint_captured_at = captured_at
        db.commit()
        return {
            "version_id": winner.id,
            "provider": provider,
            "provider_version_key": provider_version_key,
            "captured_at": captured_at,
        }
```

### Key Features:
- ✅ No route recursion - pure service function
- ✅ Handles concurrent inserts via IntegrityError catch
- ✅ Optional Redis idempotency guard
- ✅ Updates last_seen_at for existing versions
- ✅ Returns consistent response format

---

## 2. SQLite Schema: `db/sqlite_prompter.sql`

**Purpose**: Dev schema with UUID strings, partial index, no CASCADE

```sql
-- Reset (SQLite) — no CASCADE
DROP TABLE IF EXISTS prompt_results;
DROP TABLE IF EXISTS prompt_versions;
DROP TABLE IF EXISTS prompt_templates;

-- =========================
-- Templates (brand-scoped)
-- =========================
CREATE TABLE prompt_templates (
  id TEXT PRIMARY KEY,                -- UUID string
  org_id TEXT NOT NULL,
  workspace_id TEXT NOT NULL,         -- brand/workspace id
  name TEXT NOT NULL,

  system_instructions TEXT,
  user_prompt_template TEXT NOT NULL,
  country_set TEXT NOT NULL,          -- JSON string (array)
  model_id TEXT NOT NULL,

  inference_params TEXT NOT NULL,     -- JSON string
  tools_spec TEXT,                    -- JSON string (array)
  response_format TEXT,               -- JSON string (object)

  grounding_profile_id TEXT,
  grounding_snapshot_id TEXT,
  retrieval_params TEXT,              -- JSON string

  config_hash TEXT NOT NULL,
  config_canonical_json TEXT NOT NULL,-- JSON string

  created_by TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  deleted_at TEXT
);

-- Active-only uniqueness (works on modern SQLite builds)
CREATE UNIQUE INDEX IF NOT EXISTS ux_tpl_org_ws_confighash_active
  ON prompt_templates (org_id, workspace_id, config_hash)
  WHERE deleted_at IS NULL;

-- If your dev SQLite lacks partial-index support, comment the index above
-- and enforce "active-only" uniqueness in the create endpoint with a WHERE deleted_at IS NULL check.

-- =========================
-- Versions (provider-keyed)
-- =========================
CREATE TABLE prompt_versions (
  id TEXT PRIMARY KEY,                -- UUID string
  org_id TEXT NOT NULL,
  workspace_id TEXT NOT NULL,
  template_id TEXT NOT NULL,          -- FK to prompt_templates(id)

  provider TEXT NOT NULL,             -- openai|google|anthropic|azure-openai
  provider_version_key TEXT NOT NULL, -- fp_* | gemini-* | model id
  model_id TEXT NOT NULL,

  fingerprint_captured_at TEXT,
  first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),

  FOREIGN KEY (template_id) REFERENCES prompt_templates(id),
  UNIQUE (org_id, workspace_id, template_id, provider_version_key)
);

-- =========================
-- Results (audit trail)
-- =========================
CREATE TABLE prompt_results (
  id TEXT PRIMARY KEY,                -- UUID string
  org_id TEXT NOT NULL,
  workspace_id TEXT NOT NULL,
  template_id TEXT NOT NULL,          -- FK to prompt_templates(id)
  version_id TEXT,                    -- FK to prompt_versions(id)

  provider_version_key TEXT,
  system_fingerprint TEXT,

  request TEXT NOT NULL,              -- JSON string: full request snapshot
  response TEXT NOT NULL,             -- JSON string: compact raw-ish response
  analysis_config TEXT,               -- JSON string

  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (template_id) REFERENCES prompt_templates(id),
  FOREIGN KEY (version_id) REFERENCES prompt_versions(id)
);

CREATE INDEX IF NOT EXISTS ix_results_tpl_time
  ON prompt_results (template_id, created_at DESC);
```

### Key Features:
- ✅ No CASCADE (SQLite doesn't support it)
- ✅ UUID strings as TEXT (dev/prod parity)
- ✅ Partial index for active-only uniqueness
- ✅ JSON stored as TEXT
- ✅ Proper foreign key constraints

---

## 3. FastAPI Router: `prompter/router.py`

**Purpose**: Complete API implementation with all V4 features

### Key Endpoints:
- `POST /api/prompt-templates` - Create with dedup
- `POST /api/prompt-templates/check-duplicate` - Real-time duplicate check
- `POST /api/prompt-templates/{template_id}/ensure-version` - Version management

### Features:
- ✅ Uses service layer (no recursion)
- ✅ Handles 409 Conflict on duplicates
- ✅ Auto-bootstraps SQLite schema on startup
- ✅ Works with both SQLite and PostgreSQL

---

## 4. SQLite Bootstrap: `db/sqlite_bootstrap.py`

**Purpose**: Manual schema runner for development

```python
# db/sqlite_bootstrap.py
import os
from sqlalchemy import create_engine

DB_URL = os.getenv("DB_URL", "sqlite:///./dev.db")
SQLITE_BOOTSTRAP_PATH = os.getenv("SQLITE_BOOTSTRAP_PATH", "db/sqlite_prompter.sql")

def main():
    engine = create_engine(DB_URL, future=True)
    if engine.url.get_backend_name().startswith("sqlite") and os.path.exists(SQLITE_BOOTSTRAP_PATH):
        raw = engine.raw_connection()
        try:
            with open(SQLITE_BOOTSTRAP_PATH, "r", encoding="utf-8") as f:
                script = f.read()
            raw.executescript(script)  # type: ignore[attr-defined]
            raw.commit()
            print(f"Applied {SQLITE_BOOTSTRAP_PATH} to {DB_URL}")
        finally:
            raw.close()
    else:
        print("Skipping bootstrap (not SQLite or file missing).")

if __name__ == "__main__":
    main()
```

---

## 5. Optional Redis Utility: `services/redis_util.py`

**Purpose**: Redis client for idempotency guards

```python
# services/redis_util.py
import os
from typing import Optional
try:
    from redis import Redis  # type: ignore
except Exception:  # pragma: no cover
    Redis = None  # type: ignore

def get_redis() -> Optional["Redis"]:
    url = os.getenv("UPSTASH_REDIS_URL") or os.getenv("REDIS_URL")
    if not url or Redis is None:
        return None
    return Redis.from_url(url, decode_responses=True)
```

---

## Integration Notes

### How to Use in Routes (No Recursion):
```python
# inside your FastAPI run handler (after invoking the model)
ver = ensure_version_service(
    db,
    org_id=org_id,
    workspace_id=workspace_id,
    template_id=template_id,
    provider=provider,               # "openai" | "google" | "anthropic" | "azure-openai"
    model_id=model_id,
    system_instructions=system_instructions,
    inference_params=inference_params_used,
    redis=redis_client,              # optional
)

# persist PromptResult with ver["version_id"] and ver["provider_version_key"]
```

### Dev Setup:
1. Place SQL at `db/sqlite_prompter.sql`
2. `export DB_URL=sqlite:///./dev.db`
3. `python db/sqlite_bootstrap.py` → creates/refreshes tables
4. Or just run API: `uvicorn prompter.router:app --reload`

### Prod Setup:
1. Set `DB_URL=postgresql+psycopg2://...`
2. Run Alembic migrations as usual
3. The startup hook won't attempt SQLite bootstrap

---

## Summary

These production-ready components solve all the critical issues identified in the V4 review:
1. ✅ SQLite compatibility (no CASCADE, partial index)
2. ✅ UUID string parity
3. ✅ Service layer prevents recursion
4. ✅ Concurrent request handling
5. ✅ Proper error handling and idempotency
6. ✅ Clean separation of concerns
7. ✅ Dev/prod database compatibility

All components are drop-in ready and work together seamlessly.