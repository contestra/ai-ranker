# Prompter V7 Alembic Migration
## PostgreSQL Database Migration for Production

**File**: `v7_prompt_upgrade_20250814141329.py`  
**Purpose**: Creates all V7 tables with proper PostgreSQL types and indexes  
**Status**: Ready for integration with your Alembic setup

## Overview

This Alembic migration creates the complete V7 schema for PostgreSQL with:
- Full UUID support using `gen_random_uuid()`
- JSONB columns for efficient JSON storage and querying
- Partial unique index for active-only deduplication
- Optimized secondary indexes for performance

## Database Schema

### 1. prompt_templates Table
```sql
- id: UUID (auto-generated)
- org_id: UUID (required)
- workspace_id: UUID (required) 
- name: TEXT (required)
- provider: TEXT (optional)
- system_instructions: TEXT
- user_prompt_template: TEXT (required)
- country_set: JSONB (required)
- model_id: TEXT (required)
- inference_params: JSONB (required)
- tools_spec: JSONB
- response_format: JSONB
- grounding_profile_id: UUID
- grounding_snapshot_id: TEXT
- retrieval_params: JSONB
- config_hash: TEXT (required)
- config_canonical_json: JSONB (required)
- created_by: UUID
- created_at: TIMESTAMPTZ (auto-set)
- deleted_at: TIMESTAMPTZ (soft delete)
```

**Unique Index**: `ux_tpl_org_ws_confighash_active`
- Columns: `(org_id, workspace_id, config_hash)`
- Condition: `WHERE deleted_at IS NULL`
- Ensures no duplicate active templates per workspace

### 2. prompt_versions Table
```sql
- id: UUID (auto-generated)
- org_id: UUID (required)
- workspace_id: UUID (required)
- template_id: UUID (FK -> prompt_templates.id)
- provider: TEXT (required)
- provider_version_key: TEXT (required)
- model_id: TEXT (required)
- fingerprint_captured_at: TIMESTAMPTZ
- first_seen_at: TIMESTAMPTZ (auto-set)
- last_seen_at: TIMESTAMPTZ (auto-set)
```

**Unique Constraint**: `ux_versions_org_ws_tpl_pvk`
- Columns: `(org_id, workspace_id, template_id, provider_version_key)`
- Enables UPSERT operations for version tracking

### 3. prompt_results Table
```sql
- id: UUID (auto-generated)
- org_id: UUID (required)
- workspace_id: UUID (required)
- template_id: UUID (FK -> prompt_templates.id)
- version_id: UUID (FK -> prompt_versions.id)
- provider_version_key: TEXT
- system_fingerprint: TEXT
- request: JSONB (required)
- response: JSONB (required)
- analysis_config: JSONB
- created_at: TIMESTAMPTZ (auto-set)
```

**Indexes**:
- `ix_results_tpl_time`: `(template_id, created_at DESC)` - Fast template history
- `ix_results_workspace`: `(workspace_id, created_at DESC)` - Workspace activity

## Integration Instructions

### 1. Copy Migration File
```bash
# Copy to your Alembic versions directory
cp v7_prompt_upgrade_20250814141329.py alembic/versions/
```

### 2. Update Migration Header
Edit the file and set your previous migration ID:
```python
# Line 24 - Replace with your actual previous revision
down_revision = "your_previous_migration_id_here"
```

### 3. Review Current Migrations
```bash
# Check your current migration history
alembic history

# Get the latest revision ID
alembic current
```

### 4. Apply Migration
```bash
# Dry run to see SQL
alembic upgrade head --sql

# Apply the migration
alembic upgrade head
```

### 5. Verify Migration
```sql
-- Check tables were created
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('prompt_templates', 'prompt_versions', 'prompt_results');

-- Check partial index
SELECT indexname, indexdef FROM pg_indexes 
WHERE tablename = 'prompt_templates' 
AND indexname = 'ux_tpl_org_ws_confighash_active';

-- Verify pgcrypto extension
SELECT * FROM pg_extension WHERE extname = 'pgcrypto';
```

## Rollback Instructions

If needed, rollback is clean and complete:
```bash
# Rollback one revision
alembic downgrade -1

# Or rollback to specific revision
alembic downgrade your_previous_migration_id
```

The downgrade:
1. Drops all indexes in dependency order
2. Drops tables in reverse order (results → versions → templates)
3. Does NOT remove pgcrypto extension (safe to leave)

## PostgreSQL-Specific Features

### 1. UUID Generation
Uses `gen_random_uuid()` from pgcrypto extension:
- Automatically generates UUIDs at database level
- More efficient than application-generated UUIDs
- Ensures uniqueness across distributed systems

### 2. JSONB vs JSON
Uses JSONB for all JSON columns:
- Binary storage format (faster)
- Supports indexing and operators
- Removes duplicate keys and whitespace
- Allows efficient queries like `WHERE inference_params @> '{"temperature": 0.7}'`

### 3. Partial Unique Index
PostgreSQL-specific feature for active-only uniqueness:
```sql
CREATE UNIQUE INDEX ... WHERE deleted_at IS NULL
```
- Only enforces uniqueness for non-deleted records
- Allows soft-deleted duplicates to exist
- Perfect for the deduplication requirement

### 4. Timezone-Aware Timestamps
Uses `TIMESTAMP WITH TIME ZONE`:
- Stores UTC internally
- Converts to client timezone on retrieval
- Prevents timezone-related bugs

## Performance Considerations

### Index Strategy
1. **Primary Keys**: UUID with B-tree index (automatic)
2. **Foreign Keys**: Indexed automatically by PostgreSQL
3. **Partial Unique**: Efficient deduplication checks
4. **Time-based**: Optimized for recent data queries
5. **Workspace Scoping**: Fast workspace-specific queries

### Query Optimization
The indexes support these common queries efficiently:
```sql
-- Find duplicate (uses partial unique index)
SELECT * FROM prompt_templates 
WHERE org_id = ? AND workspace_id = ? 
  AND config_hash = ? AND deleted_at IS NULL;

-- Template history (uses ix_results_tpl_time)
SELECT * FROM prompt_results 
WHERE template_id = ? 
ORDER BY created_at DESC LIMIT 100;

-- Workspace activity (uses ix_results_workspace)
SELECT * FROM prompt_results 
WHERE workspace_id = ? 
ORDER BY created_at DESC LIMIT 50;
```

## Testing the Migration

### Unit Test
```python
def test_migration():
    # Apply migration
    alembic.command.upgrade(config, "head")
    
    # Check tables exist
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "prompt_templates" in tables
    assert "prompt_versions" in tables
    assert "prompt_results" in tables
    
    # Check partial index
    indexes = inspector.get_indexes("prompt_templates")
    partial_idx = [i for i in indexes 
                   if i["name"] == "ux_tpl_org_ws_confighash_active"]
    assert len(partial_idx) == 1
    assert partial_idx[0]["unique"] is True
    
    # Rollback
    alembic.command.downgrade(config, "-1")
```

### Integration Test
```python
def test_deduplication():
    # Create template
    tpl1 = create_template(workspace_id="ws1", config_hash="abc123")
    
    # Try duplicate - should fail
    with pytest.raises(IntegrityError):
        tpl2 = create_template(workspace_id="ws1", config_hash="abc123")
    
    # Soft delete first
    tpl1.deleted_at = datetime.utcnow()
    session.commit()
    
    # Now duplicate should succeed
    tpl3 = create_template(workspace_id="ws1", config_hash="abc123")
    assert tpl3.id != tpl1.id
```

## Monitoring

### Migration Status
```sql
-- Check Alembic version
SELECT * FROM alembic_version;

-- Table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename IN ('prompt_templates', 'prompt_versions', 'prompt_results');

-- Index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename IN ('prompt_templates', 'prompt_versions', 'prompt_results');
```

## Troubleshooting

### Common Issues

1. **pgcrypto extension missing**
   ```sql
   -- Requires superuser or appropriate permissions
   CREATE EXTENSION IF NOT EXISTS pgcrypto;
   ```

2. **UUID type not recognized**
   - Ensure PostgreSQL version >= 9.4
   - Check psycopg2-binary is installed

3. **Migration conflicts**
   ```bash
   # Check for conflicts
   alembic branches
   
   # Resolve if needed
   alembic merge -m "merge branches" rev1 rev2
   ```

4. **Rollback fails**
   - Check for dependent objects created outside migration
   - May need to manually drop constraints first

## Summary

This migration provides a production-ready PostgreSQL schema that:
- ✅ Implements complete V7 specification
- ✅ Uses PostgreSQL-specific optimizations
- ✅ Supports efficient deduplication
- ✅ Enables fast queries with proper indexes
- ✅ Handles soft deletes correctly
- ✅ Provides clean rollback path

The migration is idempotent and can be safely re-run if needed. It's designed to work with your existing Alembic setup with minimal configuration changes.