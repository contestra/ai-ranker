"""
Migration script to add prompt_hash columns to existing databases.
Adds hash columns and calculates hashes for existing data.
"""

import sqlite3
import hashlib
from pathlib import Path

def calculate_prompt_hash(prompt_text: str) -> str:
    """Calculate SHA256 hash of prompt text."""
    if not prompt_text:
        return hashlib.sha256(b'').hexdigest()
    
    # Normalize the prompt
    normalized = prompt_text.strip()
    normalized = normalized.replace('\r\n', '\n').replace('\r', '\n')
    
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

def migrate_database(db_path: str):
    """Add prompt_hash columns and populate with hashes."""
    print(f"Migrating database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(prompt_templates)")
        template_columns = [col[1] for col in cursor.fetchall()]
        
        cursor.execute("PRAGMA table_info(prompt_results)")
        result_columns = [col[1] for col in cursor.fetchall()]
        
        # Add prompt_hash to prompt_templates if not exists
        if 'prompt_hash' not in template_columns:
            print("Adding prompt_hash column to prompt_templates...")
            cursor.execute("""
                ALTER TABLE prompt_templates 
                ADD COLUMN prompt_hash VARCHAR(64)
            """)
            conn.commit()
            
            # Calculate hashes for existing templates
            print("Calculating hashes for existing templates...")
            cursor.execute("SELECT id, prompt_text FROM prompt_templates")
            templates = cursor.fetchall()
            
            for template_id, prompt_text in templates:
                if prompt_text:
                    prompt_hash = calculate_prompt_hash(prompt_text)
                    cursor.execute(
                        "UPDATE prompt_templates SET prompt_hash = ? WHERE id = ?",
                        (prompt_hash, template_id)
                    )
            conn.commit()
            print(f"Updated {len(templates)} templates with hashes")
        else:
            print("prompt_hash column already exists in prompt_templates")
        
        # Add prompt_hash to prompt_results if not exists
        if 'prompt_hash' not in result_columns:
            print("Adding prompt_hash column to prompt_results...")
            cursor.execute("""
                ALTER TABLE prompt_results 
                ADD COLUMN prompt_hash VARCHAR(64)
            """)
            conn.commit()
            
            # Calculate hashes for existing results
            print("Calculating hashes for existing results...")
            cursor.execute("SELECT id, prompt_text FROM prompt_results")
            results = cursor.fetchall()
            
            for result_id, prompt_text in results:
                if prompt_text:
                    prompt_hash = calculate_prompt_hash(prompt_text)
                    cursor.execute(
                        "UPDATE prompt_results SET prompt_hash = ? WHERE id = ?",
                        (prompt_hash, result_id)
                    )
            conn.commit()
            print(f"Updated {len(results)} results with hashes")
        else:
            print("prompt_hash column already exists in prompt_results")
        
        # Create index on hash columns for faster lookups
        print("Creating indexes on hash columns...")
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_prompt_templates_hash 
                ON prompt_templates(prompt_hash)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_prompt_results_hash 
                ON prompt_results(prompt_hash)
            """)
            conn.commit()
            print("Indexes created successfully")
        except Exception as e:
            print(f"Index creation skipped (may already exist): {e}")
        
        # Verify migration
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COUNT(prompt_hash) as with_hash
            FROM prompt_templates
        """)
        stats = cursor.fetchone()
        print(f"\nMigration complete!")
        print(f"Templates: {stats[0]} total, {stats[1]} with hashes")
        
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COUNT(prompt_hash) as with_hash
            FROM prompt_results
        """)
        stats = cursor.fetchone()
        print(f"Results: {stats[0]} total, {stats[1]} with hashes")
        
    except Exception as e:
        print(f"Migration error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """Run migration on all relevant databases."""
    # The prompt tables are in ai_ranker.db
    databases = [
        "ai_ranker.db",
        "../ai_ranker.db"  # Check parent directory too
    ]
    
    for db_name in databases:
        db_path = Path(db_name)
        if db_path.exists():
            try:
                migrate_database(str(db_path))
                print(f"[OK] Successfully migrated {db_name}\n")
            except Exception as e:
                print(f"[FAIL] Failed to migrate {db_name}: {e}\n")
        else:
            print(f"- Skipping {db_name} (not found)\n")

if __name__ == "__main__":
    print("=" * 60)
    print("Prompt Hash Migration Script")
    print("=" * 60)
    print("\nThis script will:")
    print("1. Add prompt_hash columns to prompt_templates and prompt_results")
    print("2. Calculate SHA256 hashes for all existing prompts")
    print("3. Create indexes for faster hash lookups")
    print("\n" + "=" * 60 + "\n")
    
    main()
    
    print("\n" + "=" * 60)
    print("Migration complete! Prompt integrity checking is now enabled.")
    print("=" * 60)