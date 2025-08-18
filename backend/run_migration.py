#!/usr/bin/env python
"""Run the SQL migration to add new columns."""

import sqlite3
import sys
import io

# Configure stdout for UTF-8 to prevent encoding errors on Windows
sys.stdout.reconfigure(encoding='utf-8')

def run_migration():
    """Execute the migration SQL script."""
    
    # Read the migration SQL
    with open('migrations/add_grounding_metadata.sql', 'r') as f:
        migration_sql = f.read()
    
    # Connect to database
    conn = sqlite3.connect('ai_ranker.db')
    cursor = conn.cursor()
    
    # Split into individual statements (SQLite requires one at a time)
    statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    print("Running migration...")
    print("-" * 50)
    
    for statement in statements:
        if not statement or statement.startswith('--'):
            continue
            
        try:
            cursor.execute(statement)
            success_count += 1
            # Extract table/column name for logging
            if 'ALTER TABLE' in statement:
                parts = statement.split()
                if len(parts) >= 6:
                    table = parts[2]
                    column = parts[5]
                    print(f"✓ Added column {column} to {table}")
            elif 'CREATE INDEX' in statement:
                # Extract index name
                if 'idx_' in statement:
                    idx_start = statement.index('idx_')
                    idx_end = statement.index(' ', idx_start) if ' ' in statement[idx_start:] else len(statement)
                    idx_name = statement[idx_start:idx_end]
                    print(f"✓ Created index {idx_name}")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e):
                skip_count += 1
                print(f"⚬ Skipped (column already exists): {str(e)}")
            elif 'already exists' in str(e):
                skip_count += 1
                print(f"⚬ Skipped (already exists): {str(e)}")
            else:
                error_count += 1
                print(f"✗ Error: {str(e)}")
                print(f"  Statement: {statement[:100]}...")
    
    conn.commit()
    conn.close()
    
    print("-" * 50)
    print(f"Migration completed:")
    print(f"  ✓ Success: {success_count}")
    print(f"  ⚬ Skipped: {skip_count}")
    print(f"  ✗ Errors: {error_count}")
    
    return error_count == 0

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)