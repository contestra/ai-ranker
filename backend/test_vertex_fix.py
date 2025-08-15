#!/usr/bin/env python
"""
Fix Vertex AI - use correct model identifiers
"""

import os
os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)
os.environ['GOOGLE_CLOUD_PROJECT'] = 'contestra-ai'

print("=" * 60)
print("STEP 1: Check exact model names per region")
print("=" * 60)

from google import genai

for loc in ("europe-west4", "us-central1"):
    c = genai.Client(vertexai=True, project="contestra-ai", location=loc)
    names = [m.name for m in c.models.list() if "gemini" in m.name]
    print(f"\n{loc}:")
    for name in names[:8]:
        print(f"  - {name}")

print("\n" + "=" * 60)
print("STEP 2: Test ungrounded with CORRECT publisher path")
print("=" * 60)

from google.genai.types import GenerateContentConfig

# Use us-central1 since it has gemini-1.5-flash-002
loc = "us-central1"
MODEL = "publishers/google/models/gemini-1.5-flash-002"  # Full publisher path

print(f"\nLocation: {loc}")
print(f"Model: {MODEL}")

try:
    client = genai.Client(vertexai=True, project="contestra-ai", location=loc)
    resp = client.models.generate_content(
        model=MODEL,
        contents="Say OK",
        config=GenerateContentConfig(temperature=0),
    )
    print(f"SUCCESS: {resp.text}")
except Exception as e:
    import traceback
    print("ERROR:")
    traceback.print_exc()
    # Print all error attributes
    for attr in ("status_code", "response", "errors", "message"):
        if hasattr(e, attr):
            print(f"  {attr}: {getattr(e, attr)}")

print("\n" + "=" * 60)
print("STEP 3: Test grounded with CORRECT publisher path")
print("=" * 60)

from google.genai.types import Tool, GoogleSearch

try:
    client = genai.Client(vertexai=True, project="contestra-ai", location=loc)
    resp = client.models.generate_content(
        model=MODEL,
        contents="What's the standard VAT rate in the UK?",
        config=GenerateContentConfig(
            tools=[Tool(google_search=GoogleSearch())],
            temperature=0,
        ),
    )
    print(f"SUCCESS: {resp.text}")
except Exception as e:
    import traceback
    print("ERROR:")
    traceback.print_exc()
    for attr in ("status_code", "response", "errors", "message"):
        if hasattr(e, attr):
            print(f"  {attr}: {getattr(e, attr)}")