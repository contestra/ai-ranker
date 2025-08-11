# AI Visibility Prompt Tracking — File Map (NONE vs WEB)

This repo contains a minimal, production‑minded scaffold for your prompt tracking system with **grounding modes = {NONE, WEB}** only. No SITE mode.

## Top‑level
- `requirements.txt` — Python dependencies.
- `CLAUDE_PROMPT.txt` — Copy‑paste prompt to instruct Claude; it specifies ONLY NONE/WEB (no SITE).
- `ARCHITECTURE.md` — This file.

## Database (Alembic)
- `alembic/versions/0001_initial.py` — Creates all tables/enums/indexes, RLS policies, and the 200‑prompt cap trigger.

## App modules
- `app/config.py` — Settings (DATABASE_URL, REDIS_URL, allowed countries, default language).
- `app/constants.py` — Enums: `RunStatus`, `GroundingMode (NONE|WEB)`, `PromptCategory`.
- `app/db.py` — SQLAlchemy engine, session factory, RLS helper.
- `app/deps.py` — FastAPI dependencies: tenant header, language validator, idempotency header access.
- `app/models.py` — ORM models matching the migration (tenants, brands, variations, prompts, prompt_countries, models, prompt_models, schedules, runs, answers).
- `app/schemas.py` — Pydantic request bodies (create/update prompt, countries upsert, model config incl. `grounding_mode`, schedules, ad‑hoc runs).

## Services
- `app/services/proxy.py` — `ProxyPool` abstraction; choose proxy per `country_code`.
- `app/services/adapters/base.py` — `ModelAdapter` interface + `ProviderResponse` shape.
- `app/services/adapters/dummy.py` — Minimal adapter returning a stubbed answer (for local dev).
- `app/services/model_registry.py` — Registry for model adapters (by `model_id`).
- `app/services/grounding.py` — **WEB retrieval stub** + `build_context` to create a numbered SOURCES block and citations for your prompt when WEB is selected.
- `app/services/prompt_compose.py` — Builds the final prompt string; if `grounding_mode=WEB`, it appends a SOURCES section and citation guidance.

## Workers
- `app/workers/queue.py` — RQ queue binding.
- `app/workers/jobs.py` — **Single job** `execute_run(payload)`:
  1. Idempotency guard in Redis.
  2. Loads prompt + brand.
  3. If `grounding_mode=WEB`, runs `retrieve_web(...)` (stub), builds context + citations.
  4. Composes prompt and calls model adapter (dummy by default).
  5. Persists `runs` + `answers` (with `grounding_mode` and `citation_count`).

## HTTP API
Routers mounted in `app/main.py`:
- `app/routers/brands.py` — Create brand, add variations, toggle canonicalization.
- `app/routers/prompts.py` — Create/edit/soft‑delete prompts; upsert countries (≤6) and models (with `grounding_mode`).
- `app/routers/schedules.py` — Create/delete schedules.
- `app/routers/runs.py` — Ad‑hoc run enqueuer; list runs; get run/answer by id.

## Scheduler
- `app/scheduler/service.py` — APScheduler loop:
  - Computes/initializes `next_run_at` in tenant timezone.
  - Selects due schedules with `FOR UPDATE SKIP LOCKED`.
  - Expands (countries × models × grounding mode) for the prompt and enqueues jobs.
  - Advances `next_run_at` considering DST.

## Scripts
- `scripts/seed_models.py` — Seeds common frontier models with capability flags.

## Execution flow
1. Tenant creates brand + prompt(s).
2. Tenant attaches countries (≤6) and one or more models **with per‑model `grounding_mode` (NONE|WEB)**.
3. Scheduler (or ad‑hoc) enqueues runs across the cartesian product.
4. Worker fetches (WEB retrieval if enabled) → composes prompt → calls model → persists `runs` + `answers` including citations.
5. UI queries `/runs` and `/runs/{id}` to display answers + badges (`Ungrounded` vs `Web‑grounded`).

Replace the dummy adapter with real provider adapters and implement `retrieve_web(...)` using your search stack (and proxies) if you choose not to rely on provider-native browsing.
