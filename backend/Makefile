.PHONY: help dev-db migrate rollback test clean install run

help:
	@echo "Available commands:"
	@echo "  make dev-db     - Set up Neon dev database (run migrations)"
	@echo "  make migrate    - Create a new migration"
	@echo "  make rollback   - Rollback last migration"
	@echo "  make test       - Run tests against Neon"
	@echo "  make clean      - Clean up cache files"
	@echo "  make install    - Install dependencies"
	@echo "  make run        - Run the backend server"

# Database commands
dev-db:
	@echo "Using Neon dev branch via DATABASE_URL; no local Postgres/SQLite needed"
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "ERROR: DATABASE_URL not set. Source .env.development first:"; \
		echo "  export $$(grep -v '^#' .env.development | xargs)"; \
		exit 1; \
	fi
	alembic upgrade head
	@echo "Database is ready!"

migrate:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

rollback:
	alembic downgrade -1

# Test commands
test:
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "ERROR: DATABASE_URL not set. Source .env.development first"; \
		exit 1; \
	fi
	pytest tests/ -v

test-integration:
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "ERROR: DATABASE_URL not set. Source .env.development first"; \
		exit 1; \
	fi
	pytest tests/ -v -m integration

# Development commands
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

run:
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "ERROR: DATABASE_URL not set. Source .env.development first"; \
		exit 1; \
	fi
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	rm -rf .pytest_cache/

# Environment setup helper
env:
	@echo "To set up your environment, run:"
	@echo "  export \$$(grep -v '^#' .env.development | xargs)"