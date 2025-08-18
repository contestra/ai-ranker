#!/usr/bin/env python
"""
Test the frontend API with correct vendor names
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

print("=" * 60)
print("TESTING FRONTEND API WITH VERTEX")
print("=" * 60)

# Test 1: Health check
print("\n1. API Health Check")
print("-" * 40)
resp = requests.get(f"{BASE_URL}/api/health")
if resp.status_code == 200:
    health = resp.json()
    print(f"[OK] API healthy")
    print(f"  - Vertex status: {health['models']['vertex']['status']}")
    print(f"  - Vertex message: {health['models']['vertex']['message']}")
else:
    print(f"[ERROR] Health check failed: {resp.status_code}")

# Test 2: Brand entity strength with Google (Vertex)
print("\n2. Brand Entity Strength (Vertex/Gemini)")
print("-" * 40)

test_data = {
    "brand_name": "AVEA",
    "domain": "avea-life.com",
    "vendor": "google",  # Use "google" for Gemini/Vertex
    "model": "gemini-2.5-pro",
    "use_grounding": True,
    "include_reasoning": True
}

print(f"Testing brand: {test_data['brand_name']}")
print(f"Vendor: {test_data['vendor']} (Vertex AI)")
print(f"Model: {test_data['model']}")
print(f"Grounding: {test_data['use_grounding']}")

start = time.time()
try:
    resp = requests.post(
        f"{BASE_URL}/api/brand-entity-strength",
        json=test_data,
        timeout=60
    )
    elapsed = time.time() - start
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"\n[OK] Response in {elapsed:.1f}s")
        print(f"  Classification: {result.get('classification', {}).get('label')}")
        print(f"  Confidence: {result.get('classification', {}).get('confidence')}%")
        
        # Check if disambiguation was needed
        if result.get('classification', {}).get('disambiguation_needed'):
            print(f"  Disambiguation: Required")
            other_entities = result.get('classification', {}).get('other_entities_list', [])
            if other_entities:
                print(f"  Other entities: {', '.join(other_entities[:3])}")
        
        # Check grounding info if available
        if 'grounded' in result:
            print(f"  Grounded: {result['grounded']}")
            
        # Check citations if present
        if 'citations' in result:
            citations = result['citations']
            if citations:
                print(f"  Citations: {len(citations)} found")
                all_dicts = all(isinstance(c, dict) for c in citations)
                print(f"  Citations are dicts: {all_dicts}")
                if not all_dicts:
                    print("  [WARNING] Some citations are not dicts")
    else:
        print(f"[ERROR] Request failed: {resp.status_code}")
        print(f"Response: {resp.text[:500]}")
        
except requests.Timeout:
    print(f"[ERROR] Request timed out after 60s")
except Exception as e:
    print(f"[ERROR] Request failed: {e}")

# Test 3: Test with OpenAI GPT-5
print("\n3. Brand Entity Strength (OpenAI GPT-5)")
print("-" * 40)

test_data_openai = {
    "brand_name": "Tesla",
    "domain": "tesla.com",
    "vendor": "openai",
    "model": "gpt-5",
    "use_grounding": False,  # GPT-5 doesn't use grounding the same way
    "include_reasoning": True
}

print(f"Testing brand: {test_data_openai['brand_name']}")
print(f"Vendor: {test_data_openai['vendor']}")
print(f"Model: {test_data_openai['model']}")

start = time.time()
try:
    resp = requests.post(
        f"{BASE_URL}/api/brand-entity-strength",
        json=test_data_openai,
        timeout=90  # GPT-5 can be slow
    )
    elapsed = time.time() - start
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"\n[OK] Response in {elapsed:.1f}s")
        print(f"  Classification: {result.get('classification', {}).get('label')}")
        print(f"  Confidence: {result.get('classification', {}).get('confidence')}%")
    else:
        print(f"[ERROR] Request failed: {resp.status_code}")
        
except requests.Timeout:
    print(f"[ERROR] Request timed out after 90s (GPT-5 is slow)")
except Exception as e:
    print(f"[ERROR] Request failed: {e}")

print("\n" + "=" * 60)
print("FRONTEND API TEST COMPLETE")
print("Supported vendors: 'openai' (GPT-5) and 'google' (Gemini/Vertex)")
print("=" * 60)