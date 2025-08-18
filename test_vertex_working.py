"""
Test if Vertex AI is now working properly
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Set environment variables for this process
os.environ['GOOGLE_IMPERSONATE_SERVICE_ACCOUNT'] = 'vertex-runner@contestra-ai.iam.gserviceaccount.com'
os.environ['GOOGLE_CLOUD_PROJECT'] = 'contestra-ai'
os.environ['GOOGLE_CLOUD_REGION'] = 'europe-west4'
os.environ['GOOGLE_CLOUD_QUOTA_PROJECT'] = 'contestra-ai'

print("Testing Vertex AI with proper configuration...")
print("=" * 60)

# Check environment
print("\n1. Environment Variables Set:")
print(f"   GOOGLE_IMPERSONATE_SERVICE_ACCOUNT: {os.getenv('GOOGLE_IMPERSONATE_SERVICE_ACCOUNT')}")
print(f"   GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
print(f"   GOOGLE_CLOUD_REGION: {os.getenv('GOOGLE_CLOUD_REGION')}")

# Check ADC
import pathlib
import json
adc_path = pathlib.Path(os.environ.get('APPDATA', '')) / 'gcloud' / 'application_default_credentials.json'
if adc_path.exists():
    with open(adc_path) as f:
        adc_data = json.load(f)
    print(f"\n2. ADC Configuration:")
    print(f"   Quota Project: {adc_data.get('quota_project_id', 'NOT SET')}")
    print(f"   Type: {adc_data.get('type')}")

# Test authentication
print("\n3. Testing Authentication:")
try:
    import google.auth
    creds, project = google.auth.default()
    print(f"   Default project: {project}")
    print(f"   Credential type: {creds.__class__.__name__}")
    
    # Check if impersonation is working
    if hasattr(creds, 'service_account_email'):
        print(f"   Service account: {creds.service_account_email}")
    elif hasattr(creds, '_service_account_email'):
        print(f"   Service account: {creds._service_account_email}")
    else:
        print(f"   Service account: Not using impersonation")
except Exception as e:
    print(f"   Error getting credentials: {e}")

# Test Vertex AI client
print("\n4. Testing Vertex AI Client:")
try:
    from google import genai
    from google.genai import types
    
    client = genai.Client(
        vertexai=True,
        project=os.getenv('GOOGLE_CLOUD_PROJECT', 'contestra-ai'),
        location=os.getenv('GOOGLE_CLOUD_REGION', 'europe-west4')
    )
    
    # Try to list models
    print("   Attempting to list models...")
    models = list(client.models.list())
    print(f"   ✅ SUCCESS! Vertex AI is working properly")
    print(f"   Found {len(models)} model(s)")
    
    # Try a simple generation
    print("\n5. Testing Generation:")
    config = types.GenerateContentConfig(
        temperature=0.0,
        top_p=1.0,
        max_output_tokens=50
    )
    
    response = client.models.generate_content(
        model="publishers/google/models/gemini-2.5-flash",
        contents="Say 'Vertex AI is working'",
        config=config
    )
    print(f"   Response: {response.text}")
    print(f"   ✅ Vertex AI generation successful!")
    
except Exception as e:
    print(f"   ❌ Vertex AI failed: {e}")
    print(f"\n   Error details: {type(e).__name__}: {str(e)}")
    
    # Check if it's an authentication error
    if "reauthentication" in str(e).lower():
        print("\n   This is an authentication issue. The ADC might need refreshing.")
    elif "quota" in str(e).lower():
        print("\n   This might be a quota or project configuration issue.")

print("\n" + "=" * 60)
print("Summary:")
if 'models' in locals():
    print("✅ Vertex AI is now working correctly!")
    print("The system should no longer fall back to Direct Gemini API.")
else:
    print("❌ Vertex AI is still not working.")
    print("The system will continue using the fallback Direct Gemini API.")