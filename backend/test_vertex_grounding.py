#!/usr/bin/env python
"""
Test Vertex grounding with working configuration
"""

import os
os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)
os.environ['GOOGLE_CLOUD_PROJECT'] = 'contestra-ai'

from google import genai
from google.genai.types import GenerateContentConfig, Tool, GoogleSearch

print("Testing grounding with europe-west4 and gemini-2.0-flash...")

loc = "europe-west4"
MODEL = "gemini-2.0-flash"

try:
    client = genai.Client(vertexai=True, project="contestra-ai", location=loc)
    resp = client.models.generate_content(
        model=MODEL,
        contents="What's the standard VAT rate in the UK? Answer briefly.",
        config=GenerateContentConfig(
            tools=[Tool(google_search=GoogleSearch())],
            temperature=0,
        ),
    )
    print(f"SUCCESS with grounding: {resp.text}")
except Exception as e:
    print(f"ERROR: {e}")
    
print("\nNow testing through our adapter...")
import asyncio
from app.llm.vertex_genai_adapter import VertexGenAIAdapter

async def test_adapter():
    adapter = VertexGenAIAdapter(project="contestra-ai", location="europe-west4")
    
    # Test without grounding
    result = await adapter.analyze_with_gemini(
        prompt="Say OK",
        use_grounding=False,
        model_name="gemini-2.0-flash"
    )
    print(f"\nAdapter without grounding: {result.get('content', result.get('error'))}")
    
    # Test with grounding
    result = await adapter.analyze_with_gemini(
        prompt="What's the standard VAT rate in the UK?",
        use_grounding=True,
        model_name="gemini-2.0-flash"
    )
    print(f"\nAdapter with grounding: {result.get('content', result.get('error'))}")

asyncio.run(test_adapter())