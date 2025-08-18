#!/usr/bin/env python
"""
Minimal test of adapter's citation extraction logic
"""

import os
import sys
from pathlib import Path

# Clear any existing Google credentials to force ADC
os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)
os.environ['GOOGLE_CLOUD_PROJECT'] = 'contestra-ai'

print("=" * 60)
print("TESTING VERTEX ADAPTER CITATION EXTRACTION")
print("=" * 60)

# First get a real response from Vertex
from google import genai
from google.genai.types import GenerateContentConfig, Tool, GoogleSearch

client = genai.Client(
    vertexai=True,
    project="contestra-ai",
    location="europe-west4"
)

print("\n1. Getting response from Vertex with grounding...")
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="What are the top 3 longevity supplement brands in Switzerland?",
    config=GenerateContentConfig(
        tools=[Tool(google_search=GoogleSearch())],
        temperature=0.0,
        seed=42
    )
)

print(f"Response: {response.text[:200]}...")

# Now test our extraction logic directly
print("\n2. Testing citation extraction logic...")

# Manually import just the needed parts to avoid app dependencies
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "app" / "llm" / "adapters"))

# Import just the adapter module
import importlib.util
spec = importlib.util.spec_from_file_location(
    "vertex_genai_adapter",
    Path(__file__).parent.parent / "backend" / "app" / "llm" / "adapters" / "vertex_genai_adapter.py"
)
vertex_module = importlib.util.module_from_spec(spec)

# Mock the types module to avoid import issues
class MockGroundingMode:
    REQUIRED = "REQUIRED"
    PREFERRED = "PREFERRED"
    OFF = "OFF"

class MockTypes:
    GroundingMode = MockGroundingMode

sys.modules['app.llm.adapters.types'] = MockTypes
sys.modules['.types'] = MockTypes

# Now load the module
spec.loader.exec_module(vertex_module)

# Get the adapter class
VertexGenAIAdapter = vertex_module.VertexGenAIAdapter

# Test the extraction
signals = VertexGenAIAdapter._vertex_grounding_signals(response)

print(f"\nExtracted signals:")
print(f"  - grounded: {signals['grounded']}")
print(f"  - tool_calls: {signals['tool_calls']}")
print(f"  - citations count: {len(signals['citations'])}")
print(f"  - queries count: {len(signals.get('queries', []))}")
print(f"  - grounding_sources count: {len(signals.get('grounding_sources', []))}")

if signals['citations']:
    print(f"\n3. Citation details (first 3):")
    for i, cite in enumerate(signals['citations'][:3]):
        print(f"\n  Citation {i+1}:")
        print(f"    Type: {type(cite).__name__}")
        if isinstance(cite, dict):
            for key, val in list(cite.items())[:4]:
                if key == 'uri':
                    # Shorten long URIs
                    val_str = val[:60] + "..." if len(str(val)) > 60 else str(val)
                else:
                    val_str = str(val)[:100] if val else "None"
                print(f"    {key}: {val_str}")
        else:
            print(f"    ERROR: Not a dict! Got {type(cite).__name__}: {cite}")

# Verify all citations are dicts
print(f"\n4. Type verification:")
all_dicts = all(isinstance(c, dict) for c in signals['citations'])
if all_dicts:
    print("  [OK] All citations are dictionaries")
    
    # Check what keys they have
    if signals['citations']:
        all_keys = set()
        for c in signals['citations']:
            all_keys.update(c.keys())
        print(f"  [INFO] Citation keys found: {sorted(all_keys)}")
else:
    print("  [ERROR] Some citations are not dicts!")
    for i, c in enumerate(signals['citations']):
        if not isinstance(c, dict):
            print(f"    Citation {i}: {type(c).__name__} - {c}")

print("\n" + "=" * 60)
print("TEST COMPLETED")
print("=" * 60)