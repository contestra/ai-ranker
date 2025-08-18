#!/usr/bin/env python
"""
Simple test of Vertex GenAI adapter without full app dependencies
"""

import os
import sys
import asyncio
import json
from pathlib import Path

# Clear any existing Google credentials to force ADC
os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)
os.environ['GOOGLE_CLOUD_PROJECT'] = 'contestra-ai'

# Import just what we need
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

print("=" * 60)
print("VERTEX GENAI ADAPTER SIMPLE TEST")
print("=" * 60)

# Test 1: Direct SDK test with grounding
print("\n1. Testing direct SDK with grounding...")
print("-" * 40)

from google import genai
from google.genai.types import GenerateContentConfig, Tool, GoogleSearch

client = genai.Client(
    vertexai=True,
    project="contestra-ai",
    location="europe-west4"
)

try:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="What is the current VAT rate in Switzerland? Answer with just the percentage.",
        config=GenerateContentConfig(
            tools=[Tool(google_search=GoogleSearch())],
            temperature=0.0,
            seed=42
        )
    )
    
    print(f"Response: {response.text}")
    
    # Check grounding metadata
    if hasattr(response, 'candidates') and response.candidates:
        gm = getattr(response.candidates[0], 'grounding_metadata', None)
        if gm:
            print(f"\nGrounding metadata found:")
            
            # Check for various attributes
            attrs = ['web_search_queries', 'grounding_chunks', 'grounding_supports', 'citations']
            for attr in attrs:
                if hasattr(gm, attr):
                    val = getattr(gm, attr)
                    if val:
                        print(f"  - {attr}: {len(val) if hasattr(val, '__len__') else 'present'}")
                        if attr == 'grounding_chunks' and val:
                            # Show first chunk structure
                            chunk = val[0]
                            print(f"    First chunk type: {type(chunk).__name__}")
                            if hasattr(chunk, 'web'):
                                web = chunk.web
                                if hasattr(web, 'uri'):
                                    print(f"    URI: {web.uri}")
                                if hasattr(web, 'title'):
                                    print(f"    Title: {web.title}")
                        elif attr == 'citations' and val:
                            # Show citation structure
                            cite = val[0]
                            print(f"    First citation type: {type(cite).__name__}")
                            if isinstance(cite, str):
                                print(f"    Value (string): {cite[:100]}")
                            elif isinstance(cite, dict):
                                print(f"    Value (dict): {cite}")
        else:
            print("No grounding metadata found")
    
    print("\n[OK] Direct SDK test completed")
    
except Exception as e:
    print(f"[ERROR] Direct SDK test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Test our adapter's citation extraction
print("\n2. Testing adapter citation extraction...")
print("-" * 40)

# Import just the adapter
from app.llm.adapters.vertex_genai_adapter import VertexGenAIAdapter

# Test the grounding signals extraction
if response:
    signals = VertexGenAIAdapter._vertex_grounding_signals(response)
    
    print(f"Extracted signals:")
    print(f"  - grounded: {signals['grounded']}")
    print(f"  - tool_calls: {signals['tool_calls']}")
    print(f"  - citations: {len(signals['citations'])}")
    
    if signals['citations']:
        print(f"\nCitation details:")
        for i, cite in enumerate(signals['citations'][:3]):
            print(f"  Citation {i+1}:")
            print(f"    Type: {type(cite).__name__}")
            if isinstance(cite, dict):
                for key, val in list(cite.items())[:3]:  # Show first 3 keys
                    val_str = str(val)[:50] if val else "None"
                    print(f"    {key}: {val_str}")
            else:
                print(f"    ERROR: Not a dict! Got {type(cite).__name__}: {cite}")
    
    # Verify all citations are dicts
    all_dicts = all(isinstance(c, dict) for c in signals['citations'])
    if all_dicts:
        print("\n[OK] All citations are dicts")
    else:
        print("\n[ERROR] Some citations are not dicts!")
        for i, c in enumerate(signals['citations']):
            if not isinstance(c, dict):
                print(f"  Citation {i}: {type(c).__name__} - {c}")

print("\n" + "=" * 60)
print("TEST COMPLETED")
print("=" * 60)