#!/usr/bin/env python
"""
Test Vertex AI setup with your contestra-ai project
"""

import os
import sys

# Set environment variables if not already set
os.environ["GOOGLE_CLOUD_PROJECT"] = "contestra-ai"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"  # Change if you prefer another region

print("=" * 60)
print("Testing Vertex AI Setup")
print("=" * 60)

# Test 1: Check if ADC is configured
print("\nStep 1: Checking Google Authentication...")
try:
    import google.auth
    credentials, project = google.auth.default()
    print(f"[OK] ADC configured for project: {project}")
    if project != "contestra-ai":
        print(f"  Note: Project is {project}, expected contestra-ai")
        print(f"  Run: gcloud config set project contestra-ai")
except Exception as e:
    print(f"[ERROR] ADC not configured: {e}")
    print("  Run: gcloud auth application-default login")
    sys.exit(1)

# Test 2: Import Vertex AI
print("\nStep 2: Importing Vertex AI...")
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    print("[OK] Vertex AI packages imported successfully")
except ImportError as e:
    print(f"[ERROR] Import error: {e}")
    sys.exit(1)

# Test 3: Initialize Vertex AI
print("\nStep 3: Initializing Vertex AI...")
try:
    vertexai.init(
        project="contestra-ai",
        location="us-central1"
    )
    print("[OK] Vertex AI initialized")
except Exception as e:
    print(f"[ERROR] Initialization error: {e}")
    print("  Make sure Vertex AI API is enabled in your project")
    sys.exit(1)

# Test 4: Simple model call
print("\nStep 4: Testing Gemini model...")
try:
    model = GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("Say 'Hello from Vertex AI'")
    print(f"[OK] Model response: {response.text}")
except Exception as e:
    print(f"[ERROR] Model call failed: {e}")
    print("  This might be a quota or permission issue")
    sys.exit(1)

# Test 5: LangChain integration
print("\nStep 5: Testing LangChain Vertex integration...")
try:
    from langchain_google_vertexai import ChatVertexAI
    
    # Create model with LangChain
    chat_model = ChatVertexAI(
        model="gemini-1.5-pro",
        project="contestra-ai",
        location="us-central1",
        temperature=0.1
    )
    
    # Test without grounding
    from langchain.schema import HumanMessage
    messages = [HumanMessage(content="What is 2+2?")]
    response = chat_model.invoke(messages)
    print(f"[OK] LangChain response: {response.content[:50]}...")
    
except Exception as e:
    print(f"[ERROR] LangChain test failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("SUCCESS! Vertex AI is ready to use")
print("=" * 60)
print("\nNext steps:")
print("1. Your project: contestra-ai")
print("2. Your region: us-central1 (change if needed)")
print("3. Authentication: Using ADC (Application Default Credentials)")
print("4. Ready to implement grounded/ungrounded runs with ChatVertexAI")