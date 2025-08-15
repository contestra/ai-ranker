#!/usr/bin/env python
"""
Simple test to verify Vertex AI is working
"""

import os
os.environ["GOOGLE_CLOUD_PROJECT"] = "contestra-ai"

print("Testing Vertex AI connection...")
print("-" * 40)

# Test 1: Try with traditional Vertex AI SDK
print("\nTest 1: Traditional Vertex AI SDK")
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    
    # Try different regions
    for location in ["us-central1", "europe-west4", "europe-west1"]:
        print(f"\nTrying location: {location}")
        try:
            vertexai.init(project="contestra-ai", location=location)
            model = GenerativeModel("gemini-1.5-flash")  # Without -002 suffix
            response = model.generate_content("Say 'Hello'")
            print(f"  SUCCESS! Response: {response.text[:50]}")
            break
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg:
                print(f"  Permission denied in {location}")
            elif "404" in error_msg:
                print(f"  Model not found in {location}")
            else:
                print(f"  Error: {error_msg[:100]}")
except ImportError:
    print("  vertexai package not found")

# Test 2: Try with Google GenAI client
print("\n" + "-" * 40)
print("Test 2: Google GenAI Client")
try:
    from google import genai
    
    # Try different model names and regions
    models_to_try = [
        ("gemini-1.5-flash", "us-central1"),
        ("gemini-1.5-flash-002", "us-central1"),
        ("gemini-1.5-flash", "europe-west4"),
        ("gemini-1.5-flash-002", "europe-west4"),
        ("gemini-1.5-pro", "us-central1"),
        ("gemini-1.5-pro-002", "us-central1"),
    ]
    
    for model_name, location in models_to_try:
        print(f"\nTrying {model_name} in {location}")
        try:
            client = genai.Client(
                vertexai=True,
                project="contestra-ai",
                location=location
            )
            
            # Try without 'models/' prefix
            response = client.models.generate_content(
                model=model_name,  # Without models/ prefix
                contents="Say 'Hello'"
            )
            print(f"  SUCCESS! Response: {response.text[:50]}")
            print(f"  >>> Working config: model='{model_name}', location='{location}'")
            break
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg:
                print(f"  Permission denied")
            elif "404" in error_msg:
                print(f"  Model/endpoint not found")
            else:
                print(f"  Error: {error_msg[:80]}")
    
except ImportError:
    print("  google.genai package not found")

print("\n" + "=" * 40)
print("DIAGNOSIS:")
print("=" * 40)
print("If you see 'Permission denied' - API is enabled but needs IAM roles")
print("If you see 'Model not found' - Try a different region or model name")
print("If you see SUCCESS - Note the working configuration above")