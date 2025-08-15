#!/usr/bin/env python
"""
Quick test after adding IAM role
"""

print("Testing Vertex AI after IAM fix...")
print("=" * 50)

# Test 1: Traditional SDK
print("\n1. Traditional Vertex AI SDK:")
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    vertexai.init(project="contestra-ai", location="europe-west4")
    response = GenerativeModel("gemini-1.5-flash-002").generate_content("Say OK")
    print(f"   SUCCESS: {response.text.strip()}")
except Exception as e:
    print(f"   FAILED: {str(e)[:100]}")

# Test 2: New GenAI Client
print("\n2. Google GenAI Client:")
try:
    from google import genai
    client = genai.Client(vertexai=True, project="contestra-ai", location="europe-west4")
    response = client.models.generate_content(model="gemini-1.5-flash-002", contents="Say OK")
    print(f"   SUCCESS: {response.text.strip()}")
except Exception as e:
    print(f"   FAILED: {str(e)[:100]}")

# Test 3: With grounding
print("\n3. With Grounding (Google Search):")
try:
    from google import genai
    from google.genai import types
    
    client = genai.Client(vertexai=True, project="contestra-ai", location="europe-west4")
    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )
    response = client.models.generate_content(
        model="gemini-1.5-flash-002",
        contents="What is the current temperature in Tokyo?",
        config=config
    )
    print(f"   SUCCESS: {response.text[:100]}...")
except Exception as e:
    print(f"   FAILED: {str(e)[:100]}")

print("\n" + "=" * 50)
print("If all tests show SUCCESS, Vertex AI is fully working!")
print("If you see PERMISSION_DENIED, wait 1-2 minutes for IAM to propagate.")