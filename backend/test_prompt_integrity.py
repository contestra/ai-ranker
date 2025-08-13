"""
Test script to verify prompt integrity checking functionality
"""

import sqlite3
from app.services.prompt_hasher import (
    calculate_prompt_hash,
    verify_prompt_integrity,
    detect_prompt_modification
)

def test_integrity_checking():
    """Test the prompt integrity checking functionality."""
    
    print("=" * 60)
    print("Testing Prompt Integrity Checking")
    print("=" * 60)
    
    # Test 1: Hash calculation
    print("\n1. Testing hash calculation:")
    test_prompt = "What are the top AI companies in 2025?"
    hash1 = calculate_prompt_hash(test_prompt)
    print(f"   Prompt: {test_prompt}")
    print(f"   SHA256: {hash1}")
    
    # Test 2: Consistent hashing
    print("\n2. Testing hash consistency:")
    hash2 = calculate_prompt_hash(test_prompt)
    print(f"   Same prompt hashed again: {hash2}")
    print(f"   Hashes match: {hash1 == hash2}")
    
    # Test 3: Different prompts produce different hashes
    print("\n3. Testing different prompts:")
    different_prompt = "What are the top AI companies in 2024?"
    hash3 = calculate_prompt_hash(different_prompt)
    print(f"   Different prompt: {different_prompt}")
    print(f"   Hash: {hash3}")
    print(f"   Different from original: {hash1 != hash3}")
    
    # Test 4: Whitespace normalization
    print("\n4. Testing whitespace normalization:")
    prompt_with_spaces = "  What are the top AI companies in 2025?  \n"
    hash4 = calculate_prompt_hash(prompt_with_spaces)
    print(f"   Prompt with extra whitespace: '{prompt_with_spaces}'")
    print(f"   Hash matches normalized: {hash1 == hash4}")
    
    # Test 5: Integrity verification
    print("\n5. Testing integrity verification:")
    is_valid, current_hash = verify_prompt_integrity(hash1, test_prompt)
    print(f"   Original hash: {hash1}")
    print(f"   Current hash:  {current_hash}")
    print(f"   Integrity valid: {is_valid}")
    
    # Test 6: Detect modification
    print("\n6. Testing modification detection:")
    modified_prompt = "What are the best AI companies in 2025?"  # Changed "top" to "best"
    is_valid, modified_hash = verify_prompt_integrity(hash1, modified_prompt)
    print(f"   Original prompt: {test_prompt}")
    print(f"   Modified prompt: {modified_prompt}")
    print(f"   Modification detected: {not is_valid}")
    
    # Test 7: Check database
    print("\n7. Checking database integrity:")
    conn = sqlite3.connect("ai_ranker.db")
    cursor = conn.cursor()
    
    # Check templates with hashes
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(prompt_hash) as with_hash,
               COUNT(DISTINCT prompt_hash) as unique_hashes
        FROM prompt_templates
    """)
    stats = cursor.fetchone()
    print(f"   Templates: {stats[0]} total, {stats[1]} with hashes, {stats[2]} unique")
    
    # Find any duplicates
    cursor.execute("""
        SELECT prompt_hash, COUNT(*) as count
        FROM prompt_templates
        WHERE prompt_hash IS NOT NULL
        GROUP BY prompt_hash
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()
    if duplicates:
        print(f"   Found {len(duplicates)} duplicate prompts:")
        for hash_val, count in duplicates[:3]:  # Show first 3
            print(f"     - Hash {hash_val[:16]}... appears {count} times")
    else:
        print("   No duplicate prompts found")
    
    # Test 8: Verify a specific template
    print("\n8. Verifying a random template:")
    cursor.execute("""
        SELECT id, template_name, prompt_text, prompt_hash
        FROM prompt_templates
        WHERE prompt_hash IS NOT NULL
        LIMIT 1
    """)
    template = cursor.fetchone()
    if template:
        template_id, name, text, stored_hash = template
        is_valid, recalculated = verify_prompt_integrity(stored_hash, text)
        print(f"   Template: {name}")
        print(f"   Stored hash:  {stored_hash[:32]}...")
        print(f"   Current hash: {recalculated[:32]}...")
        print(f"   Integrity: {'VALID' if is_valid else 'CORRUPTED'}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("Integrity checking tests complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_integrity_checking()