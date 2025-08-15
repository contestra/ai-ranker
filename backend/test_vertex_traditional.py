#!/usr/bin/env python
"""
Test with traditional Vertex AI SDK
"""

import os
os.environ["GOOGLE_CLOUD_PROJECT"] = "contestra-ai"

print("Testing traditional Vertex AI SDK...")
print("-" * 50)

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    
    # Initialize Vertex AI
    vertexai.init(
        project="contestra-ai",
        location="us-central1"
    )
    
    print("Vertex AI initialized")
    print("Creating model...")
    
    # Create model
    model = GenerativeModel("gemini-1.5-flash")
    
    print("Sending request...")
    
    # Generate content
    response = model.generate_content("Say 'Vertex AI works!'")
    
    print(f"\n[SUCCESS] Response: {response.text}")
    print("\nVertex AI is working!")
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    
    error_str = str(e)
    if "403" in error_str and "PERMISSION_DENIED" in error_str:
        print("\nPermissions issue - IAM role not yet active")
        print("This can take up to 15 minutes for new projects")
    elif "404" in error_str:
        print("\nModel or endpoint not found")
    elif "billing" in error_str.lower():
        print("\nBilling issue detected")
    else:
        print(f"\nFull error: {error_str[:500]}")