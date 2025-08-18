"""
Test API with fixed data
"""

import requests
import json
import time

print("Testing fixed API call...")

# Get existing templates first
templates_response = requests.get("http://localhost:8000/api/prompt-tracking/templates?brand_name=AVEA")
templates = templates_response.json().get('templates', [])

if templates:
    # Use first template
    template = templates[0]
    print(f"Using template ID {template['id']}: {template['template_name']}")
    
    # Run it with brand_name included
    run_data = {
        "template_id": template['id'],
        "model_name": "gemini-2.5-pro",
        "brand_name": "AVEA"  # This was missing!
    }
    
    print("\nRunning template...")
    run_response = requests.post(
        "http://localhost:8000/api/prompt-tracking/run",
        json=run_data
    )
    
    print(f"Status: {run_response.status_code}")
    if run_response.status_code == 200:
        print("✅ SUCCESS! Template is running")
        result = run_response.json()
        print(f"Run ID: {result.get('run_id')}")
        print(f"Status: {result.get('status')}")
        
        # Wait a bit and check results
        if result.get('run_id'):
            time.sleep(5)
            print("\nChecking results...")
            results_response = requests.get(f"http://localhost:8000/api/prompt-tracking/results/{result['run_id']}")
            if results_response.status_code == 200:
                data = results_response.json()
                print(f"Brand mentioned: {data.get('brand_mentioned')}")
                print(f"Response preview: {data.get('model_response', '')[:200]}...")
    else:
        print(f"Error: {run_response.text}")
else:
    print("No templates found, creating one...")
    
    # Create a test template
    template_data = {
        "brand_name": "AVEA",
        "template_name": "Test Recognition",
        "prompt_text": "What is {brand_name}? Tell me about this brand.",
        "prompt_type": "recognition",
        "model_name": "gemini-2.5-pro",
        "countries": ["US"],
        "grounding_modes": ["none"]
    }
    
    create_response = requests.post(
        "http://localhost:8000/api/prompt-tracking/templates",
        json=template_data
    )
    
    if create_response.status_code == 200:
        print("Created template successfully")
        template = create_response.json()
        
        # Now run it
        run_data = {
            "template_id": template['id'],
            "model_name": "gemini-2.5-pro",
            "brand_name": "AVEA"
        }
        
        run_response = requests.post(
            "http://localhost:8000/api/prompt-tracking/run",
            json=run_data
        )
        
        print(f"Run status: {run_response.status_code}")
        if run_response.status_code == 200:
            print("✅ Template running successfully!")