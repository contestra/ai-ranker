"""
Clean up test/dummy data from the database
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import get_db, engine
from app.models import BotEvent, Domain, DailyBotStats
import json

def cleanup_test_data():
    """Remove all test data from the database"""
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Method 1: Delete events with test metadata flag
        test_events_deleted = 0
        events_with_metadata = db.query(BotEvent).filter(
            BotEvent.event_metadata != None
        ).all()
        
        for event in events_with_metadata:
            if event.event_metadata and isinstance(event.event_metadata, dict):
                if event.event_metadata.get('test') == True:
                    db.delete(event)
                    test_events_deleted += 1
        
        # Method 2: Delete all events for the test domain
        test_domain = "insights.avea-life.com"
        domain = db.query(Domain).filter(Domain.url == test_domain).first()
        
        domain_events_deleted = 0
        if domain:
            # Delete all events for this domain
            domain_events = db.query(BotEvent).filter(
                BotEvent.domain_id == domain.id
            ).all()
            
            for event in domain_events:
                db.delete(event)
                domain_events_deleted += 1
            
            # Delete daily stats for this domain
            stats = db.query(DailyBotStats).filter(
                DailyBotStats.domain_id == domain.id
            ).all()
            
            for stat in stats:
                db.delete(stat)
            
            print(f"Deleted {len(stats)} daily stats records for {test_domain}")
            
            # Optionally delete the domain itself
            # db.delete(domain)
            # print(f"Deleted domain: {test_domain}")
        
        # Commit all deletions
        db.commit()
        
        print(f"\n=== Cleanup Complete ===")
        print(f"Deleted {test_events_deleted} events with test metadata flag")
        print(f"Deleted {domain_events_deleted} events for domain {test_domain}")
        print(f"Total events deleted: {test_events_deleted + domain_events_deleted}")
        
        # Show remaining event count
        remaining_events = db.query(BotEvent).count()
        print(f"\nRemaining events in database: {remaining_events}")
        
        # Show domains with events
        domains_with_events = db.execute(text("""
            SELECT d.url, COUNT(be.id) as event_count
            FROM domains d
            LEFT JOIN bot_events be ON d.id = be.domain_id
            GROUP BY d.id, d.url
            HAVING COUNT(be.id) > 0
        """)).fetchall()
        
        if domains_with_events:
            print("\nDomains with remaining events:")
            for domain_url, count in domains_with_events:
                print(f"  - {domain_url}: {count} events")
        else:
            print("\nNo domains have any events (database is clean)")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting cleanup of test/dummy data...")
    cleanup_test_data()