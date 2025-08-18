#!/usr/bin/env python
"""
Simple test to verify Templates work with Vertex grounding
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

print("=" * 60)
print("SIMPLE TEMPLATES TEST WITH VERTEX GROUNDING")
print("=" * 60)

# Test 1: Create a simple template with Gemini and grounding
print("\n1. Creating template with Gemini 2.0 Flash (working model)")
template_data = {
    "brand_name": "Tesla",  # Well-known brand for testing
    "template_name": f"Test Gemini Grounding {int(time.time())}",  # Unique name
    "prompt_text": "What are the top electric vehicle companies? List the top 5.",
    "model_name": "gemini-2.0-flash",  # Use the working model
    "countries": ["US"],
    "grounding_modes": ["web"],
    "prompt_type": "test"
}

resp = requests.post(f"{BASE_URL}/api/prompt-tracking/templates", json=template_data)
if resp.status_code in [200, 201]:
    template = resp.json()
    template_id = template["id"]
    print(f"  [OK] Template created: ID={template_id}")
else:
    print(f"  [FAIL] Status: {resp.status_code}")
    print(f"  Response: {resp.text[:300]}")
    exit(1)

# Test 2: Run the template
print("\n2. Running template with grounding enabled")
run_data = {
    "template_id": template_id,
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
            
            # Check the actual response
            response_text = r.get("response", "")
            if response_text:
                print(f"    Response preview: {response_text[:150]}...")
else:
    print(f"  [FAIL] Status: {resp.status_code}")
    print(f"  Response: {resp.text[:500]}")

print("\n" + "=" * 60)
print("GROUNDING TEST COMPLETE")
print("=" * 60)
print("\nKey Points:")
print("- Used gemini-2.0-flash (known working model)")
print("- Grounding mode: web")
print("- Check grounding_metadata.grounded field")
print("- Check citations are dictionaries")
print("- Citations built from grounding_chunks")