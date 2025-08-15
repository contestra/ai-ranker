#!/usr/bin/env python
"""
Check which Gemini models are available in different regions
"""

import os
# Remove any old GOOGLE_APPLICATION_CREDENTIALS
os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)

from google import genai

print("=" * 60)
print("CHECKING VERTEX AI MODEL AVAILABILITY")
print("=" * 60)

regions = ["europe-west4", "us-central1", "us-east1"]

for region in regions:
    print(f"\n{region}:")
    print("-" * 40)
    try:
        client = genai.Client(
            vertexai=True, 
            project="contestra-ai", 
            location=region
        )
        
        models = [m.name for m in client.models.list() if "gemini" in m.name.lower()]
        
        if models:
            print(f"[SUCCESS] Found {len(models)} Gemini models:")
            for model in models[:5]:  # Show first 5
                print(f"   - {model}")
        else:
            print("[ERROR] No Gemini models found")
            
    except Exception as e:
        error_str = str(e)
        if "403" in error_str:
            print("[ERROR] Permission denied (IAM not ready)")
        elif "404" in error_str:
            print("[ERROR] Region/endpoint not found")
        else:
            print(f"[ERROR] Error: {error_str[:100]}")

print("\n" + "=" * 60)
print("TESTING SIMPLE GENERATION")
print("=" * 60)

# Try us-central1 with the exact model name
try:
    print("\nTrying us-central1 with gemini-1.5-flash-002...")
    client = genai.Client(
        vertexai=True,
        project="contestra-ai",
        location="us-central1"
    )
    
    from google.genai.types import GenerateContentConfig
    
    resp = client.models.generate_content(
        model="gemini-1.5-flash-002",
        contents="Say OK",
        config=GenerateContentConfig(temperature=0)
    )
    
    print(f"[SUCCESS] SUCCESS: {resp.text}")
    
except Exception as e:
    print(f"[ERROR] Failed: {e}")

# Try europe-west4
try:
    print("\nTrying europe-west4 with gemini-1.5-pro-002...")
    client = genai.Client(
        vertexai=True,
        project="contestra-ai",
        location="europe-west4"
    )
    
    resp = client.models.generate_content(
        model="gemini-1.5-pro-002",
        contents="Say OK",
        config=GenerateContentConfig(temperature=0)
    )
    
    print(f"[SUCCESS] SUCCESS: {resp.text}")
    
except Exception as e:
    print(f"[ERROR] Failed: {e}")