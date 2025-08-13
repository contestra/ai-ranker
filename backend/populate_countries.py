"""Populate countries table with initial data"""
from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.database_url)

with engine.begin() as conn:
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
        result = conn.execute(text("""
            INSERT OR REPLACE INTO countries (code, name, flag_emoji, timezone, civic_keyword, has_als_support)
            VALUES (:code, :name, :flag, :tz, :keyword, :has_als)
        """), {
            "code": code,
            "name": name, 
            "flag": flag,
            "tz": tz,
            "keyword": keyword,
            "has_als": has_als
        })
        print(f"Inserted {name} ({code})")
    
    # Verify data
    count = conn.execute(text("SELECT COUNT(*) FROM countries")).scalar()
    print(f"\nTotal countries in database: {count}")