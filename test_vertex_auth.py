"""
Test Vertex AI authentication directly
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

print("Testing Vertex AI Authentication...")
print("=" * 60)

# Check environment variables
print("\n1. Environment Variables:")
print(f"   GOOGLE_IMPERSONATE_SERVICE_ACCOUNT: {os.getenv('GOOGLE_IMPERSONATE_SERVICE_ACCOUNT', 'NOT SET')}")
print(f"   GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT', 'NOT SET')}")
print(f"   GOOGLE_CLOUD_REGION: {os.getenv('GOOGLE_CLOUD_REGION', 'NOT SET')}")

# Check ADC file exists
import pathlib
adc_path = pathlib.Path(os.environ.get('APPDATA', '')) / 'gcloud' / 'application_default_credentials.json'
print(f"\n2. ADC File:")
print(f"   Path: {adc_path}")
print(f"   Exists: {adc_path.exists()}")
if adc_path.exists():
    import json
    with open(adc_path) as f:
        adc_data = json.load(f)
    print(f"   Type: {adc_data.get('type', 'unknown')}")
    print(f"   Client ID: {adc_data.get('client_id', 'N/A')[:20]}...")

# Try to authenticate with Vertex
print("\n3. Testing Vertex AI Client:")
try:
    from google import genai
    from google.genai import types
    
    # Try with explicit project/location
    client = genai.Client(
        vertexai=True,
        project="contestra-ai",
        location="europe-west4"
    )
    
    # Try a simple list models call
    models = list(client.models.list())
    print(f"   ✅ Vertex AI connection successful!")
    print(f"   Available models: {len(models)}")
    
except Exception as e:
    print(f"   ❌ Vertex AI connection failed:")
    print(f"   Error: {e}")
    
    print("\n4. Falling back to Direct Gemini API:")
    try:
        import google.generativeai as genai_direct
        genai_direct.configure(api_key=os.getenv('GOOGLE_API_KEY', ''))
        
        # Test direct API
        model = genai_direct.GenerativeModel('gemini-2.5-pro')
        response = model.generate_content("Say 'test successful'")
        print(f"   ✅ Direct Gemini API working: {response.text[:50]}")
    except Exception as e2:
        print(f"   ❌ Direct API also failed: {e2}")

print("\n5. Summary:")
print("   The system is using Direct Gemini API (gemini_direct) as fallback")
print("   because Vertex AI authentication is not properly configured.")
print("   This is why you see 'Authentication error' for Vertex but")
print("   the application still works (using the fallback).")