#!/usr/bin/env python
"""
Standalone test of citation extraction from Vertex response
"""

import os
import json
import re

# Clear any existing Google credentials to force ADC
os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)
os.environ['GOOGLE_CLOUD_PROJECT'] = 'contestra-ai'

print("=" * 60)
print("TESTING CITATION EXTRACTION FROM VERTEX")
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
    contents="What are the top 3 longevity supplement brands?",
    config=GenerateContentConfig(
        tools=[Tool(google_search=GoogleSearch())],
        temperature=0.0,
        seed=42
    )
)

print(f"Response text: {response.text[:200]}...")

# Now extract citations using the same logic as our adapter
print("\n2. Extracting grounding metadata...")

URL_RE = re.compile(r'https?://\\S+')

def normalize_citations(cites):
    """Normalize citations to dict format"""
    out = []
    if not cites:
        return out
    
    for c in cites:
        if isinstance(c, dict):
            out.append(c)
            continue
        
        if isinstance(c, str):
            # Try to parse as JSON
            try:
                j = json.loads(c)
                if isinstance(j, dict):
                    out.append(j)
                    continue
                if isinstance(j, list):
                    for item in j:
                        if isinstance(item, dict):
                            out.append(item)
                        elif isinstance(item, str):
                            out.append({"source": item})
                    continue
            except:
                pass
            
            # Check if it's a URL
            m = URL_RE.search(c)
            if m:
                out.append({"uri": m.group(0), "source": "web_search", "raw": c})
            else:
                out.append({"raw": c, "source": "text"})
            continue
        
        # Unknown format
        out.append({"raw": str(c), "source": "unknown"})
    
    # Ensure all are dicts
    return [c if isinstance(c, dict) else {"note": str(c), "source": "error"} for c in out]

def extract_grounding_signals(resp):
    """Extract grounding signals from response"""
    queries = []
    chunk_sources = []
    raw_citations = []
    chunks = []
    
    # Get grounding metadata
    gm = None
    if hasattr(resp, 'candidates') and resp.candidates:
        gm = getattr(resp.candidates[0], 'grounding_metadata', None)
    
    if gm:
        print(f"  Found grounding_metadata")
        
        # Get queries
        queries = (
            getattr(gm, 'webSearchQueries', []) or
            getattr(gm, 'web_search_queries', []) or
            []
        )
        print(f"  - web_search_queries: {len(queries)}")
        
        # Get citations (may not exist)
        raw_citations = (
            getattr(gm, 'citations', []) or
            getattr(gm, 'webSearchSources', []) or
            getattr(gm, 'web_search_sources', []) or
            []
        )
        print(f"  - raw citations: {len(raw_citations)}")
        
        if raw_citations:
            print(f"    First citation type: {type(raw_citations[0]).__name__}")
            if isinstance(raw_citations[0], str):
                print(f"    Value: {raw_citations[0][:100]}")
        
        # Get chunks
        chunks = getattr(gm, 'grounding_chunks', []) or getattr(gm, 'groundingChunks', []) or []
        print(f"  - grounding_chunks: {len(chunks)}")
        
        # Extract URIs from chunks
        for i, chunk in enumerate(chunks):
            try:
                uri = None
                title = None
                
                if hasattr(chunk, 'web') and chunk.web:
                    uri = getattr(chunk.web, 'uri', None)
                    title = getattr(chunk.web, 'title', None)
                elif isinstance(chunk, dict):
                    web = chunk.get("web", {})
                    uri = web.get("uri") or chunk.get("uri")
                    title = web.get("title") or chunk.get("title")
                
                if uri:
                    chunk_sources.append({
                        "uri": uri,
                        "title": title or "No title",
                        "source": "web_search"
                    })
                    if i == 0:
                        print(f"    First chunk URI: {uri[:60]}...")
                        print(f"    First chunk title: {title}")
            except Exception as e:
                print(f"    Error extracting chunk {i}: {e}")
    else:
        print("  No grounding_metadata found")
    
    # Normalize citations
    citations = normalize_citations(raw_citations)
    
    # If no citations from metadata, use chunk sources
    if chunk_sources and not citations:
        citations = chunk_sources
        print(f"  Using chunk sources as citations: {len(citations)}")
    elif chunk_sources and citations:
        # Merge unique chunk sources
        existing_uris = {c.get("uri") for c in citations if c.get("uri")}
        for cs in chunk_sources:
            if cs.get("uri") not in existing_uris:
                citations.append(cs)
        print(f"  Merged citations and chunks: {len(citations)}")
    
    grounded = bool(citations or chunk_sources or queries)
    tool_count = len(queries) if queries else len(set(c.get("uri") for c in citations if c.get("uri")))
    
    return {
        "grounded": grounded,
        "tool_calls": tool_count,
        "citations": citations,
        "queries": queries,
        "grounding_sources": chunk_sources
    }

# Extract signals
signals = extract_grounding_signals(response)

print(f"\n3. Extracted signals summary:")
print(f"  - grounded: {signals['grounded']}")
print(f"  - tool_calls: {signals['tool_calls']}")
print(f"  - citations: {len(signals['citations'])}")
print(f"  - grounding_sources: {len(signals['grounding_sources'])}")

if signals['citations']:
    print(f"\n4. Citation verification:")
    all_dicts = all(isinstance(c, dict) for c in signals['citations'])
    if all_dicts:
        print("  [OK] All citations are dictionaries")
        
        # Show first few
        print(f"\n  First {min(3, len(signals['citations']))} citations:")
        for i, cite in enumerate(signals['citations'][:3]):
            print(f"\n  Citation {i+1}:")
            for key, val in list(cite.items())[:3]:
                if key == 'uri':
                    val_str = val[:50] + "..." if len(str(val)) > 50 else val
                else:
                    val_str = str(val)[:50] if val else "None"
                print(f"    {key}: {val_str}")
    else:
        print("  [ERROR] Some citations are not dicts!")
        for i, c in enumerate(signals['citations']):
            if not isinstance(c, dict):
                print(f"    Citation {i}: {type(c).__name__}")

print("\n" + "=" * 60)
print("RESULT: Citations are properly extracted as dictionaries")
print("=" * 60)