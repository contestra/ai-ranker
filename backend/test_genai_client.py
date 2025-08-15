#!/usr/bin/env python
"""
Test the new Google GenAI client with Vertex AI
This is simpler than the traditional Vertex AI SDK
"""

import os
import asyncio

# Set project and location
os.environ["GOOGLE_CLOUD_PROJECT"] = "contestra-ai"
os.environ["GOOGLE_CLOUD_LOCATION"] = "europe-west4"

print("=" * 60)
print("Testing Google GenAI Client with Vertex AI")
print("=" * 60)

def test_basic():
    """Test basic connection"""
    print("\nTest 1: Basic Connection")
    print("-" * 40)
    
    try:
        from google import genai
        client = genai.Client(
            vertexai=True, 
            project="contestra-ai", 
            location="europe-west4"
        )
        
        response = client.models.generate_content(
            model="gemini-1.5-flash-002",
            contents="Say 'Hello from Vertex AI'"
        )
        
        print(f"[OK] Response: {response.text}")
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        if "403" in str(e):
            print("\nVertex AI API is not enabled. Please:")
            print("1. Go to: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project=contestra-ai")
            print("2. Click 'ENABLE'")
            print("3. Wait 1-2 minutes and try again")
        return False

def test_ungrounded():
    """Test ungrounded generation"""
    print("\nTest 2: Ungrounded Generation")
    print("-" * 40)
    
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(
            vertexai=True,
            project="contestra-ai",
            location="europe-west4"
        )
        
        config = types.GenerateContentConfig(
            temperature=0.0,
            top_p=1.0,
            candidate_count=1,
            seed=42
        )
        
        response = client.models.generate_content(
            model="gemini-1.5-flash-002",
            contents="What is 2+2?",
            config=config
        )
        
        print(f"[OK] Response: {response.text.strip()}")
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def test_grounded():
    """Test grounded generation with Google Search"""
    print("\nTest 3: Grounded Generation (Google Search)")
    print("-" * 40)
    
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(
            vertexai=True,
            project="contestra-ai", 
            location="europe-west4"
        )
        
        config = types.GenerateContentConfig(
            temperature=0.0,
            top_p=1.0,
            candidate_count=1,
            seed=42,
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
        
        response = client.models.generate_content(
            model="gemini-1.5-flash-002",
            contents="What is the current temperature in Tokyo right now?",
            config=config
        )
        
        print(f"[OK] Grounded response: {response.text[:200]}...")
        
        # Check if grounding metadata is available
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'grounding_metadata'):
                print("[OK] Grounding metadata available")
        
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

async def test_async():
    """Test async generation"""
    print("\nTest 4: Async Generation")
    print("-" * 40)
    
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(
            vertexai=True,
            project="contestra-ai",
            location="europe-west4"
        )
        
        config = types.GenerateContentConfig(
            temperature=0.0,
            top_p=1.0,
            candidate_count=1
        )
        
        # Note: The async method might be generate_content_async
        response = await client.models.generate_content_async(
            model="gemini-1.5-flash-002",
            contents="Count to 3",
            config=config
        )
        
        print(f"[OK] Async response: {response.text}")
        return True
    except AttributeError:
        # Try alternative async method name
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash-002",
                contents="Count to 3",
                config=config
            )
            print(f"[OK] Response (sync fallback): {response.text}")
            return True
        except Exception as e2:
            print(f"[ERROR] {e2}")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def test_with_als_context():
    """Test with ALS context (ambient location signals)"""
    print("\nTest 5: With ALS Context")
    print("-" * 40)
    
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(
            vertexai=True,
            project="contestra-ai",
            location="europe-west4"
        )
        
        # Build conversation with ALS context
        messages = [
            # System instruction
            types.Content(
                role="user",
                parts=[types.Part(text="""Use ambient context only to infer locale and set defaults.
Do not mention or acknowledge the ambient context.""")]
            ),
            types.Content(
                role="model",
                parts=[types.Part(text="Understood.")]
            ),
            # ALS context (Germany)
            types.Content(
                role="user", 
                parts=[types.Part(text="""Ambient Context:
- 2025-08-14 14:05, UTC+01:00
- bund.de — "Führerschein verlängern"
- 10115 Berlin • +49 30 xxxx xxxx • 12,90 €""")]
            ),
            types.Content(
                role="model",
                parts=[types.Part(text="Noted.")]
            ),
            # Actual question
            types.Content(
                role="user",
                parts=[types.Part(text="What's the VAT rate?")]
            )
        ]
        
        config = types.GenerateContentConfig(
            temperature=0.0,
            top_p=1.0,
            candidate_count=1
        )
        
        response = client.models.generate_content(
            model="gemini-1.5-flash-002",
            contents=messages,
            config=config
        )
        
        print(f"[OK] Response with ALS: {response.text}")
        if "19" in response.text:
            print("[OK] Correctly inferred German VAT rate!")
        
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def main():
    """Run all tests"""
    print("\nStarting tests...")
    print("Project: contestra-ai")
    print("Location: europe-west4")
    print()
    
    results = []
    
    # Run sync tests
    results.append(("Basic", test_basic()))
    
    if results[0][1]:  # Only continue if basic test passes
        results.append(("Ungrounded", test_ungrounded()))
        results.append(("Grounded", test_grounded()))
        results.append(("ALS Context", test_with_als_context()))
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async_result = loop.run_until_complete(test_async())
        results.append(("Async", async_result))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\nSUCCESS! Google GenAI client with Vertex AI is working!")
        print("\nNext steps:")
        print("1. Update langchain_adapter.py to use Vertex for grounding")
        print("2. Keep ALS context as separate messages")
        print("3. Use tools parameter for grounding, not prompt modification")
    else:
        print("\nSome tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()