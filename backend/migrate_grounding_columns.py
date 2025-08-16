"""
Migration script to add grounding tracking columns to prompt_results table
Run this ONCE to update your existing database
"""

from sqlalchemy import text
from app.database import engine

def add_grounding_columns():
    """Add the new grounding tracking columns to prompt_results table"""
    
    with engine.begin() as conn:
        # Check if columns already exist (for idempotency)
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'prompt_results' 
            AND column_name IN ('tool_call_count', 'grounded_effective', 'json_valid', 'als_variant_id')
        """)
        
        # For SQLite, we need a different approach
        try:
            result = conn.execute(check_query)
            existing_columns = {row[0] for row in result}
        except:
            # SQLite doesn't have information_schema, use pragma
            pragma_query = text("PRAGMA table_info(prompt_results)")
            result = conn.execute(pragma_query)
            existing_columns = {row[1] for row in result}
        
        # Add missing columns
        if 'tool_call_count' not in existing_columns:
            print("Adding tool_call_count column...")
            conn.execute(text("""
                ALTER TABLE prompt_results 
                ADD COLUMN tool_call_count INTEGER DEFAULT 0
            """))
            print("[OK] Added tool_call_count")
        
        if 'grounded_effective' not in existing_columns:
            print("Adding grounded_effective column...")
            conn.execute(text("""
                ALTER TABLE prompt_results 
                ADD COLUMN grounded_effective BOOLEAN DEFAULT FALSE
            """))
            print("[OK] Added grounded_effective")
        
        if 'json_valid' not in existing_columns:
            print("Adding json_valid column...")
            conn.execute(text("""
                ALTER TABLE prompt_results 
                ADD COLUMN json_valid BOOLEAN DEFAULT TRUE
            """))
            print("[OK] Added json_valid")
        
        if 'als_variant_id' not in existing_columns:
            print("Adding als_variant_id column...")
            conn.execute(text("""
                ALTER TABLE prompt_results 
                ADD COLUMN als_variant_id VARCHAR(50)
            """))
            print("[OK] Added als_variant_id")
        
        print("\nUpdating historical GPT-5 'grounded' data to reflect reality...")
        
        # Mark all historical GPT-5 "grounded" tests as actually ungrounded
        update_query = text("""
            UPDATE prompt_results 
            SET grounded_effective = 0,
                tool_call_count = 0
            WHERE run_id IN (
                SELECT id FROM prompt_runs 
                WHERE model_name LIKE 'gpt-5%' 
                AND grounding_mode = 'web'
            )
        """)
        
        result = conn.execute(update_query)
        rows_updated = result.rowcount if hasattr(result, 'rowcount') else 0
        
        if rows_updated > 0:
            print(f"[OK] Marked {rows_updated} fake 'grounded' GPT-5 tests as ungrounded")
        
        # Add note to prompt_runs table if it has a notes column
        try:
            conn.execute(text("""
                UPDATE prompt_runs
                SET error_message = COALESCE(error_message || ' | ', '') || 
                    'Note: Grounding was not implemented for GPT-5 at time of test'
                WHERE model_name LIKE 'gpt-5%'
                AND grounding_mode = 'web'
                AND DATE(created_at) < '2025-08-16'
            """))
            print("[OK] Added notes to historical GPT-5 grounded runs")
        except:
            print("[WARNING] Could not add notes (error_message column may not exist)")
        
        print("\n[SUCCESS] Migration complete!")
        print("\nSummary:")
        print("- New columns added for grounding tracking")
        print("- Historical GPT-5 'grounded' data marked as invalid")
        print("- System ready for REAL grounding implementation")

if __name__ == "__main__":
    print("Starting grounding columns migration...")
    print("=" * 50)
    
    try:
        add_grounding_columns()
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {str(e)}")
        print("\nThis might mean:")
        print("1. Columns already exist (safe to ignore)")
        print("2. Database connection issues")
        print("3. Permission issues")
    
    print("\n" + "=" * 50)
    print("Migration script finished")