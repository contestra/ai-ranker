"""
Create database tables for Prompt Tracking feature (SQLite compatible)
Run this after the main create_tables.py
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./ai_ranker.db"

engine = create_engine(DATABASE_URL)

def create_prompt_tracking_tables():
    """Create tables for prompt tracking feature (SQLite compatible)"""
    
    with engine.begin() as conn:
        # Create prompt_templates table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS prompt_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_name VARCHAR(255) NOT NULL,
                template_name VARCHAR(255) NOT NULL,
                prompt_text TEXT NOT NULL,
                prompt_type VARCHAR(50) DEFAULT 'custom',
                countries TEXT, -- JSON array stored as text
                grounding_modes TEXT, -- JSON array stored as text
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(brand_name, template_name)
            )
        """))
        
        # Create prompt_runs table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS prompt_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER REFERENCES prompt_templates(id) ON DELETE CASCADE,
                brand_name VARCHAR(255) NOT NULL,
                model_name VARCHAR(100) NOT NULL,
                country_code VARCHAR(10),
                grounding_mode VARCHAR(20),
                status VARCHAR(50) DEFAULT 'pending',
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                tokens_used INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create prompt_results table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS prompt_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER REFERENCES prompt_runs(id) ON DELETE CASCADE,
                prompt_text TEXT NOT NULL,
                model_response TEXT,
                brand_mentioned BOOLEAN DEFAULT 0,
                mention_count INTEGER DEFAULT 0,
                mention_positions TEXT, -- JSON array stored as text
                competitors_mentioned TEXT, -- JSON array stored as text
                confidence_score REAL,
                response_metadata TEXT, -- JSON stored as text
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create prompt_schedules table for periodic runs
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS prompt_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER REFERENCES prompt_templates(id) ON DELETE CASCADE,
                schedule_type VARCHAR(50), -- 'daily', 'weekly', 'monthly'
                run_time TIME,
                timezone VARCHAR(50) DEFAULT 'UTC',
                last_run_at TIMESTAMP,
                next_run_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create indexes for better query performance
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_prompt_runs_brand ON prompt_runs(brand_name)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_prompt_runs_status ON prompt_runs(status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_prompt_results_run ON prompt_results(run_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_prompt_schedules_next_run ON prompt_schedules(next_run_at)"))
        
        print("SUCCESS: Prompt tracking tables created successfully!")
        
        # Add some default prompt templates (using JSON strings for arrays)
        conn.execute(text("""
            INSERT OR IGNORE INTO prompt_templates (brand_name, template_name, prompt_text, prompt_type, countries, grounding_modes)
            VALUES 
            ('DEFAULT', 'Brand Recognition', 'What do you know about {brand_name}?', 'recognition', '["US", "GB"]', '["none", "web"]'),
            ('DEFAULT', 'Competitor Analysis', 'What are the main competitors of {brand_name}?', 'competitive', '["US"]', '["none", "web"]'),
            ('DEFAULT', 'Product Knowledge', 'What products or services does {brand_name} offer?', 'product', '["US"]', '["none", "web"]'),
            ('DEFAULT', 'Industry Position', 'What is {brand_name}''s position in its industry?', 'industry', '["US"]', '["none"]')
        """))
        
        print("SUCCESS: Default prompt templates added!")

if __name__ == "__main__":
    create_prompt_tracking_tables()