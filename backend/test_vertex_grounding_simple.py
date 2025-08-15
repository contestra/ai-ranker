#!/usr/bin/env python
"""
Simple test to verify Vertex grounding works without JSON schema
"""

import os
import sys
from pathlib import Path

# Remove problematic environment variable
if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
    del os.environ['GOOGLE_APPLICATION_CREDENTIALS']

sys.path.insert(0, str(Path(__file__).parent))

from google import genai
from google.genai.types import GenerateContentConfig, Tool, GoogleSearch

print("Testing Vertex Gemini 2.5 with GoogleSearch...")

# Initialize client
client = genai.Client(vertexai=True, project="contestra-ai", location="europe-west4")

# Test 1: Without JSON schema requirement
print("\n1. Testing WITH GoogleSearch, WITHOUT JSON schema:")
config = GenerateContentConfig(
    tools=[Tool(google_search=GoogleSearch())],
    temperature=1.0
)

try:
    response = client.models.generate_content(
        model="publishers/google/models/gemini-2.5-flash",
        contents="What is the current GST rate in Singapore as of today? Include an official source URL.",
        config=config
    )
    
    text = getattr(response, 'text', 'NO TEXT ATTRIBUTE')
    print(f"Response text: {text[:500] if text else 'EMPTY'}")
    
    # Check for grounding metadata
    if hasattr(response, 'candidates') and response.candidates:
        cand = response.candidates[0]
        if hasattr(cand, 'grounding_metadata'):
            print(f"Grounding metadata found: {cand.grounding_metadata}")
        else:
            print("No grounding_metadata in candidate")
    
except Exception as e:
    print(f"Error: {e}")

# Test 2: With JSON schema but no grounding
print("\n2. Testing WITHOUT GoogleSearch, WITH JSON schema:")
from google.genai.types import Schema, Type

config = GenerateContentConfig(
    temperature=0.0,
    response_mime_type="application/json",
    response_schema=Schema(
        type=Type.OBJECT,
        properties={
            "rate": Schema(type=Type.STRING),
            "source": Schema(type=Type.STRING)
        }
    )
)

try:
    response = client.models.generate_content(
        model="publishers/google/models/gemini-2.5-flash",
        contents="What is Singapore's GST rate? Return as JSON with rate and source fields.",
        config=config
    )
    
    text = getattr(response, 'text', 'NO TEXT ATTRIBUTE')
    print(f"Response text: {text}")
    
except Exception as e:
    print(f"Error: {e}")

# Test 3: Try both together (might fail)
print("\n3. Testing WITH GoogleSearch AND JSON schema:")
config = GenerateContentConfig(
    tools=[Tool(google_search=GoogleSearch())],
    temperature=1.0,
    response_mime_type="application/json",
    response_schema=Schema(
        type=Type.OBJECT,
        properties={
            "rate": Schema(type=Type.STRING),
            "source": Schema(type=Type.STRING)
        }
    )
)

try:
    response = client.models.generate_content(
        model="publishers/google/models/gemini-2.5-flash",
        contents="What is the current GST rate in Singapore as of today? Include an official source URL. Return as JSON.",
        config=config
    )
    
    text = getattr(response, 'text', 'NO TEXT ATTRIBUTE')
    print(f"Response text: {text[:500] if text else 'EMPTY'}")
    
    # Check response structure
    print(f"Response type: {type(response)}")
    print(f"Response attributes: {dir(response)}")
    
except Exception as e:
    print(f"Error: {e}")