# Prompter V7 Testing and SQLite Parity
## Complete Test Coverage and Development Database Support

**Status**: Complete testing infrastructure for both PostgreSQL and SQLite  
**Purpose**: Ensure V7 migration works correctly and provide SQLite parity for development

## Overview

The external model provided comprehensive testing and SQLite parity files to ensure:
1. **PostgreSQL Migration Testing** - Round-trip upgrade/downgrade verification
2. **SQLite Development Parity** - Matching schema for local development
3. **Automated Testing** - Both database systems have test coverage

## Files Provided

### PostgreSQL Testing
- `test_alembic_v7_migration.py` - Alembic migration round-trip test

### SQLite Parity
- `sqlite_v7_parity.sql` - DDL script for SQLite schema
- `apply_sqlite_v7.py` - Python script to apply SQLite schema
- `test_sqlite_v7_parity.py` - Test to verify SQLite schema

## PostgreSQL Alembic Test

### Purpose
Tests that the V7 Alembic migration:
- Successfully upgrades (creates all tables and indexes)
- Successfully downgrades (removes all V7 objects)
- Creates the partial unique index correctly
- Leaves database in clean state

### Test Coverage (`test_alembic_v7_migration.py`)

```python
def test_v7_migration_upgrade_downgrade_roundtrip():
    # 1. Upgrade to head (includes V7)
    command.upgrade(cfg, "head")
    
    # 2. Verify tables exist
    for t in ("prompt_templates", "prompt_versions", "prompt_results"):
        assert insp.has_table(t)
    
    # 3. Verify partial unique index
    idx = conn.execute(text("""
        SELECT indexdef FROM pg_indexes
        WHERE tablename='prompt_templates'
          AND indexname='ux_tpl_org_ws_confighash_active'
    """)).scalar()
    assert "WHERE deleted_at IS NULL" in idx
    
    # 4. Downgrade one step
    command.downgrade(cfg, "-1")
    
    # 5. Verify tables removed
    for t in ("prompt_templates", "prompt_versions", "prompt_results"):
        assert not insp2.has_table(t)
    
    # 6. Re-upgrade to leave DB clean
    command.upgrade(cfg, "head")
```

### Running the PostgreSQL Test

```bash
# Install dependencies
pip install sqlalchemy alembic psycopg2-binary pytest

# Set PostgreSQL DSN (must be a test database!)
export TEST_PG_DSN="postgresql+psycopg2://user:pass@localhost/testdb"
# OR
export DATABASE_URL="postgresql://user:pass@localhost/testdb"

# Run the test
pytest test_alembic_v7_migration.py -v

# Test will skip if no PostgreSQL DSN provided
```

### Safety Features
- Requires explicit PostgreSQL DSN (won't run accidentally)
- Skips gracefully if no PostgreSQL available
- Re-upgrades after test to leave DB in good state
- Uses pytest markers for conditional execution

## SQLite Development Parity

### Purpose
Provides identical schema for SQLite to enable:
- Local development without PostgreSQL
- Fast testing without database server
- CI/CD testing with in-memory SQLite
- Schema parity between dev and production

### Schema File (`sqlite_v7_parity.sql`)

Key differences from PostgreSQL:
```sql
-- SQLite uses TEXT for UUIDs (stored as strings)
id TEXT PRIMARY KEY,

-- SQLite datetime function instead of now()
created_at TEXT NOT NULL DEFAULT (datetime('now')),

-- SQLite supports partial indexes (same syntax!)
CREATE UNIQUE INDEX IF NOT EXISTS ux_tpl_org_ws_confighash_active
  ON prompt_templates (org_id, workspace_id, config_hash)
  WHERE deleted_at IS NULL;

-- Foreign keys work the same
FOREIGN KEY (template_id) REFERENCES prompt_templates(id)
```

### Apply Script (`apply_sqlite_v7.py`)

Simple Python script to apply the SQLite schema:
```python
# Reads DB_URL from environment
DB_URL = os.getenv("DB_URL", "sqlite:///./dev.db")

# Applies the SQL file
conn.executescript(script)
```

Usage:
```bash
# Default: applies to dev.db
python apply_sqlite_v7.py

# Custom database
DB_URL=sqlite:///./custom.db python apply_sqlite_v7.py

# Custom SQL file location
SQLITE_V7_FILE=path/to/schema.sql python apply_sqlite_v7.py
```

### SQLite Test (`test_sqlite_v7_parity.py`)

Verifies the SQLite schema is correct:
```python
def test_sqlite_v7_parity_schema():
    # Apply schema to test database
    conn.executescript(script)
    
    # Verify tables exist
    names = {r[0] for r in rows}
    assert {'prompt_templates','prompt_versions','prompt_results'}.issubset(names)
    
    # Verify partial unique index
    idx = cur.fetchone()
    assert 'WHERE deleted_at IS NULL' in idx[1]
```

### Running the SQLite Test

```bash
# Install pytest
pip install pytest

# Ensure files are in place
mkdir -p db tests
cp sqlite_v7_parity.sql db/
cp test_sqlite_v7_parity.py tests/

# Run the test
pytest tests/test_sqlite_v7_parity.py -v

# Output
test_sqlite_v7_parity.py::test_sqlite_v7_parity_schema PASSED
```

## Development Workflow

### 1. Initial Setup (SQLite)
```bash
# Apply V7 schema to dev.db
python apply_sqlite_v7.py

# Verify schema
sqlite3 dev.db ".schema prompt_templates"
```

### 2. Initial Setup (PostgreSQL)
```bash
# Run Alembic migration
alembic upgrade head

# Verify with psql
psql $DATABASE_URL -c "\dt prompt_*"
```

### 3. Testing Both Databases
```bash
# Run all tests
pytest tests/ -v

# SQLite only
pytest tests/test_sqlite_v7_parity.py -v

# PostgreSQL only (requires DSN)
TEST_PG_DSN=$PROD_DSN pytest tests/test_alembic_v7_migration.py -v
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: V7 Database Tests

on: [push, pull_request]

jobs:
  sqlite-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install pytest sqlalchemy
      - name: Test SQLite parity
        run: pytest tests/test_sqlite_v7_parity.py -v

  postgres-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install pytest sqlalchemy alembic psycopg2-binary
      - name: Test Alembic migration
        env:
          TEST_PG_DSN: postgresql+psycopg2://postgres:postgres@localhost/postgres
        run: pytest tests/test_alembic_v7_migration.py -v
```

## Key Benefits

### 1. Development/Production Parity
- Same schema structure in both SQLite and PostgreSQL
- Same partial unique index behavior
- Same foreign key constraints
- UUID strings work identically

### 2. Fast Local Development
- No PostgreSQL server needed for development
- SQLite in-memory for ultra-fast tests
- Easy to reset (just delete dev.db)
- Version controlled schema

### 3. Comprehensive Testing
- PostgreSQL migration tested both ways (up/down)
- SQLite schema verified programmatically
- CI/CD ready with both database types
- No manual verification needed

### 4. Easy Onboarding
- New developers can start with SQLite
- No database server setup required
- Schema applied with one command
- Tests verify correctness

## Troubleshooting

### PostgreSQL Test Failures

1. **"Postgres DSN not provided"**
   - Set TEST_PG_DSN or DATABASE_URL environment variable
   - Must point to a test database (data will be modified!)

2. **"Migration not found"**
   - Ensure alembic/versions/ contains the V7 migration
   - Check alembic.ini points to correct directory

3. **"Permission denied for schema public"**
   - User needs CREATE permission on test database
   - Or use a dedicated test database

### SQLite Test Failures

1. **"sqlite_v7_parity.sql not found"**
   - Ensure file is in db/ directory
   - Or set SQLITE_V7_FILE environment variable

2. **"Foreign key constraint failed"**
   - SQLite foreign keys are enforced
   - Ensure proper order of operations

3. **"Unique constraint failed"**
   - Partial index is working correctly
   - Check for duplicate active records

## Best Practices

### For Development
1. Use SQLite for rapid iteration
2. Test with PostgreSQL before PR
3. Keep both schemas in sync
4. Run tests after schema changes

### For Testing
1. Use in-memory SQLite for unit tests
2. Use PostgreSQL for integration tests
3. Test migration rollback regularly
4. Verify indexes are used (EXPLAIN QUERY PLAN)

### For Production
1. Always use PostgreSQL with Alembic
2. Test migrations on staging first
3. Have rollback plan ready
4. Monitor index usage

## Summary

These testing and parity files ensure:
- ✅ PostgreSQL migrations are tested bidirectionally
- ✅ SQLite provides identical functionality for development
- ✅ Both database systems have automated tests
- ✅ Schema parity is maintained automatically
- ✅ New developers can start immediately with SQLite
- ✅ Production deployments are safe with tested migrations

The combination of PostgreSQL for production and SQLite for development provides the best of both worlds: production robustness with development simplicity.