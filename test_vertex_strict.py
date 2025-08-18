# test_vertex_strict.py
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from google import genai
from google.auth.transport.requests import Request
import google.auth

project = os.getenv("GOOGLE_CLOUD_PROJECT","contestra-ai")
location = os.getenv("GOOGLE_CLOUD_REGION","europe-west4")

print("=" * 60)
print("STRICT VERTEX AI TEST - NO FALLBACK")
print("=" * 60)

# Print identity
creds, quota_project = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
creds.refresh(Request())
print("\nAuthentication Status:")
print("  Credential type:", creds.__class__.__name__)
print("  Quota project   :", quota_project)
print("  Impersonated SA :", getattr(creds, "service_account_email", None))

# Strict: raise if not impersonated (optional but recommended)
if "Impersonated" not in creds.__class__.__name__:
    print("\n❌ ERROR: Not impersonating the service account!")
    print("   Current type:", creds.__class__.__name__)
    print("   Expected: ImpersonatedCredentials")
    raise SystemExit("Not impersonating the service account. Aborting.")

print("\n✅ Impersonation is working correctly!")

# Test Vertex AI client
print("\nTesting Vertex AI Client...")
try:
    client = genai.Client(vertexai=True, project=project, location=location)
    resp = client.models.generate_content(
        model="publishers/google/models/gemini-2.5-flash",
        contents="Say 'Vertex AI is working'",
    )
    
    response_text = resp.text if hasattr(resp, 'text') else str(resp)
    print("  Response:", response_text[:100])
    print("\n✅ SUCCESS: Vertex AI is working properly!")
    print("   No fallback to Direct Gemini API needed.")
    
except Exception as e:
    print(f"\n❌ FAILED: {e}")
    print("\nThis means Vertex AI is not accessible.")
    print("Check:")
    print("  1. Service account has roles/aiplatform.user")
    print("  2. Vertex AI API is enabled in project")
    print("  3. Region europe-west4 has Gemini models")
    raise