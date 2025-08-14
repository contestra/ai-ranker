"""Check how results are linked to hashed prompts"""
import sqlite3

conn = sqlite3.connect('ai_ranker.db')
cursor = conn.cursor()

print("=" * 80)
print("PROMPT HASH LINKAGE VERIFICATION")
print("=" * 80)

# 1. Check table structure
print("\n1. TABLE STRUCTURE:")
cursor.execute("PRAGMA table_info(prompt_results)")
columns = cursor.fetchall()
hash_columns = [col for col in columns if 'hash' in col[1].lower()]
print(f"   Hash columns in prompt_results: {[col[1] for col in hash_columns]}")

cursor.execute("PRAGMA table_info(prompt_templates)")
columns = cursor.fetchall()
hash_columns = [col for col in columns if 'hash' in col[1].lower()]
print(f"   Hash columns in prompt_templates: {[col[1] for col in hash_columns]}")

# 2. Check linkage
print("\n2. RESULT-TO-TEMPLATE LINKAGE:")
cursor.execute("""
    SELECT COUNT(*) FROM prompt_results pr
    JOIN prompt_runs prun ON pr.run_id = prun.id
    WHERE pr.prompt_hash IS NOT NULL
""")
total_with_hash = cursor.fetchone()[0]
print(f"   Results with prompt_hash: {total_with_hash}")

# 3. Check integrity
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN pr.prompt_hash = pt.prompt_hash THEN 1 ELSE 0 END) as matching
    FROM prompt_results pr
    JOIN prompt_runs prun ON pr.run_id = prun.id
    JOIN prompt_templates pt ON prun.template_id = pt.id
    WHERE pr.prompt_hash IS NOT NULL AND pt.prompt_hash IS NOT NULL
""")
stats = cursor.fetchone()
print(f"   Results linked to templates: {stats[0]}")
print(f"   Results matching template hash: {stats[1]}")
print(f"   Results modified from template: {stats[0] - stats[1]}")

# 4. Show example
print("\n3. EXAMPLE RECORD:")
cursor.execute("""
    SELECT 
        pr.id as result_id,
        pr.run_id,
        prun.template_id,
        pr.prompt_hash as result_hash,
        pt.prompt_hash as template_hash,
        LENGTH(pr.prompt_text) as prompt_length,
        LENGTH(pr.model_response) as response_length
    FROM prompt_results pr
    JOIN prompt_runs prun ON pr.run_id = prun.id
    JOIN prompt_templates pt ON prun.template_id = pt.id
    WHERE pr.prompt_hash IS NOT NULL
    LIMIT 1
""")
example = cursor.fetchone()
if example:
    print(f"   Result ID: {example[0]}")
    print(f"   Run ID: {example[1]} -> Template ID: {example[2]}")
    print(f"   Result hash: {example[3][:32]}...")
    print(f"   Template hash: {example[4][:32]}...")
    print(f"   Hash match: {'YES' if example[3] == example[4] else 'NO (modified)'}")
    print(f"   Prompt length: {example[5]} chars")
    print(f"   Response length: {example[6]} chars")

print("\n" + "=" * 80)
print("SUMMARY: Each result stores:")
print("  1. The exact prompt text that was sent")
print("  2. The SHA256 hash of that prompt")
print("  3. Link to the run (run_id)")
print("  4. Run links to template (template_id)")
print("  5. Can verify if prompt was modified by comparing hashes")
print("=" * 80)

conn.close()