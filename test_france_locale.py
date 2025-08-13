"""Test France locale with improved probe and parser"""
import requests
import json

# Test with Gemini
response = requests.post(
    'http://localhost:8000/api/countries/test',
    json={
        'country_code': 'FR',
        'model': 'gemini'
    }
)

print(f"Status: {response.status_code}")
if response.ok:
    data = response.json()
    print(f"\nOverall Status: {data['overall_status']}")
    print(f"Test Date: {data['test_date']}")
    
    print("\nProbe Results:")
    for key, result in data.get('probes', {}).items():
        print(f"\n{key.upper()}:")
        print(f"  Question: {result.get('question', 'N/A')}")
        print(f"  Expected: {result.get('expected', 'N/A')}")
        print(f"  Found: {result.get('found', 'N/A')}")
        print(f"  Passed: {'✓' if result.get('passed') else '✗'}")
        if 'response' in result:
            print(f"  Raw Response: {result['response'][:100]}...")
else:
    print(f"Error: {response.text}")