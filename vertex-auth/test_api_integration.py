#!/usr/bin/env python
"""
Test the Vertex adapter through the actual API endpoints
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

print("=" * 60)
print("TESTING VERTEX THROUGH API")
print("=" * 60)

# Test 1: Health check
print("\n1. Testing API health")
print("-" * 40)
resp = requests.get(f"{BASE_URL}/api/health")
if resp.status_code == 200:
    print(f"[OK] API is healthy: {resp.json()}")
else:
    print(f"[ERROR] API health check failed: {resp.status_code}")
    exit(1)

# Test 2: Test Vertex through brand entity strength endpoint
print("\n2. Testing Vertex through brand-entity-strength endpoint")
print("-" * 40)

test_data = {
    "brand_name": "AVEA",
    "domain": "avea-life.com",
    "vendor": "vertex",  # Use Vertex
    "model": "gemini-2.0-flash",
    "use_grounding": True,
    "include_reasoning": True
}

print(f"Request: {json.dumps(test_data, indent=2)}")
print("\nSending request...")

start = time.time()
resp = requests.post(
    f"{BASE_URL}/api/brand-entity-strength",
    json=test_data,
    timeout=60
)
elapsed = time.time() - start

if resp.status_code == 200:
    result = resp.json()
    print(f"\n[OK] Response received in {elapsed:.1f}s")
    print(f"Classification: {result.get('classification', {}).get('label')}")
    print(f"Confidence: {result.get('classification', {}).get('confidence')}%")
    print(f"Grounded: {result.get('grounded', False)}")
    
    # Check if citations are present and valid
    citations = result.get('citations', [])
    if citations:
        print(f"Citations: {len(citations)} found")
        # Verify all citations are dicts
        all_dicts = all(isinstance(c, dict) for c in citations)
        print(f"All citations are dicts: {all_dicts}")
        if not all_dicts:
            print("[ERROR] Some citations are not dictionaries!")
            for i, c in enumerate(citations):
                if not isinstance(c, dict):
                    print(f"  Citation {i}: {type(c).__name__}")
    else:
        print("No citations found (may not have triggered grounding)")
else:
    print(f"[ERROR] Request failed: {resp.status_code}")
    print(f"Response: {resp.text}")

# Test 3: Test through prompt tracking endpoint
print("\n3. Testing Vertex through prompt-tracking run endpoint")
print("-" * 40)

# Create a test template first
template_data = {
    "name": "Test Vertex Grounding",
    "prompt_text": "What are the top 3 longevity supplement brands?",
    "model_name": "gemini-2.0-flash",
    "countries": ["US"],
    "grounding_modes": ["web"],
    "prompt_type": "test"
}

print("Creating template...")
resp = requests.post(
    f"{BASE_URL}/api/prompt-tracking/templates",
    json=template_data
)

if resp.status_code in [200, 201]:
    template = resp.json()
    template_id = template["id"]
    print(f"[OK] Template created: {template_id}")
    
    # Now run the template
    run_data = {
        "template_id": template_id,
        "brand_name": "AVEA"
    }
    
    print(f"\nRunning template with brand: {run_data['brand_name']}")
    start = time.time()
    resp = requests.post(
        f"{BASE_URL}/api/prompt-tracking/run",
        json=run_data,
        timeout=90
    )
    elapsed = time.time() - start
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"\n[OK] Run completed in {elapsed:.1f}s")
        
        # Check results
        if "results" in result and result["results"]:
            for r in result["results"]:
                print(f"\nCountry: {r.get('country', 'N/A')}")
                print(f"Grounding: {r.get('grounding_mode', 'N/A')}")
                print(f"Mentioned: {r.get('mentioned', False)}")
                print(f"Confidence: {r.get('confidence_score', 0)}")
                
                # Check citations
                citations = r.get('grounding_metadata', {}).get('citations', [])
                if citations:
                    print(f"Citations: {len(citations)}")
                    all_dicts = all(isinstance(c, dict) for c in citations)
                    print(f"All citations are dicts: {all_dicts}")
    else:
        print(f"[ERROR] Run failed: {resp.status_code}")
        print(f"Response: {resp.text}")
else:
    print(f"[ERROR] Template creation failed: {resp.status_code}")
    print(f"Response: {resp.text}")

print("\n" + "=" * 60)
print("API INTEGRATION TEST COMPLETE")
print("=" * 60)