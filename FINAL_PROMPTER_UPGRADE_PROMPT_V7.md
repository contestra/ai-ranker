# FINAL_PROMPTER_UPGRADE_PROMPT_V7.md

**Scope:** Replace V6 with this corrected, production‑ready spec for **Prompt De‑dup + Provider‑Versioned Runs** with **multi‑brand support**. All diffs from V6 are applied (endpoint paths flattened, SQLite handling, request models, fingerprint logic, idempotency seam, async/sync safety).

---

## Role & Stack

**Role:** Senior platform engineer implementing prompt template de‑duplication and versioned runs.

**Stack:** FastAPI (Pydantic v2), SQLAlchemy 2.x, Alembic; **PostgreSQL (prod)** / **SQLite (dev)**; Celery (Upstash Redis); LangChain + LangSmith; Fly.io.

**Do‑not‑touch:** `backend/app/services/als/*` (and system prompts), shared tables (`brands`, `countries`, `entity_mentions`, `entity_strength`). Only add Prompter‑specific code.

---

## Objectives (authoritative)

1) **Block duplicate templates per brand** with active‑only uniqueness on `(org_id, workspace_id, config_hash)`.
2) **Version runs by provider version key** (OpenAI `system_fingerprint`; Gemini `modelVersion`/`Model.version`; Anthropic = model id).
3) **Audit trail:** persist full **request/response JSON** + provider key for every result.
4) **Aliases plug‑and‑play:** **aliases are out of the config hash**; per‑run `analysis_config` snapshot is allowed.
5) **Prod/dev parity:** UUID strings everywhere (Postgres UUID / SQLite TEXT), identical hashing; safe SQLite JSON handling.
6) **Routing hygiene:** no route→route calls; use a shared **service** to upsert provider versions.
7) **Idempotency seam:** Optional Redis `SET NX PX` guard for probes to avoid thundering herds.

---

## Canonical Template Identity (config hash)

Hash a **canonical JSON** for generation config only (aliases excluded):

- `system_instructions` — normalize: **preserve newlines**, collapse spaces/tabs, normalize EOLs.
- `user_prompt_template` — same normalization; keep placeholders (`{{brand}}` etc.).
- `country_set` — ISO‑3166 alpha‑2, uppercase, de‑dup, **sorted** (`UK→GB`).
- `model_id` — e.g., `gpt-4o`, `omni-moderate`, `gemini-2.5-pro`, `claude-3.7-sonnet-20250219`.
- `inference_params` — recursively **round floats to 4 dp**; **deep‑sort** dict keys.
- `tools_spec` — **preserve list order**; deep‑sort items.
- `response_format` — deep‑sorted.
- `grounding_profile_id`, `grounding_snapshot_id`.
- `retrieval_params` — deep‑sorted.
- (optional) `preprocess_pipeline_id`, `postprocess_pipeline_id`.

Compute `sha256` over compact JSON (`separators=(',',':')`); **store hash and the canonical JSON** (`config_canonical_json`).

**Provider version key:**  
- OpenAI → `system_fingerprint` (from response metadata).  
- Gemini → `modelVersion` (fallback to `model`/`model_name`).  
- Anthropic → **model id** string.

---

## Utilities (drop‑in)

```python
# utils_prompting.py
from __future__ import annotations
import json, re, hashlib
from typing import Any, Dict, List, Optional, Tuple

_WS_RE = re.compile(r"[ \t]+")
UK_SYNONYMS = {"UK":"GB", "UKK":"GB"}

def normalize_text(s: Optional[str]) -> str:
    s = (s or "").replace("\r\n","\n").replace("\r","\n")
    return _WS_RE.sub(" ", s).strip()

def normalize_countries(codes: Optional[List[str]]) -> List[str]:
    out = []
    for c in (codes or []):
        cc = (c or "").strip().upper()
        cc = UK_SYNONYMS.get(cc, cc)
        if cc: out.append(cc)
    return sorted(set(out))

def round_floats(obj: Any) -> Any:
    if isinstance(obj, float): return float(f"{obj:.4f}")
    if isinstance(obj, list):  return [round_floats(x) for x in obj]
    if isinstance(obj, dict):  return {k: round_floats(v) for k,v in obj.items()}
    return obj

def deep_sort(obj: Any) -> Any:
    if isinstance(obj, dict): return {k: deep_sort(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list): return [deep_sort(x) for x in obj]   # preserve order
    return obj

def calc_config_hash(
    *, system_instructions: Optional[str], user_prompt_template: str,
    country_set: Optional[List[str]], model_id: str,
    inference_params: Dict[str, Any] | None, tools_spec: List[Dict[str, Any]] | None,
    response_format: Dict[str, Any] | None,
    grounding_profile_id: Optional[str], grounding_snapshot_id: Optional[str],
    retrieval_params: Dict[str, Any] | None,
    preprocess_pipeline_id: Optional[str] = None,
    postprocess_pipeline_id: Optional[str] = None,
) -> tuple[str, Dict[str, Any]]:
    canonical = {
        "system_instructions": normalize_text(system_instructions),
        "user_prompt_template": normalize_text(user_prompt_template),
        "country_set": normalize_countries(country_set),
        "model_id": model_id,
        "inference_params": deep_sort(round_floats(inference_params or {})),
        "tools_spec": [deep_sort(t or {}) for t in (tools_spec or [])],
        "response_format": deep_sort(response_format or {}),
        "grounding_profile_id": grounding_profile_id,
        "grounding_snapshot_id": grounding_snapshot_id,
        "retrieval_params": deep_sort(retrieval_params or {}),
        "preprocess_pipeline_id": preprocess_pipeline_id,
        "postprocess_pipeline_id": postprocess_pipeline_id,
    }
    payload = json.dumps(canonical, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest(), canonical

def infer_provider(model_id: str) -> str:
    m = (model_id or "").lower()
    if m.startswith(("gpt","o3","o4","omni")) or "turbo" in m or "chatgpt" in m:
        return "openai"
    if "gemini" in m or "google" in m:
        return "google"
    if "claude" in m or "anthropic" in m:
        return "anthropic"
    if "azure" in m:
        return "azure-openai"
    return "unknown"

def extract_fingerprint(response: Dict[str, Any], *, provider: Optional[str]=None,
                        model_id: Optional[str]=None) -> tuple[Optional[str], str]:
    meta = response.get("response_metadata") or response.get("metadata") or {}
    sys_fp = meta.get("system_fingerprint")
    model_ver = meta.get("modelVersion") or meta.get("model") or meta.get("model_name")
    if provider == "anthropic" and model_id:
        return None, model_id
    provider_version_key = model_ver or sys_fp or "unknown"
    return sys_fp, provider_version_key

def as_dict_maybe(v):
    return v if isinstance(v, dict) else json.loads(v)

def is_sqlite(db) -> bool:
    return (getattr(db.bind, "dialect", None) is not None) and (db.bind.dialect.name == "sqlite")
```

---

## Database Schema

### PostgreSQL (production target schema; use Alembic)

```sql
-- Templates (brand-scoped; active-only dedup lives here)
CREATE TABLE IF NOT EXISTS prompt_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL,
  workspace_id UUID NOT NULL,
  name TEXT NOT NULL,
  provider TEXT, -- optional, do NOT include in hash
  system_instructions TEXT,
  user_prompt_template TEXT NOT NULL,
  country_set JSONB NOT NULL,
  model_id TEXT NOT NULL,
  inference_params JSONB NOT NULL,
  tools_spec JSONB,
  response_format JSONB,
  grounding_profile_id UUID,
  grounding_snapshot_id TEXT,
  retrieval_params JSONB,
  config_hash TEXT NOT NULL,
  config_canonical_json JSONB NOT NULL,
  created_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_tpl_org_ws_confighash_active
  ON prompt_templates (org_id, workspace_id, config_hash)
  WHERE deleted_at IS NULL;

-- Versions (provider-keyed; per template & brand)
CREATE TABLE IF NOT EXISTS prompt_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL,
  workspace_id UUID NOT NULL,
  template_id UUID NOT NULL REFERENCES prompt_templates(id),
  provider TEXT NOT NULL,
  provider_version_key TEXT NOT NULL,
  model_id TEXT NOT NULL,
  fingerprint_captured_at TIMESTAMPTZ,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (org_id, workspace_id, template_id, provider_version_key)
);

-- Results (audit trail + future alias analysis)
CREATE TABLE IF NOT EXISTS prompt_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL,
  workspace_id UUID NOT NULL,
  template_id UUID NOT NULL REFERENCES prompt_templates(id),
  version_id UUID REFERENCES prompt_versions(id),
  provider_version_key TEXT,
  system_fingerprint TEXT,
  request JSONB NOT NULL,
  response JSONB NOT NULL,
  analysis_config JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_results_tpl_time
  ON prompt_results (template_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_results_workspace
  ON prompt_results (workspace_id, created_at DESC);
```

### SQLite (dev only; idempotent; UUID strings)

```sql
-- No CASCADE; idempotent indexes
DROP TABLE IF EXISTS prompt_results;
DROP TABLE IF EXISTS prompt_versions;
DROP TABLE IF EXISTS prompt_templates;

CREATE TABLE prompt_templates (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  workspace_id TEXT NOT NULL,
  name TEXT NOT NULL,
  provider TEXT,
  system_instructions TEXT,
  user_prompt_template TEXT NOT NULL,
  country_set TEXT NOT NULL,          -- JSON string
  model_id TEXT NOT NULL,
  inference_params TEXT NOT NULL,     -- JSON string
  tools_spec TEXT,                    -- JSON string
  response_format TEXT,               -- JSON string
  grounding_profile_id TEXT,
  grounding_snapshot_id TEXT,
  retrieval_params TEXT,              -- JSON string
  config_hash TEXT NOT NULL,
  config_canonical_json TEXT NOT NULL,-- JSON string
  created_by TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  deleted_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_tpl_org_ws_confighash_active
  ON prompt_templates (org_id, workspace_id, config_hash)
  WHERE deleted_at IS NULL;

CREATE TABLE prompt_versions (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  workspace_id TEXT NOT NULL,
  template_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  provider_version_key TEXT NOT NULL,
  model_id TEXT NOT NULL,
  fingerprint_captured_at TEXT,
  first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (org_id, workspace_id, template_id, provider_version_key),
  FOREIGN KEY (template_id) REFERENCES prompt_templates(id)
);

CREATE TABLE prompt_results (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  workspace_id TEXT NOT NULL,
  template_id TEXT NOT NULL,
  version_id TEXT,
  provider_version_key TEXT,
  system_fingerprint TEXT,
  request TEXT NOT NULL,              -- JSON string
  response TEXT NOT NULL,             -- JSON string
  analysis_config TEXT,               -- JSON string
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (template_id) REFERENCES prompt_templates(id),
  FOREIGN KEY (version_id) REFERENCES prompt_versions(id)
);

CREATE INDEX IF NOT EXISTS ix_results_tpl_time
  ON prompt_results (template_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_results_workspace
  ON prompt_results (workspace_id, created_at DESC);
```

---

## API (flattened paths)

Router prefix: **`/api/prompt-templates`**

- **POST `/`** — create template (dedup by brand).
- **POST `/check-duplicate`** — typing‑time exact‑match check.
- **POST `/{template_id}/ensure-version`** — capture/UPSERT provider version key.
- **POST `/{template_id}/run`** — execute one run and persist result (example only; your app may use callbacks).

### Request Models (add to your router/module)

```python
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class CreateTemplateRequest(BaseModel):
    org_id: Optional[str] = None
    workspace_id: str
    name: str
    provider: Optional[str] = None      # optional; not part of hash
    system_instructions: Optional[str] = None
    user_prompt_template: str
    country_set: List[str] = Field(default_factory=list)
    model_id: str
    inference_params: Any = Field(default_factory=dict)   # dict or Pydantic
    tools_spec: List[Dict[str, Any]] = Field(default_factory=list)
    response_format: Optional[Dict[str, Any]] = None
    grounding_profile_id: Optional[str] = None
    grounding_snapshot_id: Optional[str] = None
    retrieval_params: Optional[Dict[str, Any]] = None
    created_by: Optional[str] = None

class RunTemplateRequest(BaseModel):
    rendered_prompt: str
    brand_name: Optional[str] = None
    country: Optional[str] = None
    analysis_scope: Optional[str] = "brand"
    runtime_vars: Dict[str, Any] = Field(default_factory=dict)
    use_grounding: bool = False
```

---

## Version Service (no route→route calls; optional Redis)

```python
# services/prompt_versions.py
from __future__ import annotations
import datetime as dt
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from prompter.models import PromptVersion
from utils_prompting import as_dict_maybe
try:
    from redis import Redis
except Exception:
    Redis = None  # type: ignore

def _probe_key(org_id, workspace_id, template_id, provider, model_id, bucket):
    return f"probe:{org_id}:{workspace_id}:{template_id}:{provider}:{model_id}:{bucket}"

def ensure_version_service(
    db: Session, *, org_id: str, workspace_id: str, template_id: str,
    provider: str, model_id: str,
    system_instructions: Optional[str] = None,
    inference_params: Optional[Dict[str, Any]] = None,
    probe_func=None, redis: Optional["Redis"] = None, ttl_sec:int = 3600,
) -> Dict[str, Any]:
    from services.provider_probe import probe_provider_version as default_probe
    probe = probe_func or default_probe
    if redis is not None:
        bucket = dt.datetime.utcnow().strftime("%Y%m%d%H")
        redis.set(_probe_key(org_id, workspace_id, template_id, provider, model_id, bucket), "1", nx=True, ex=ttl_sec)

    provider_version_key, captured_at = probe(
        provider=provider, model_id=model_id,
        system_instructions=system_instructions, inference_params=inference_params or {}
    )

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
        winner = db.execute(
            select(PromptVersion).where(
                PromptVersion.org_id == org_id,
                PromptVersion.workspace_id == workspace_id,
                PromptVersion.template_id == template_id,
                PromptVersion.provider_version_key == provider_version_key,
            )
        ).scalars().first()
        if not winner: raise
        winner.last_seen_at = max(winner.last_seen_at or captured_at, captured_at)
        if not winner.fingerprint_captured_at:
            winner.fingerprint_captured_at = captured_at
        db.commit()
        return {"version_id": winner.id, "provider_version_key": provider_version_key, "captured_at": captured_at}
```

---

## Router patches (essentials only)

- **Flattened paths**: `@router.post("")`, `@router.post("/check-duplicate")`, `@router.post("/{template_id}/ensure-version")`, `@router.post("/{template_id}/run")`.
- **SQLite JSON**: if `is_sqlite(db)` then `json.dumps(...)` when writing JSON columns; else pass dicts/lists.
- **`inference_params` tolerant**: accept dict or Pydantic (`.dict()` if available).
- **Result consistency**: set `provider_version_key` from response **or** fallback to service key.
- **Async/sync safety**: `inspect.isawaitable(resp)` around adapter calls.

Example snippets:

```python
# create_template: before hashing
params_raw = req.inference_params or {}
if hasattr(params_raw, "dict"): params_raw = params_raw.dict()

config_hash, canonical = calc_config_hash(
    system_instructions=req.system_instructions,
    user_prompt_template=req.user_prompt_template,
    country_set=req.country_set,
    model_id=req.model_id,
    inference_params=params_raw,
    tools_spec=req.tools_spec,
    response_format=req.response_format,
    grounding_profile_id=req.grounding_profile_id,
    grounding_snapshot_id=req.grounding_snapshot_id,
    retrieval_params=req.retrieval_params,
)
```

```python
# run_template: after model call (response is a dict with response_metadata)
from utils_prompting import extract_fingerprint, infer_provider

prov = req.provider or template.provider or infer_provider(template.model_id)
sys_fp, pvk_from_resp = extract_fingerprint(response, provider=prov, model_id=template.model_id)

ver = ensure_version_service(
    db, org_id=template.org_id, workspace_id=template.workspace_id, template_id=template.id,
    provider=prov, model_id=template.model_id,
    system_instructions=canonical.get("system_instructions"),
    inference_params=canonical.get("inference_params", {}),
    redis=redis_client  # optional
)

provider_version_key = pvk_from_resp or ver["provider_version_key"]
if provider_version_key == "unknown":
    provider_version_key = ver["provider_version_key"]
```

```python
# async/sync safety around adapters
import inspect
resp = adapter.analyze_with_gpt4(req.rendered_prompt, model_name=template.model_id, **params_used)
response = await resp if inspect.isawaitable(resp) else resp
```

---

## Testing (additive)

- **Hash stability:** whitespace and country order don’t change `config_hash`.
- **Dedup:** same `(org, workspace, config_hash)` ⇒ second create returns **409**; different workspace ⇒ **201**.
- **Versioning:** two concurrent ensure‑version calls ⇒ one row per provider key.
- **SQLite ↔ Postgres parity:** identical inputs ⇒ identical `config_hash`.
- **Result consistency:** `provider_version_key` on result equals the version row’s key even when the response shows `"unknown"` (Anthropic/Azure cases).

---

## Definition of Done

- Active‑only dedup on `(org_id, workspace_id, config_hash)` in both Postgres (partial index) and SQLite (partial index or app‑level guard).
- A **new prompt_version** row is created **only** when the provider version key changes.
- Each result stores **full request/response JSON**, `version_id`, and provider key; OpenAI runs include `system_fingerprint`.
- SQLite dev and Postgres prod have identical behavior for hashing and ID handling.
- Ensure‑version logic lives in a **service**; routes do not call routes.
- Optional Redis idempotency reduces redundant probes.
