"""
Test API directly to see exact errors
"""

import requests
import json

# Test template creation
print("Testing template creation...")

template_data = {
    "brand_name": "AVEA",
    "template_name": "recognition_US_none_1",
    "prompt_text": "What is {brand_name}?",
    "prompt_type": "recognition",
    "model_name": "gemini-2.5-pro",
    "countries": ["US"],
    "grounding_modes": ["none"]
}

response = requests.post(
    "http://localhost:8000/api/prompt-tracking/templates",
    json=template_data
)

print(f"Status: {response.status_code}")
if response.status_code != 200:
    print(f"Error: {response.text}")
else:
    print("Success!")
    template = response.json()
    print(f"Created template ID: {template.get('id')}")
    
    # Now try to run it
    print("\nTesting run...")
    run_data = {
        "template_id": template['id'],
        "model_name": "gemini-2.5-pro"
    }
    
    run_response = requests.post(
        "http://localhost:8000/api/prompt-tracking/run",
        json=run_data
    )
    
    print(f"Run status: {run_response.status_code}")
    if run_response.status_code != 200:
        print(f"Run error: {run_response.text}")
    else:
        print("Run successful!")
        print(json.dumps(run_response.json(), indent=2))