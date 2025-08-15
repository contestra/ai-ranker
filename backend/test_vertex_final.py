#!/usr/bin/env python
"""
Final test after ADC re-authentication
"""

import os
import google.auth

print("=" * 60)
print("FINAL VERTEX AI TEST")
print("=" * 60)

# Check which project ADC is using
try:
    credentials, project = google.auth.default()
    print(f"\nADC Project: {project}")
    
    if project != "contestra-ai":
        print("[ERROR] ADC is still using wrong project!")
        print("   Please run in PowerShell:")
        print("   gcloud config set project contestra-ai")
        print("   gcloud auth application-default login")
        exit(1)
    else:
        print("[OK] ADC is using correct project: contestra-ai")
except Exception as e:
    print(f"Error checking ADC: {e}")
    exit(1)

# Test Vertex AI
print("\n" + "-" * 60)
print("Testing Vertex AI...")
print("-" * 60)

try:
    from google import genai
    
    # Explicitly set project
    os.environ["GOOGLE_CLOUD_PROJECT"] = "contestra-ai"
    
    client = genai.Client(
        vertexai=True,
        project="contestra-ai",
        location="europe-west4"
    )
    
    print("\n1. Basic test:")
    response = client.models.generate_content(
        model="gemini-1.5-flash-002",
        contents="Say 'Vertex AI is working!'"
    )
    print(f"   [OK] {response.text.strip()}")
    
    print("\n2. Test with grounding (Google Search):")
    from google.genai import types
    config = types.GenerateContentConfig(
        temperature=0.0,
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )
    
    response = client.models.generate_content(
        model="gemini-1.5-flash-002",
        contents="What's the current weather in Tokyo? (Be brief)",
        config=config
    )
    print(f"   [OK] Grounded response: {response.text[:150]}...")
    
    print("\n" + "=" * 60)
    print("SUCCESS! VERTEX AI IS FULLY OPERATIONAL!")
    print("=" * 60)
    print("\nYour setup:")
    print("- Project: contestra-ai")
    print("- Region: europe-west4")
    print("- Grounding: Working with server-side execution")
    print("- Ready for production use!")
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    
    if "403" in str(e):
        print("\nPermission issue. Possible causes:")
        print("1. IAM role not fully propagated (wait 1-2 more minutes)")
        print("2. Need to re-run the ADC authentication")
    elif "404" in str(e):
        print("\nModel not found. The model name or region might be wrong.")
    else:
        print(f"\nUnexpected error: {str(e)[:200]}")