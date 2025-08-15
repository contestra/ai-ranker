#!/usr/bin/env python
"""
Complete Vertex AI diagnostic - finds and fixes the issue
"""

import os
import json
import subprocess
from pathlib import Path

print("=" * 60)
print("VERTEX AI COMPLETE DIAGNOSTIC")
print("=" * 60)

# Force project
os.environ["GOOGLE_CLOUD_PROJECT"] = "contestra-ai"

# Step 1: Check ADC file
print("\n1. CHECKING ADC CREDENTIALS...")
print("-" * 40)

adc_paths = [
    Path(os.environ.get("APPDATA", "")) / "gcloud" / "application_default_credentials.json",
    Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
]

adc_file = None
for path in adc_paths:
    if path.exists():
        adc_file = path
        break

if adc_file:
    print(f"Found ADC file: {adc_file}")
    with open(adc_file) as f:
        creds = json.load(f)
    print(f"Quota project: {creds.get('quota_project_id', 'NOT SET')}")
    print(f"Type: {creds.get('type')}")
    
    if creds.get('quota_project_id') != 'contestra-ai':
        print("\n[WARNING] ADC quota project is not contestra-ai!")
else:
    print("[ERROR] No ADC file found!")
    print("You need to run: gcloud auth application-default login")

# Step 2: Test REST API directly
print("\n2. TESTING REST API ACCESS...")
print("-" * 40)

try:
    import google.auth
    from google.auth.transport.requests import Request
    import requests
    
    # Get credentials
    credentials, project = google.auth.default()
    print(f"Using project from ADC: {project}")
    
    # Refresh token
    auth_req = Request()
    credentials.refresh(auth_req)
    
    # Test US region
    location = "us-central1"
    url = f"https://{location}-aiplatform.googleapis.com/v1/projects/contestra-ai/locations/{location}/publishers/google/models"
    
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json"
    }
    
    print(f"Testing {location}...")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        models = response.json().get('models', [])
        print(f"[SUCCESS] Found {len(models)} models in {location}")
        if models:
            print("Sample models available:")
            for model in models[:3]:
                print(f"  - {model.get('name', 'unknown')}")
    elif response.status_code == 403:
        print(f"[ERROR] Permission denied: {response.text[:200]}")
        print("\nThis means IAM roles haven't propagated yet.")
    else:
        print(f"[ERROR] Status {response.status_code}: {response.text[:200]}")
        
except Exception as e:
    print(f"[ERROR] {e}")

# Step 3: Test with Python SDKs
print("\n3. TESTING PYTHON SDKs...")
print("-" * 40)

# Test traditional Vertex AI
print("\nTesting traditional Vertex AI SDK...")
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    
    vertexai.init(project="contestra-ai", location="us-central1")
    model = GenerativeModel("gemini-1.5-flash-002")
    response = model.generate_content("Say 'OK'")
    print(f"[SUCCESS] Vertex AI SDK works! Response: {response.text[:50]}")
    
except Exception as e:
    error_str = str(e)
    if "403" in error_str and "PERMISSION_DENIED" in error_str:
        print("[ERROR] Permission denied - IAM roles not propagated")
    else:
        print(f"[ERROR] {error_str[:200]}")

# Test new GenAI client
print("\nTesting Google GenAI client...")
try:
    from google import genai
    
    client = genai.Client(
        vertexai=True,
        project="contestra-ai",
        location="us-central1"
    )
    
    response = client.models.generate_content(
        model="gemini-1.5-flash-002",
        contents="Say 'OK'"
    )
    print(f"[SUCCESS] GenAI client works! Response: {response.text[:50]}")
    
except Exception as e:
    error_str = str(e)
    if "403" in error_str:
        print("[ERROR] Permission denied - IAM roles not propagated")
    else:
        print(f"[ERROR] {error_str[:200]}")

# Step 4: Diagnosis
print("\n" + "=" * 60)
print("DIAGNOSIS")
print("=" * 60)

if adc_file and creds.get('quota_project_id') == 'contestra-ai':
    print("✓ ADC is configured correctly for contestra-ai")
else:
    print("✗ ADC needs to be reconfigured")
    print("  Run: gcloud auth application-default login")

print("\nIf you're seeing 403 PERMISSION_DENIED errors:")
print("1. Your Owner role should include all permissions")
print("2. But IAM can take up to 30 minutes for new projects")
print("3. Try again in a few minutes")
print("\nAlternative: Use direct Gemini API (already working!)")