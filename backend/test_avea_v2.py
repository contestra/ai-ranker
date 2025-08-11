#!/usr/bin/env python3
"""
Quick test of AVEA with v2 endpoint
"""

import requests
import json
import sys

# Force UTF-8 output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("Testing AVEA with two-step approach...")
print("-" * 40)

# Test the v2 endpoint
response = requests.post(
    'http://localhost:8000/api/brand-entity-strength-v2',
    json={
        'brand_name': 'AVEA',
        'domain': 'avea-life.com',
        'information_vendor': 'google',
        'classifier_vendor': 'openai'
    },
    timeout=60  # 60 second timeout
)

if response.ok:
    data = response.json()
    classification = data.get('classification', {})
    
    print(f"✅ SUCCESS!")
    print(f"\nClassification: {classification.get('label')}")
    print(f"Confidence: {classification.get('confidence')}%")
    print(f"Methodology: {classification.get('methodology')}")
    
    # Show stats
    analysis = classification.get('classifier_analysis', {})
    print(f"\nFacts Found: {analysis.get('specific_facts', 0)}")
    print(f"Generic Claims: {analysis.get('generic_claims', 0)}")
    print(f"Multiple Entities: {analysis.get('multiple_entities', False)}")
    
    # Show first part of natural response
    natural = classification.get('natural_response', '')
    if natural:
        print(f"\nNatural Response Preview:")
        print(natural[:300] + "..." if len(natural) > 300 else natural)
    
    # Save full response for inspection
    with open('avea_v2_response.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Full response saved to avea_v2_response.json")
else:
    print(f"❌ ERROR {response.status_code}")
    print(response.text)