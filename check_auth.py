import os
import json
from pathlib import Path

# Check for existing ADC
adc_path = Path(os.environ.get('APPDATA', '')) / 'gcloud' / 'application_default_credentials.json'
print(f"ADC path: {adc_path}")
print(f"ADC exists: {adc_path.exists()}")

if adc_path.exists():
    with open(adc_path) as f:
        data = json.load(f)
    print(f"ADC type: {data.get('type', 'unknown')}")
    print(f"Client ID: {data.get('client_id', 'N/A')[:30]}..." if data.get('client_id') else 'N/A')
    print(f"Expiry: {data.get('expiry', 'N/A')}")
    if 'refresh_token' in data:
        print("Has refresh token: Yes")

# Check for service account key
sa_key = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
print(f"\nGOOGLE_APPLICATION_CREDENTIALS: {sa_key}")
if sa_key and os.path.exists(sa_key):
    with open(sa_key) as f:
        sa_data = json.load(f)
    print(f"Service account: {sa_data.get('client_email', 'N/A')}")

# Check default auth
print("\nTrying google.auth.default()...")
try:
    from google.auth import default
    creds, project = default()
    print(f"Default auth type: {type(creds).__name__}")
    print(f"Project: {project}")
    
    # Try to refresh
    from google.auth.transport.requests import Request
    try:
        creds.refresh(Request())
        print("Auth refresh: SUCCESS")
    except Exception as e:
        print(f"Auth refresh: FAILED - {e}")
except Exception as e:
    print(f"Default auth failed: {e}")