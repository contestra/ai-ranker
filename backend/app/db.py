from sqlalchemy import create_engine
import os

# Get DATABASE_URL from environment
DATABASE_URL = os.environ["DATABASE_URL"]

# Create engine with Postgres-optimized settings
engine = create_engine(
    DATABASE_URL, 
    pool_size=5, 
    max_overflow=10, 
    pool_pre_ping=True
)