"""
Create tables for multi-tenant crawler monitor
"""

from app.database import engine, Base
from app.models import Domain, BotEvent

def create_tables():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)
    print("[OK] Tables created successfully!")
    
    # Show created tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print("\nDatabase tables:")
    for table in sorted(tables):
        print(f"  - {table}")
    
    if 'domains' in tables and 'bot_events' in tables:
        print("\n[OK] Multi-tenant tables created:")
        print("  - domains: Store tracked domains per brand")
        print("  - bot_events: Store bot traffic events per domain")
    else:
        print("\n[WARNING] Multi-tenant tables may not have been created")

if __name__ == "__main__":
    create_tables()