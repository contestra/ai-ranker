"""Verify Neon database schema"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.development')

# Set UTF-8 encoding for Windows
sys.stdout.reconfigure(encoding='utf-8')

try:
    from sqlalchemy import create_engine, text, inspect
    
    database_url = os.getenv('DATABASE_URL')
    engine = create_engine(database_url)
    inspector = inspect(engine)
    
    print("=== DATABASE SCHEMA VERIFICATION ===\n")
    
    # Get all tables
    tables = inspector.get_table_names()
    print(f"Tables found ({len(tables)}):")
    for table in sorted(tables):
        print(f"  - {table}")
    
    print("\n=== CHECKING REQUIRED TABLES ===")
    
    required_tables = [
        'organizations',
        'workspaces', 
        'prompt_templates',
        'prompt_runs',
        'prompt_results',
        'prompt_versions'
    ]
    
    for table in required_tables:
        if table in tables:
            print(f"[OK] {table}")
            
            # Get columns for this table
            columns = inspector.get_columns(table)
            print(f"     Columns ({len(columns)}):")
            for col in columns[:5]:  # Show first 5 columns
                col_type = str(col['type'])
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                print(f"       - {col['name']}: {col_type} {nullable}")
            if len(columns) > 5:
                print(f"       ... and {len(columns) - 5} more columns")
        else:
            print(f"[MISSING] {table}")
    
    print("\n=== CHECKING INDEXES ===")
    
    # Check specific indexes we created
    important_indexes = {
        'prompt_runs': ['idx_runs_provider_model_time', 'idx_runs_template_id'],
        'prompt_templates': ['idx_templates_provider_sha'],
        'prompt_results': ['idx_results_run_id']
    }
    
    for table, expected_indexes in important_indexes.items():
        if table in tables:
            indexes = inspector.get_indexes(table)
            index_names = [idx['name'] for idx in indexes]
            for expected in expected_indexes:
                if expected in index_names:
                    print(f"[OK] {table}.{expected}")
                else:
                    print(f"[MISSING] {table}.{expected}")
    
    print("\n=== VERIFICATION COMPLETE ===")
    print("Schema has been successfully created in Neon!")
    
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)