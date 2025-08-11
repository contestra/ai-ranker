"""
Test multi-tenant crawler monitor functionality
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_domain_validation():
    """Test domain validation endpoint"""
    print("\n1. Testing domain validation...")
    
    test_domains = [
        "wordpress-site.com",
        "shopify-store.myshopify.com",
        "custom-site.io",
        "wix-site.wixsite.com"
    ]
    
    for domain in test_domains:
        response = requests.post(
            f"{BASE_URL}/api/domains/validate",
            json={"url": domain}
        )
        if response.status_code == 200:
            data = response.json()
            trackable = "YES" if data.get("is_trackable") else "NO"
            tech = ", ".join(data.get("technology", []))
            print(f"  {domain}: Trackable={trackable}, Technology={tech}")
        else:
            print(f"  {domain}: Validation failed")

def test_ingest_bot_traffic():
    """Test ingesting bot traffic"""
    print("\n2. Testing bot traffic ingestion...")
    
    # Simulate ChatGPT bot hit
    bot_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "domain": "test-domain.com",
        "method": "GET",
        "path": "/products/ai-assistant",
        "status": 200,
        "user_agent": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot",
        "client_ip": "52.41.93.1",
        "provider": "openai",
        "metadata": {
            "referrer": "https://chat.openai.com/",
            "is_test": True
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/crawler/v2/ingest/generic",
        json=bot_data
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"  Bot traffic accepted: is_bot={data.get('is_bot')}")
    else:
        print(f"  Failed to ingest: {response.text}")

def test_get_stats():
    """Test getting domain stats"""
    print("\n3. Testing stats retrieval...")
    
    response = requests.get(
        f"{BASE_URL}/api/crawler/v2/monitor/stats/test-domain.com?hours=24"
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"  Total hits: {data.get('total_hits', 0)}")
        print(f"  Bot hits: {data.get('bot_hits', 0)}")
        print(f"  On-demand hits: {data.get('on_demand_hits', 0)}")
        print(f"  Bot percentage: {data.get('bot_percentage', 0):.1f}%")
    else:
        print(f"  No stats available for test-domain.com")

def test_brand_domains():
    """Test getting domains for a brand"""
    print("\n4. Testing brand domains...")
    
    # First, create a test brand
    response = requests.post(
        f"{BASE_URL}/api/brands",
        json={
            "name": "Test Brand",
            "domain": "",
            "aliases": [],
            "category": [],
            "use_canonical_entities": True
        }
    )
    
    if response.status_code == 200:
        brand = response.json()
        brand_id = brand["id"]
        print(f"  Created test brand with ID: {brand_id}")
        
        # Get domains for this brand
        response = requests.get(
            f"{BASE_URL}/api/crawler/v2/monitor/brand/{brand_id}/domains"
        )
        
        if response.status_code == 200:
            domains = response.json()
            print(f"  Brand has {len(domains)} domains")
            for domain in domains:
                print(f"    - {domain['url']}: {domain.get('technology', 'unknown')}")
        else:
            print(f"  Failed to get brand domains")
    else:
        print(f"  Failed to create test brand")

if __name__ == "__main__":
    print("Testing Multi-Tenant Crawler Monitor")
    print("=" * 40)
    
    try:
        test_domain_validation()
        test_ingest_bot_traffic()
        test_get_stats()
        test_brand_domains()
        
        print("\n" + "=" * 40)
        print("[OK] All tests completed!")
        print("\nYou can now:")
        print("1. Open http://localhost:3001 in your browser")
        print("2. Navigate to the 'Crawler Monitor' tab")
        print("3. Add domains directly in the interface")
        print("4. Install the WordPress plugin on tracked sites")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        print("\nMake sure the backend is running on port 8000")