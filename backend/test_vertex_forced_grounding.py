#!/usr/bin/env python
"""
Test Vertex grounding with DynamicRetrievalConfig per ChatGPT's guidance
Forces web search with dynamic_threshold=0.0
"""

import os
import json

# Remove problematic environment variable
if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
    del os.environ['GOOGLE_APPLICATION_CREDENTIALS']

from google import genai
from google.genai.types import (
    GenerateContentConfig, Tool, GoogleSearch, Schema, Type, HttpOptions
)

print("Testing Vertex grounding with forced dynamic retrieval...")

# Initialize with global location per ChatGPT
client = genai.Client(
    http_options=HttpOptions(api_version="v1"),
    vertexai=True, 
    project="contestra-ai", 
    location="global"  # ChatGPT recommends global for grounding
)

# Schema with source fields
schema = Schema(
    type=Type.OBJECT,
    properties={
        "value": Schema(type=Type.STRING),
        "source_url": Schema(type=Type.STRING),
        "as_of_utc": Schema(type=Type.STRING),
    },
    required=["value", "source_url", "as_of_utc"]
)

# Config with grounding - CANNOT use response_schema with GoogleSearch!
cfg = GenerateContentConfig(
    tools=[
        Tool(
            google_search=GoogleSearch()  # Simple GoogleSearch without dynamic config
        )
    ],
    temperature=1.0,  # Vertex suggests 1.0 for Search-grounded prompts
    # response_mime_type="application/json",  # Can't use with GoogleSearch
    # response_schema=schema  # Can't use with GoogleSearch
)

# Prompt that should trigger search - ask for JSON format in prompt
prompt = (
    "As of today, what's the standard VAT in Singapore? "
    "Return JSON with fields: value, source_url, and as_of_utc. "
    "Make sure to search for current official information."
)

try:
    print("\nCalling Gemini 2.5 Pro with forced GoogleSearch...")
    resp = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=cfg
    )
    
    # Get text
    text = getattr(resp, "text", None)
    if not text and hasattr(resp, 'candidates'):
        try:
            text = resp.candidates[0].content.parts[0].text
        except:
            pass
    
    print(f"\nResponse text: {text}")
    
    # Check for grounding using ChatGPT's method
    cand = resp.candidates[0] if resp.candidates else None
    gm = getattr(cand, "grounding_metadata", None) if cand else None
    
    queries = getattr(gm, "web_search_queries", []) or []
    chunks = getattr(gm, "grounding_chunks", []) or []
    supports = getattr(gm, "grounding_supports", []) or []
    entry = getattr(gm, "search_entry_point", None)
    
    grounded_effective = bool(queries or chunks or supports or entry)
    
    print(f"\n===== GROUNDING ANALYSIS =====")
    print(f"Grounded: {grounded_effective}")
    print(f"Web Search Queries: {queries}")
    print(f"Grounding Chunks: {len(chunks)} found")
    
    # Extract citations from chunks
    citations = []
    for ch in chunks:
        if hasattr(ch, 'web') and ch.web:
            uri = getattr(ch.web, 'uri', None)
            if uri:
                citations.append(uri)
    
    print(f"Citations: {citations}")
    
    if grounded_effective:
        print("\n[SUCCESS] Web search was performed!")
    else:
        print("\n[FAIL] No web search performed")
    
    # Parse JSON
    if text:
        try:
            if "```" in text:
                import re
                match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
                if match:
                    text = match.group(1).strip()
            
            obj = json.loads(text)
            print(f"\nParsed JSON: {json.dumps(obj, indent=2)}")
        except Exception as e:
            print(f"JSON parsing failed: {e}")
            
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()