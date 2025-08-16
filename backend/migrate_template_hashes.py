#!/usr/bin/env python
"""
Migration script to update existing prompt template hashes from text-only to bundle hashes.
This ensures existing templates work correctly with the new bundle-aware deduplication.
"""

import sqlite3
import json
import sys
sys.path.append('.')

from app.services.prompt_hasher import calculate_bundle_hash

def migrate_hashes():
    conn = sqlite3.connect('ai_ranker.db')
    cursor = conn.cursor()
    
    # Get all templates
    cursor.execute("""
        SELECT id, prompt_text, model_name, countries, grounding_modes, prompt_type, prompt_hash 
        FROM prompt_templates
    """)
    
    templates = cursor.fetchall()
    updated_count = 0
    
    for template in templates:
        template_id, prompt_text, model_name, countries_str, modes_str, prompt_type, old_hash = template
        
        # Parse JSON fields
        countries = json.loads(countries_str) if isinstance(countries_str, str) else countries_str
        modes = json.loads(modes_str) if isinstance(modes_str, str) else modes_str
        
        # Calculate new bundle hash
        new_hash = calculate_bundle_hash(
            prompt_text,
            model_name=model_name or 'gemini',
            countries=countries or ['US'],
            grounding_modes=modes or ['none'],
            prompt_type=prompt_type or 'custom'
        )
        
        # Only update if hash is different
        if old_hash != new_hash:
            cursor.execute(
                "UPDATE prompt_templates SET prompt_hash = ? WHERE id = ?",
                (new_hash, template_id)
            )
            updated_count += 1
            print(f"Updated template {template_id}: {old_hash[:16]}... -> {new_hash[:16]}...")
    
    conn.commit()
    conn.close()
    
    print(f"\nMigration complete. Updated {updated_count} of {len(templates)} templates.")

if __name__ == "__main__":
    print("Migrating prompt template hashes to bundle-aware format...")
    migrate_hashes()