"""Test if ADC is working"""
import json
import os
from pathlib import Path

adc_path = Path(os.environ['APPDATA']) / 'gcloud' / 'application_default_credentials.json'
print(f"ADC Path: {adc_path}")
print(f"Exists: {adc_path.exists()}")

if adc_path.exists():
    with open(adc_path) as f:
        data = json.load(f)
    print(f"Type: {data.get('type')}")
    print(f"Client ID: {data.get('client_id', '')[:30]}...")
    print(f"Quota Project ID: {data.get('quota_project_id', 'NOT SET')}")
    
    # Check if refresh token exists
    if 'refresh_token' in data:
        print("Refresh token: Present")
    else:
        print("Refresh token: MISSING")
        
    # Check file modification time
    import datetime
    mtime = datetime.datetime.fromtimestamp(adc_path.stat().st_mtime)
    print(f"Last modified: {mtime}")
    print(f"Minutes ago: {(datetime.datetime.now() - mtime).total_seconds() / 60:.1f}")