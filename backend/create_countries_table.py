"""Create countries table for managing supported countries and ALS testing"""
from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.database_url)

# Create countries table
with engine.begin() as conn:
    # Create countries table
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            flag_emoji TEXT,
            timezone TEXT,
            civic_keyword TEXT,
            has_als_support BOOLEAN DEFAULT 0,
            gpt5_test_status TEXT DEFAULT 'untested',
            gpt5_test_date TEXT,
            gpt5_test_results TEXT,
            gemini_test_status TEXT DEFAULT 'untested', 
            gemini_test_date TEXT,
            gemini_test_results TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """))
    
    # Insert default supported countries
    countries_data = [
        ('DE', 'Germany', '🇩🇪', 'Europe/Berlin', 'Bürgeramt', 1),
        ('CH', 'Switzerland', '🇨🇭', 'Europe/Zurich', 'Bundesverwaltung', 1),
        ('US', 'United States', '🇺🇸', 'America/New_York', 'state DMV', 1),
        ('GB', 'United Kingdom', '🇬🇧', 'Europe/London', 'GOV.UK', 1),
        ('AE', 'United Arab Emirates', '🇦🇪', 'Asia/Dubai', 'سياق محلي', 1),
        ('SG', 'Singapore', '🇸🇬', 'Asia/Singapore', 'SingPass', 1),
        ('IT', 'Italy', '🇮🇹', 'Europe/Rome', 'Agenzia delle Entrate', 1),
        ('FR', 'France', '🇫🇷', 'Europe/Paris', 'service-public.fr', 1),
    ]
    
    for code, name, flag, tz, keyword, has_als in countries_data:
        conn.execute(text("""
            INSERT OR IGNORE INTO countries (code, name, flag_emoji, timezone, civic_keyword, has_als_support)
            VALUES (:code, :name, :flag, :tz, :keyword, :has_als)
        """), {
            "code": code,
            "name": name, 
            "flag": flag,
            "tz": tz,
            "keyword": keyword,
            "has_als": has_als
        })
    
    print("Countries table created successfully")
    
    # Verify data
    result = conn.execute(text("SELECT code, name, flag_emoji FROM countries"))
    for row in result:
        print(f"{row[2]} {row[1]} ({row[0]})")