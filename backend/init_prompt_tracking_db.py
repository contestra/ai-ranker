"""
Initialize database tables for prompt tracking.
Run this to create the necessary tables.
"""

import sqlite3
import json

# Connect to database
conn = sqlite3.connect('airanker.db')
cursor = conn.cursor()

# Create prompt_templates table
cursor.execute("""
CREATE TABLE IF NOT EXISTS prompt_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_name TEXT NOT NULL,
    template_name TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    prompt_type TEXT DEFAULT 'custom',
    countries TEXT DEFAULT '["US"]',
    grounding_modes TEXT DEFAULT '["none"]',
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Create prompt_runs table
cursor.execute("""
CREATE TABLE IF NOT EXISTS prompt_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    brand_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    country_code TEXT,
    grounding_mode TEXT,
    status TEXT DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES prompt_templates(id) ON DELETE CASCADE
)
""")

# Create prompt_results table (simplified schema without extra columns)
cursor.execute("""
CREATE TABLE IF NOT EXISTS prompt_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    prompt_text TEXT NOT NULL,
    model_response TEXT NOT NULL,
    brand_mentioned BOOLEAN DEFAULT 0,
    mention_count INTEGER DEFAULT 0,
    competitors_mentioned TEXT,
    confidence_score REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES prompt_runs(id) ON DELETE CASCADE
)
""")

# Create prompt_schedules table
cursor.execute("""
CREATE TABLE IF NOT EXISTS prompt_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    schedule_type TEXT NOT NULL,
    run_time TEXT NOT NULL,
    timezone TEXT DEFAULT 'UTC',
    is_active BOOLEAN DEFAULT 1,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES prompt_templates(id) ON DELETE CASCADE
)
""")

# Create indexes for better performance
cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_brand ON prompt_runs(brand_name)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_status ON prompt_runs(status)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_run ON prompt_results(run_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_brand ON prompt_templates(brand_name)")

# Insert some default templates if none exist
cursor.execute("SELECT COUNT(*) FROM prompt_templates")
count = cursor.fetchone()[0]

if count == 0:
    print("Inserting default templates...")
    
    default_templates = [
        {
            "brand_name": "DEFAULT",
            "template_name": "Top 3 Longevity Supplements",
            "prompt_text": "What are the top 3 longevity supplements?",
            "prompt_type": "custom",
            "countries": json.dumps(["NONE", "DE", "US", "GB"]),
            "grounding_modes": json.dumps(["none", "web"])
        },
        {
            "brand_name": "DEFAULT",
            "template_name": "Top 10 Longevity Companies",
            "prompt_text": "List the top 10 longevity supplement companies",
            "prompt_type": "custom",
            "countries": json.dumps(["NONE", "DE", "US", "GB"]),
            "grounding_modes": json.dumps(["none", "web"])
        },
        {
            "brand_name": "AVEA",
            "template_name": "AVEA Brand Test",
            "prompt_text": "What do you know about {brand_name} supplements?",
            "prompt_type": "brand",
            "countries": json.dumps(["NONE", "DE", "CH", "US"]),
            "grounding_modes": json.dumps(["none"])
        }
    ]
    
    for template in default_templates:
        cursor.execute("""
            INSERT INTO prompt_templates 
            (brand_name, template_name, prompt_text, prompt_type, countries, grounding_modes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            template["brand_name"],
            template["template_name"],
            template["prompt_text"],
            template["prompt_type"],
            template["countries"],
            template["grounding_modes"]
        ))
    
    print(f"Inserted {len(default_templates)} default templates")

# Commit changes
conn.commit()

# Show table info
print("\nDatabase initialized successfully!")
print("\nTables created:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
for table in cursor.fetchall():
    print(f"  - {table[0]}")

# Show template count
cursor.execute("SELECT COUNT(*) FROM prompt_templates")
template_count = cursor.fetchone()[0]
print(f"\nTotal templates: {template_count}")

# Close connection
conn.close()

print("\nDatabase ready for use!")