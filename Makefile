
# Makefile — Prompter V7 local dev helpers
#
# Usage:
#   make help
#   make venv install run
#   make test
#   make migrate  (Postgres via Alembic)
#   make sqlite-reset  (dev DB schema)
#
# Variables you can override:
#   PYTHON?=.venv/bin/python
#   PIP?=.venv/bin/pip
#   UVICORN?=.venv/bin/uvicorn
#   PYTEST?=.venv/bin/pytest
#   ALEMBIC?=.venv/bin/alembic
#   DB_URL?=sqlite:///./dev.db
#   TEST_PG_DSN?=postgresql+psycopg2://user:pass@localhost:5432/yourdb

SHELL := /bin/bash
PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
UVICORN ?= .venv/bin/uvicorn
PYTEST ?= .venv/bin/pytest
ALEMBIC ?= .venv/bin/alembic

DB_URL ?= sqlite:///./dev.db
TEST_PG_DSN ?=

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS=":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

.PHONY: venv
venv: ## Create Python virtualenv at .venv
	@test -d .venv || python3 -m venv .venv
	@echo "✅ venv ready"

.PHONY: install
install: venv ## Install dev requirements
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	@echo "✅ dependencies installed"

.PHONY: run
run: ## Start FastAPI locally (SQLite). Edit DB_URL to point to Postgres if desired
	@DB_URL="$(DB_URL)" CREATE_ALL_ON_STARTUP=true METRICS_ENV=dev METRICS_SERVICE=prompter-api \
	$(UVICORN) prompter_router_min:app --reload --port 8000

.PHONY: test
test: ## Run all pytest tests
	@DB_URL="$(DB_URL)" CREATE_ALL_ON_STARTUP=true \
	$(PYTEST) -q

.PHONY: test-sqlite
test-sqlite: ## Run only SQLite parity tests
	@DB_URL="sqlite:///./test_sqlite_v7.db" CREATE_ALL_ON_STARTUP=true \
	$(PYTEST) -q tests/test_sqlite_v7_parity.py

.PHONY: test-pg
test-pg: ## Run Alembic roundtrip test against Postgres (set TEST_PG_DSN env)
	@if [ -z "$(TEST_PG_DSN)" ]; then echo "ERROR: set TEST_PG_DSN to run Postgres tests"; exit 1; fi
	@DATABASE_URL="$(TEST_PG_DSN)" TEST_PG_DSN="$(TEST_PG_DSN)" \
	$(PYTEST) -q tests/test_alembic_v7_migration.py

.PHONY: migrate
migrate: ## Alembic upgrade head (Postgres)
	@if [ -z "$(TEST_PG_DSN)" ]; then echo "ERROR: set TEST_PG_DSN to run migrations"; exit 1; fi
	@$(ALEMBIC) -x DB_URL="$(TEST_PG_DSN)" upgrade head

.PHONY: downgrade
downgrade: ## Alembic downgrade by one revision (Postgres)
	@if [ -z "$(TEST_PG_DSN)" ]; then echo "ERROR: set TEST_PG_DSN to run migrations"; exit 1; fi
	@$(ALEMBIC) -x DB_URL="$(TEST_PG_DSN)" downgrade -1

.PHONY: sqlite-reset
sqlite-reset: ## Reset dev SQLite schema to V7 (DROPs existing tables)
	@DB_URL="$(DB_URL)" $(PYTHON) db/apply_sqlite_v7.py

.PHONY: fmt
fmt: dev-tools ## Format with ruff (format) + isort fallback
	@.venv/bin/ruff format || true
	@.venv/bin/isort . || true

.PHONY: lint
lint: dev-tools ## Lint with ruff
	@.venv/bin/ruff check . || true

.PHONY: typecheck
typecheck: dev-tools ## Type-check (mypy)
	@.venv/bin/mypy prompter_router_min.py prompter/ services/ || true

.PHONY: dev-tools
dev-tools: venv ## Install optional developer tools (ruff, mypy, isort, black)
	$(PIP) install ruff mypy isort black

.PHONY: metrics
metrics: ## Curl the /metrics endpoint
	@curl -sS localhost:8000/metrics | head -n 20

.PHONY: clean
clean: ## Remove caches and dev DB
	@rm -rf .pytest_cache .ruff_cache **/__pycache__ *.db dev.db test_sqlite_v7.db || true
	@find . -name "__pycache__" -type d -exec rm -rf {} +
	@echo "🧹 cleaned"
