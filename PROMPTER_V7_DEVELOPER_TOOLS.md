# Prompter V7 Developer Tools
## Makefile and Development Workflow Automation

**File**: `Makefile`  
**Status**: Complete development automation  
**Purpose**: Streamline daily development tasks with simple commands

## Overview

The external model has provided a comprehensive Makefile that automates all common development tasks. This final enhancement makes the V7 solution not just complete, but also **developer-friendly** with convenient shortcuts for every task.

## Quick Start Commands

### Essential Workflow
```bash
make venv        # Create virtual environment
make install     # Install all dependencies
make run         # Start the API server
make test        # Run all tests
```

### That's it! Your complete workflow in 4 commands.

## Complete Command Reference

### 🚀 Core Commands

#### `make run`
Starts the FastAPI server with hot reload
```bash
make run
# Server running at http://localhost:8000
# Metrics at http://localhost:8000/metrics
```

#### `make test`
Runs the complete test suite
```bash
make test
# Runs all tests including fingerprint validation
```

#### `make help`
Shows all available commands
```bash
make help
# Displays formatted help for all targets
```

### 🗄️ Database Commands

#### `make sqlite-reset`
Resets SQLite database to V7 schema
```bash
make sqlite-reset
# Drops existing tables and creates fresh V7 schema
```

#### `make migrate`
Runs Alembic migrations (PostgreSQL)
```bash
TEST_PG_DSN=postgresql://user:pass@localhost/db make migrate
```

#### `make test-pg`
Tests PostgreSQL migration roundtrip
```bash
TEST_PG_DSN=postgresql://user:pass@localhost/db make test-pg
```

### 🧪 Testing Commands

#### `make test-sqlite`
Tests SQLite schema parity
```bash
make test-sqlite
```

#### `make metrics`
Quick check of Prometheus metrics
```bash
make metrics
# Shows first 20 lines of /metrics output
```

### 🛠️ Development Tools

#### `make dev-tools`
Installs optional development tools
```bash
make dev-tools
# Installs: ruff, mypy, isort, black
```

#### `make fmt`
Formats code with ruff and isort
```bash
make fmt
# Auto-formats all Python files
```

#### `make lint`
Lints code with ruff
```bash
make lint
# Shows linting issues
```

#### `make typecheck`
Type-checks with mypy
```bash
make typecheck
# Checks type annotations
```

### 🧹 Maintenance

#### `make clean`
Removes caches and temporary files
```bash
make clean
# Removes: __pycache__, .pytest_cache, *.db files
```

## Advanced Usage

### Override Variables
```bash
# Use PostgreSQL instead of SQLite
make run DB_URL=postgresql://user:pass@localhost/prompter

# Run tests against PostgreSQL
make test DB_URL=postgresql://user:pass@localhost/test_db

# Change port
make run UVICORN_PORT=3000
```

### Environment Variables
The Makefile respects these environment variables:
- `DB_URL` - Database connection string
- `TEST_PG_DSN` - PostgreSQL DSN for testing
- `METRICS_ENV` - Environment label for metrics
- `METRICS_SERVICE` - Service name for metrics

## Typical Development Workflow

### First Time Setup
```bash
git clone <repo>
cd ai-ranker
make venv install
make sqlite-reset
make run
# Visit http://localhost:8000
```

### Daily Development
```bash
# Start your day
make run

# In another terminal, run tests
make test

# Format your code
make fmt

# Check metrics
make metrics
```

### Before Committing
```bash
make fmt         # Format code
make lint        # Check for issues
make test        # Run all tests
git add -A
git commit -m "Your changes"
```

## Benefits of the Makefile

### 1. Consistency
- Same commands work for everyone
- No need to remember complex commands
- Standardized development workflow

### 2. Convenience
- Short, memorable commands
- Sensible defaults
- Easy overrides when needed

### 3. Documentation
- Commands are self-documenting
- `make help` shows everything
- Comments explain each target

### 4. Cross-Platform
- Works on Linux, macOS, WSL
- Uses standard Make syntax
- No special dependencies

## Integration with V7 Solution

The Makefile perfectly complements the V7 solution:

1. **Quick Start**: `make venv install run` gets you running
2. **Testing**: `make test` validates everything works
3. **Development**: `make fmt lint` keeps code clean
4. **Production**: `make migrate` handles database setup
5. **Monitoring**: `make metrics` checks observability

## Complete Developer Experience

With this Makefile, the V7 solution now has:
- ✅ **One-command setup** - `make install`
- ✅ **One-command run** - `make run`
- ✅ **One-command test** - `make test`
- ✅ **Code quality tools** - `make fmt lint`
- ✅ **Database management** - `make sqlite-reset migrate`
- ✅ **Clean workflow** - `make clean`

## Example Session

```bash
# Fresh clone
$ git clone <repo>
$ cd ai-ranker

# Setup
$ make venv install
✅ venv ready
✅ dependencies installed

# Reset database
$ make sqlite-reset
Applied db/sqlite_v7_parity.sql to ./dev.db

# Run server
$ make run
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete

# Test it (new terminal)
$ make test
====== 6 passed in 0.45s ======

# Check metrics
$ make metrics
# HELP starlette_requests_total Total HTTP requests
# TYPE starlette_requests_total counter
starlette_requests_total{env="dev",method="GET",...} 1.0

# Format code
$ make fmt
✅ formatted

# Clean up
$ make clean
🧹 cleaned
```

## Summary

The Makefile provides:
- ✅ **Streamlined workflow** for daily development
- ✅ **Simple commands** that are easy to remember
- ✅ **Flexible configuration** with overrides
- ✅ **Complete tooling** for code quality
- ✅ **Database management** for both SQLite and PostgreSQL
- ✅ **Self-documentation** with help command

This final addition makes the V7 solution not just complete and production-ready, but also **a joy to develop with**. Every common task is now just a `make` command away!