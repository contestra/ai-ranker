#!/usr/bin/env python
"""
Test if Vertex AI API is responding at all
"""

import os
os.environ["GOOGLE_CLOUD_PROJECT"] = "contestra-ai"

print("Testing Vertex AI API availability...")
print("-" * 50)

try:
    from google.cloud import aiplatform
    
    # Initialize with explicit project and location
    aiplatform.init(
        project="contestra-ai",
        location="us-central1"
    )
    
    print("AI Platform initialized")
    
    # Try to list models (this should work even without specific model access)
    print("\nTrying to list available models...")
    
    # This might fail but will give us more info
    models = aiplatform.Model.list(limit=1)
    print(f"API is responding. Found {len(models)} models.")
    
except Exception as e:
    error_str = str(e)
    print(f"\nError: {error_str[:500]}")
    
    if "403" in error_str:
        print("\nPermissions issue - but API is responding")
    elif "404" in error_str:
        print("\nAPI endpoint not found - might need different region")
    elif "ADC" in error_str or "credentials" in error_str.lower():
        print("\nAuthentication issue")
    else:
        print("\nCheck if Vertex AI API is enabled in console")

print("\n" + "-" * 50)
print("Checking API enablement directly...")

try:
    import requests
    
    # Try a simple API call to check if the API is enabled
    url = "https://aiplatform.googleapis.com/v1/projects/contestra-ai/locations/us-central1"
    
    # Get access token from ADC
    from google.auth.transport.requests import Request
    from google.auth import default
    
    credentials, project = default()
    credentials.refresh(Request())
    
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    print(f"API Response Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✓ Vertex AI API is enabled and responding")
    elif response.status_code == 403:
        print("✓ API is enabled but permissions not ready")
    elif response.status_code == 404:
        print("✗ API might not be enabled or wrong endpoint")
    
    print(f"Response: {response.text[:200]}...")
    
except Exception as e:
    print(f"Could not check API directly: {e}")