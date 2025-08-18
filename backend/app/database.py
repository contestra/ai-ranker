from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

from app.config import settings

# Get DATABASE_URL from environment, require it
database_url = os.environ.get("DATABASE_URL") or settings.database_url
if not database_url:
    raise ValueError("DATABASE_URL environment variable is required")

# Fix postgres:// to postgresql:// for SQLAlchemy 2.0
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Ensure we're using PostgreSQL with required SSL
if "sqlite" in database_url.lower():
    raise ValueError("SQLite is no longer supported. Please use PostgreSQL with DATABASE_URL")

# Create engine with Postgres-optimized settings
engine = create_engine(
    database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()