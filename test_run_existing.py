#!/usr/bin/env python
"""
Run existing template 14 to test grounding
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"
TEMPLATE_ID = 14  # Use existing template

print("=" * 60)
print("TESTING GROUNDING WITH EXISTING TEMPLATE")
print("=" * 60)

# Run the existing template
print(f"\nRunning template {TEMPLATE_ID} with grounding enabled")
run_data = {
    "template_id": TEMPLATE_ID,
    "brand_name": "Tesla"
}

print("  Sending request (this may take 30-60 seconds)...")
start = time.time()
resp = requests.post(
    f"{BASE_URL}/api/prompt-tracking/run",
    json=run_data,
    timeout=120
)
elapsed = time.time() - start

if resp.status_code == 200:
    result = resp.json()
    print(f"  [OK] Completed in {elapsed:.1f}s")
    
    # Check results
    if "results" in result and result["results"]:
        for r in result["results"]:
            country = r.get("country")
            grounding = r.get("grounding_mode")
            mentioned = r.get("mentioned")
            confidence = r.get("confidence_score", 0)
            
            # Check grounding metadata - this is the key part!
            grounding_meta = r.get("grounding_metadata", {})
            grounded_actual = grounding_meta.get("grounded", False)
            citations = grounding_meta.get("citations", [])
            queries = grounding_meta.get("web_search_queries", [])
            
            print(f"\n  Result for {country}/{grounding}:")
            print(f"    Brand mentioned: {mentioned}")
            print(f"    Confidence: {confidence}")
            print(f"    Grounding successful: {grounded_actual}")
            print(f"    Web queries made: {len(queries)}")
            print(f"    Citations found: {len(citations)}")
            
            if citations:
                # Verify citations are dicts
                all_dicts = all(isinstance(c, dict) for c in citations)
                print(f"    Citations are dicts: {all_dicts}")
                
                # Show first citation
                if citations and isinstance(citations[0], dict):
                    first = citations[0]
                    print(f"    First citation keys: {list(first.keys())[:5]}")
                    if "uri" in first:
                        uri = first["uri"]
                        print(f"    First URI: {uri[:80]}...")
                    if "title" in first:
                        print(f"    First title: {first['title']}")
            
            # Check the actual response
            response_text = r.get("response", "")
            if response_text:
                print(f"    Response preview: {response_text[:150]}...")
    else:
        print("  No results found in response")
else:
    print(f"  [FAIL] Status: {resp.status_code}")
    print(f"  Response: {resp.text[:500]}")

print("\n" + "=" * 60)
print("GROUNDING TEST COMPLETE")
print("=" * 60)