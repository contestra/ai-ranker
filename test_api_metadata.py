"""
Check what metadata the API returns
"""

import requests
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Get templates
print("Fetching templates...")
templates = requests.get("http://localhost:8000/api/prompt-tracking/templates?brand_name=AVEA")
print(f"Templates response keys: {templates.json().get('templates', [{}])[0].keys() if templates.json().get('templates') else 'No templates'}")

# Get runs
print("\nFetching runs...")
runs = requests.get("http://localhost:8000/api/prompt-tracking/runs?brand_name=AVEA&limit=5")
run_data = runs.json().get('runs', [])
if run_data:
    print(f"Run response keys: {run_data[0].keys()}")
    
    # Get detailed result for first run
    run_id = run_data[0]['id']
    print(f"\nFetching detailed result for run {run_id}...")
    result = requests.get(f"http://localhost:8000/api/prompt-tracking/results/{run_id}")
    if result.status_code == 200:
        data = result.json()
        print(f"Result keys: {data.keys()}")
        print(f"\nSample data:")
        for key in ['grounding_metadata', 'system_fingerprint', 'citations', 'temperature', 'seed', 'canonical_json']:
            if key in data:
                value = data[key]
                if isinstance(value, (dict, list)):
                    print(f"  {key}: {json.dumps(value, indent=2)[:200]}...")
                else:
                    print(f"  {key}: {value}")