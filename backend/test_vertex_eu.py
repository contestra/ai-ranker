#!/usr/bin/env python
"""
Test with europe-west4 models
"""

import os
os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)
os.environ['GOOGLE_CLOUD_PROJECT'] = 'contestra-ai'

from google import genai
from google.genai.types import GenerateContentConfig

print("Testing europe-west4 with gemini-2.0-flash...")

loc = "europe-west4"
MODEL = "publishers/google/models/gemini-2.0-flash"  # Model that's actually in EU

try:
    client = genai.Client(vertexai=True, project="contestra-ai", location=loc)
    resp = client.models.generate_content(
        model=MODEL,
        contents="Say OK",
        config=GenerateContentConfig(temperature=0),
    )
    print(f"SUCCESS: {resp.text}")
except Exception as e:
    print(f"ERROR: {e}")

print("\nTesting without publisher prefix...")
MODEL = "gemini-2.0-flash"  # Try without prefix

try:
    client = genai.Client(vertexai=True, project="contestra-ai", location=loc)
    resp = client.models.generate_content(
        model=MODEL,
        contents="Say OK",
        config=GenerateContentConfig(temperature=0),
    )
    print(f"SUCCESS: {resp.text}")
except Exception as e:
    print(f"ERROR: {e}")

print("\nTesting us-central1 with gemini-pro...")
loc = "us-central1"
MODEL = "publishers/google/models/gemini-pro"  # Try an older model

try:
    client = genai.Client(vertexai=True, project="contestra-ai", location=loc)
    resp = client.models.generate_content(
        model=MODEL,
        contents="Say OK",
        config=GenerateContentConfig(temperature=0),
    )
    print(f"SUCCESS: {resp.text}")
except Exception as e:
    print(f"ERROR: {e}")