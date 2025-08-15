#!/usr/bin/env python
"""
Direct Vertex AI test bypassing google.auth.default()
"""

import os

# Force the project
os.environ["GOOGLE_CLOUD_PROJECT"] = "contestra-ai"
os.environ["GCLOUD_PROJECT"] = "contestra-ai"

print("=" * 60)
print("DIRECT VERTEX AI TEST")
print("=" * 60)

print(f"\nEnvironment variables set:")
print(f"GOOGLE_CLOUD_PROJECT: {os.environ.get('GOOGLE_CLOUD_PROJECT')}")
print(f"GCLOUD_PROJECT: {os.environ.get('GCLOUD_PROJECT')}")

print("\n" + "-" * 60)
print("Testing with Google GenAI Client...")
print("-" * 60)

try:
    from google import genai
    
    # Create client with explicit project
    client = genai.Client(
        vertexai=True,
        project="contestra-ai",
        location="us-central1"  # Try US region
    )
    
    print("Client created successfully")
    print("Sending test request...")
    
    response = client.models.generate_content(
        model="gemini-1.5-flash-002",
        contents="Say 'Vertex AI is working!'"
    )
    
    print(f"\n[SUCCESS] Response: {response.text.strip()}")
    
    # Test with grounding
    print("\n" + "-" * 60)
    print("Testing with grounding...")
    print("-" * 60)
    
    from google.genai import types
    config = types.GenerateContentConfig(
        temperature=0.0,
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )
    
    response = client.models.generate_content(
        model="gemini-1.5-flash-002",
        contents="What's the current weather in Tokyo?",
        config=config
    )
    
    print(f"[SUCCESS] Grounded response: {response.text[:150]}...")
    
    print("\n" + "=" * 60)
    print("VERTEX AI IS FULLY OPERATIONAL!")
    print("=" * 60)
    print("\nYour configuration:")
    print("- Project: contestra-ai")
    print("- Location: us-central1")
    print("- Grounding: Working!")
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    
    if "403" in str(e):
        print("\nThis is still a permissions issue.")
        print("The ADC is correct, but IAM permissions may not have propagated.")
        print("Wait a few more minutes or check IAM roles.")
    else:
        print(f"\nFull error: {str(e)}")