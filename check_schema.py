"""Check table schema"""
import sqlite3

conn = sqlite3.connect("backend/ai_ranker.db")
cursor = conn.cursor()

# Check prompt_templates columns
cursor.execute("PRAGMA table_info(prompt_templates)")
columns = cursor.fetchall()
print("prompt_templates columns:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

conn.close()