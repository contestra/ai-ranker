#!/usr/bin/env python
"""
Manually fix ADC by updating the credentials file
"""

import os
import json
import shutil
from pathlib import Path

print("=" * 60)
print("FIXING ADC CREDENTIALS MANUALLY")
print("=" * 60)

# Find the ADC credentials file
adc_path = Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
adc_path_alt = Path(os.environ.get("APPDATA", "")) / "gcloud" / "application_default_credentials.json"

# Check which path exists
if adc_path.exists():
    creds_file = adc_path
elif adc_path_alt.exists():
    creds_file = adc_path_alt
else:
    print(f"\n[ERROR] ADC credentials file not found!")
    print(f"Checked: {adc_path}")
    print(f"Checked: {adc_path_alt}")
    print("\nSolution: You need to install Google Cloud SDK:")
    print("1. Download from: https://cloud.google.com/sdk/docs/install")
    print("2. After installing, run: gcloud auth application-default login")
    exit(1)

print(f"\nFound ADC file: {creds_file}")

# Backup the original
backup_file = creds_file.with_suffix(".json.backup")
shutil.copy2(creds_file, backup_file)
print(f"Created backup: {backup_file}")

# Read and update the credentials
try:
    with open(creds_file, 'r') as f:
        creds = json.load(f)
    
    print(f"\nCurrent quota project: {creds.get('quota_project_id', 'NOT SET')}")
    
    # Update the quota project
    creds['quota_project_id'] = 'contestra-ai'
    
    # Write back
    with open(creds_file, 'w') as f:
        json.dump(creds, f, indent=2)
    
    print(f"Updated quota project to: contestra-ai")
    print("\n[SUCCESS] ADC manually updated!")
    
except Exception as e:
    print(f"\n[ERROR] Failed to update credentials: {e}")
    print("Restoring backup...")
    shutil.copy2(backup_file, creds_file)
    exit(1)

# Test the fix
print("\n" + "-" * 60)
print("Testing the fix...")
print("-" * 60)

import google.auth
credentials, project = google.auth.default()
print(f"ADC Project: {project}")

if project == "contestra-ai":
    print("[SUCCESS] ADC is now using contestra-ai!")
else:
    print(f"[WARNING] ADC still shows: {project}")
    print("But quota_project_id is set to contestra-ai")
    print("This should still work!")

# Final test with Vertex
print("\n" + "-" * 60)
print("Testing Vertex AI...")
print("-" * 60)

os.environ["GOOGLE_CLOUD_PROJECT"] = "contestra-ai"

try:
    from google import genai
    client = genai.Client(
        vertexai=True,
        project="contestra-ai",
        location="europe-west4"
    )
    
    response = client.models.generate_content(
        model="gemini-1.5-flash-002",
        contents="Say 'Hello from Vertex AI!'"
    )
    print(f"[SUCCESS] Vertex response: {response.text.strip()}")
    print("\n" + "=" * 60)
    print("VERTEX AI IS WORKING!")
    print("=" * 60)
    
except Exception as e:
    print(f"[ERROR] {str(e)[:200]}")
    
    if "403" in str(e):
        print("\nThis is still a permission issue.")
        print("Your ADC is fixed, but the IAM role may not have propagated.")
        print("Wait 2-3 more minutes and try again.")
    else:
        print("\nUnexpected error. You may need to install gcloud SDK.")