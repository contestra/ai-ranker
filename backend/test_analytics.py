"""
Test analytics by creating some bot event data
"""

import requests
import json
from datetime import datetime, timedelta
import random

BASE_URL = "http://localhost:8000"

# Different bot user agents
BOT_AGENTS = {
    "ChatGPT-User": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot",
    "PerplexityBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; PerplexityBot/1.0; +https://perplexity.ai/bot",
    "Claude-Web": "Mozilla/5.0 (compatible; Claude-Web/1.0; +https://anthropic.com)",
    "GPTBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.0; +https://openai.com/gptbot",
    "GoogleBot": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Human": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

PATHS = [
    "/",
    "/products",
    "/blog/ai-future",
    "/about",
    "/services",
    "/contact",
    "/blog/machine-learning",
    "/products/ai-assistant"
]

def send_bot_hit(domain: str, bot_name: str, path: str, timestamp: datetime):
    """Send a single bot hit"""
    data = {
        "timestamp": timestamp.isoformat() + "Z",
        "domain": domain,
        "method": "GET",
        "path": path,
        "status": 200,
        "user_agent": BOT_AGENTS[bot_name],
        "client_ip": f"52.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
        "provider": bot_name.split('-')[0].lower() if '-' in bot_name else bot_name.lower(),
        "metadata": {
            "test": True,
            "referrer": "https://chat.openai.com/" if "ChatGPT" in bot_name else ""
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/crawler/v2/ingest/generic",
            json=data
        )
        return response.status_code == 200
    except:
        return False

def generate_test_data(domain: str, days: int = 7):
    """Generate test data for the last N days"""
    print(f"\nGenerating test data for {domain} for the last {days} days...")
    
    now = datetime.utcnow()
    success_count = 0
    
    for day in range(days):
        date = now - timedelta(days=day)
        
        # Generate varying amounts of traffic per day
        daily_hits = random.randint(20, 100)
        
        for _ in range(daily_hits):
            # Random hour of the day
            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            timestamp = date.replace(hour=hour, minute=minute)
            
            # Pick random bot (70% bots, 30% human)
            if random.random() < 0.7:
                bot = random.choice(["ChatGPT-User", "PerplexityBot", "Claude-Web", "GPTBot", "GoogleBot"])
            else:
                bot = "Human"
            
            # Pick random path
            path = random.choice(PATHS)
            
            # Send the hit
            if send_bot_hit(domain, bot, path, timestamp):
                success_count += 1
        
        print(f"  Day {day+1}/{days}: Generated {daily_hits} hits")
    
    print(f"\nSuccessfully sent {success_count} events")
    
    # Trigger aggregation
    print("\nTriggering data aggregation...")
    for domain_id in [1, 2, 3]:  # Try first 3 domain IDs
        try:
            response = requests.post(
                f"{BASE_URL}/api/bot-analytics/domains/{domain_id}/aggregate-stats"
            )
            if response.status_code == 200:
                print(f"  Aggregation triggered for domain ID {domain_id}")
                break
        except:
            continue

if __name__ == "__main__":
    print("Bot Analytics Test Data Generator")
    print("=" * 40)
    
    # Test with insights.avea-life.com if it exists
    test_domain = "insights.avea-life.com"
    
    generate_test_data(test_domain, days=7)
    
    print("\n" + "=" * 40)
    print("Test data generation complete!")
    print("\nYou can now:")
    print("1. Go to the Crawler Monitor tab")
    print("2. Select your domain")
    print("3. Click 'Analytics' to view historical data")
    print("4. The charts should show the generated bot traffic")