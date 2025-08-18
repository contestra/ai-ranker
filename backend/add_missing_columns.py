#!/usr/bin/env python
"""Add the missing columns that weren't added in the first migration."""

import sqlite3
import sys
import io

# Configure stdout for UTF-8
sys.stdout.reconfigure(encoding='utf-8')

def add_missing_columns():
    """Add columns that were missed in the initial migration."""
    
    conn = sqlite3.connect('ai_ranker.db')
    cursor = conn.cursor()
    
    missing_columns = [
        ("prompt_templates", "provider", "TEXT"),
        ("prompt_runs", "provider", "TEXT"),
        ("prompt_results", "citations", "TEXT"),
        ("prompt_runs", "idx_runs_composite", None)  # Special marker for index
    ]
    
    success_count = 0
    skip_count = 0
    
    print("Adding missing columns...")
    print("-" * 50)
    
    for table, column, dtype in missing_columns:
        if column == "idx_runs_composite":
            # Create the composite index
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_runs_composite 
                    ON prompt_runs(provider, model_name, grounding_mode_requested, created_at)
                """)
                success_count += 1
                print(f"✓ Created composite index idx_runs_composite")
            except sqlite3.OperationalError as e:
                if 'no such column: provider' in str(e):
                    # Provider column missing, create it first
                    try:
                        cursor.execute("ALTER TABLE prompt_runs ADD COLUMN provider TEXT")
                        print(f"✓ Added column provider to prompt_runs")
                        # Now try the index again
                        cursor.execute("""
                            CREATE INDEX IF NOT EXISTS idx_runs_composite 
                            ON prompt_runs(provider, model_name, grounding_mode_requested, created_at)
                        """)
                        success_count += 2
                        print(f"✓ Created composite index idx_runs_composite")
                    except Exception as e2:
                        print(f"✗ Error creating index: {e2}")
                else:
                    print(f"⚬ Index might already exist: {e}")
                    skip_count += 1
        else:
            # Add regular column
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {dtype}")
                success_count += 1
                print(f"✓ Added column {column} to {table}")
            except sqlite3.OperationalError as e:
                if 'duplicate column name' in str(e):
                    skip_count += 1
                    print(f"⚬ Column {column} already exists in {table}")
                else:
                    print(f"✗ Error adding {column} to {table}: {e}")
    
    # Now create the provider index
    try:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_templates_provider 
            ON prompt_templates(provider)
        """)
        success_count += 1
        print(f"✓ Created index idx_templates_provider")
    except Exception as e:
        print(f"⚬ Index idx_templates_provider might already exist: {e}")
        skip_count += 1
    
    conn.commit()
    conn.close()
    
    print("-" * 50)
    print(f"Missing columns migration completed:")
    print(f"  ✓ Success: {success_count}")
    print(f"  ⚬ Skipped: {skip_count}")
    
    return True

if __name__ == "__main__":
    add_missing_columns()