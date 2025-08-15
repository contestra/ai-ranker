#!/usr/bin/env python
"""
Test Vertex AI with correct configuration
"""

import os
# Remove any old GOOGLE_APPLICATION_CREDENTIALS
os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)
# Explicitly set the project
os.environ['GOOGLE_CLOUD_PROJECT'] = 'contestra-ai'

print("=" * 60)
print("VERTEX AI CORRECT CONFIGURATION TEST")
print("=" * 60)

# First verify ADC
import google.auth
creds, proj = google.auth.default()
print(f"\n1. ADC Project: {proj}")
if proj != "contestra-ai":
    print(f"[WARNING] ADC project is {proj}, explicitly setting to contestra-ai")
    proj = "contestra-ai"

# Try to list models
from google import genai

print("\n2. Testing model listing in europe-west4...")
try:
    client = genai.Client(
        vertexai=True,
        project="contestra-ai",
        location="europe-west4"
    )
    
    available = [m.name for m in client.models.list() if "gemini" in m.name.lower()]
    if available:
        print(f"[SUCCESS] Found {len(available)} Gemini models:")
        for model in available[:5]:
            print(f"   - {model}")
    else:
        print("[WARNING] No Gemini models found in europe-west4")
        
except Exception as e:
    print(f"[ERROR] {e}")

print("\n3. Testing model listing in us-central1...")
try:
    client = genai.Client(
        vertexai=True,
        project="contestra-ai",
        location="us-central1"
    )
    
    available = [m.name for m in client.models.list() if "gemini" in m.name.lower()]
    if available:
        print(f"[SUCCESS] Found {len(available)} Gemini models:")
        for model in available[:5]:
            print(f"   - {model}")
    else:
        print("[WARNING] No Gemini models found in us-central1")
        
except Exception as e:
    print(f"[ERROR] {e}")

print("\n4. Testing simple generation with us-central1...")
try:
    from google.genai.types import GenerateContentConfig
    
    client = genai.Client(
        vertexai=True,
        project="contestra-ai",
        location="us-central1"
    )
    
    resp = client.models.generate_content(
        model="gemini-1.5-flash-002",  # Try without full path
        contents="Say OK",
        config=GenerateContentConfig(temperature=0)
    )
    
    print(f"[SUCCESS] Basic generation works: {resp.text}")
    
except Exception as e:
    error_str = str(e)
    print(f"[ERROR] Full error: {error_str}")

print("\n5. Testing grounded generation with us-central1...")
try:
    from google.genai.types import Tool, GoogleSearch, GenerateContentConfig
    
    client = genai.Client(
        vertexai=True,
        project="contestra-ai",
        location="us-central1"
    )
    
    resp = client.models.generate_content(
        model="gemini-1.5-flash-002",  # Try without full path
        contents="What's the standard VAT rate in the UK? Answer briefly.",
        config=GenerateContentConfig(
            tools=[Tool(google_search=GoogleSearch())],  # Vertex grounding
            temperature=0,
        )
    )
    
    print(f"[SUCCESS] Grounded generation works: {resp.text}")
    
except Exception as e:
    error_str = str(e)
    print(f"[ERROR] Full error: {error_str}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("""
If you see 403 errors: IAM permissions are still propagating
If you see 404 errors: Wrong region or model name
If you see success: Vertex is ready to use!
""")