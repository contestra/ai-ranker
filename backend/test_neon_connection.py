"""Test Neon database connection"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.development')

# Set UTF-8 encoding for Windows
sys.stdout.reconfigure(encoding='utf-8')

# Test connection
try:
    from sqlalchemy import create_engine, text
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not found in .env.development")
        sys.exit(1)
    
    print(f"Connecting to Neon database...")
    print(f"Host: ep-little-block-a23fv9os-pooler.eu-central-1.aws.neon.tech")
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.scalar()
        print(f"SUCCESS! Connected to PostgreSQL")
        print(f"Version: {version}")
        
        # Check if we can create tables
        result = conn.execute(text("SELECT current_database(), current_user"))
        db, user = result.fetchone()
        print(f"Database: {db}")
        print(f"User: {user}")
        
except Exception as e:
    print(f"ERROR: Failed to connect to database")
    print(f"Error: {e}")
    sys.exit(1)