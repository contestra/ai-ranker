#!/usr/bin/env python
"""
Minimal test to verify Vertex grounding works
Exactly as ChatGPT suggested
"""

import os
import json

# Remove problematic environment variable
if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
    del os.environ['GOOGLE_APPLICATION_CREDENTIALS']

from google import genai
from google.genai.types import GenerateContentConfig, Tool, GoogleSearch, Schema, Type, HttpOptions

print("Testing minimal Vertex grounding setup...")

# Initialize with API v1
client = genai.Client(
    http_options=HttpOptions(api_version="v1"),
    vertexai=True, 
    project="contestra-ai", 
    location="europe-west4"
)

# Schema with source fields
schema = Schema(
    type=Type.OBJECT,
    properties={
        "gst_rate": Schema(type=Type.STRING),
        "source_url": Schema(type=Type.STRING),
        "as_of_utc": Schema(type=Type.STRING),
    },
    required=["gst_rate", "source_url", "as_of_utc"]
)

# Config with grounding
cfg = GenerateContentConfig(
    tools=[Tool(google_search=GoogleSearch())],
    response_mime_type="application/json",
    response_schema=schema,
    temperature=1.0  # Critical for grounding
)

# Prompt that should trigger search
prompt = (
    "As of today, what is Singapore's current GST (VAT) rate? "
    "Include an official government source URL and ISO8601 as_of_utc timestamp."
)

try:
    print("\nCalling Gemini 2.5 Pro with GoogleSearch tool...")
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
    
    # Check for grounding metadata
    grounded = False
    if hasattr(resp, 'candidates') and resp.candidates:
        cand = resp.candidates[0]
        if hasattr(cand, 'grounding_metadata'):
            gm = cand.grounding_metadata
            print(f"\nGrounding metadata found!")
            print(f"  - Type: {type(gm)}")
            print(f"  - Dir: {dir(gm)}")
            
            # Try to convert to dict to see structure
            try:
                gm_dict = gm.to_dict() if hasattr(gm, 'to_dict') else gm.__dict__
                print(f"  - Dict: {gm_dict}")
            except:
                pass
                
            print(f"  - Citations: {getattr(gm, 'citations', [])}")
            print(f"  - Web queries: {getattr(gm, 'web_search_queries', None)}")
            print(f"  - Search queries: {getattr(gm, 'search_queries', None)}")
            grounded = True
    
    if not grounded:
        print("\nNO GROUNDING METADATA FOUND")
        
        # Try to find it in response dict
        try:
            d = resp.to_dict() if hasattr(resp, 'to_dict') else resp.__dict__
            print(f"\nResponse dict keys: {list(d.keys())}")
            if 'candidates' in d and d['candidates']:
                cand_dict = d['candidates'][0]
                print(f"Candidate keys: {list(cand_dict.keys())}")
        except Exception as e:
            print(f"Failed to inspect response: {e}")
    
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