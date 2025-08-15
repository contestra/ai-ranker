# Vertex Grounding - The Final Solution

## The Missing Piece: Schema Fields for Sources!

**Problem**: Our JSON schema for grounded tests doesn't have `source_url` field, so Gemini has no way to include the official source we're asking for!

## Critical Fixes

### 1. Add Source Fields to Schema
```python
schema = Schema(
    type=Type.OBJECT,
    properties={
        "vat_percent": Schema(type=Type.STRING),
        "source_url": Schema(type=Type.STRING),  # THIS WAS MISSING!
        "as_of_utc": Schema(type=Type.STRING),   # THIS TOO!
    }
)
```

### 2. Use API v1 with HttpOptions
```python
from google.genai.types import HttpOptions

client = genai.Client(
    http_options=HttpOptions(api_version="v1"),
    vertexai=True, 
    project="contestra-ai", 
    location="europe-west4"
)
```

### 3. Temperature MUST be 1.0
```python
cfg = GenerateContentConfig(
    tools=[Tool(google_search=GoogleSearch())],
    temperature=1.0,  # Critical for grounding
    response_mime_type="application/json",
    response_schema=schema
)
```

### 4. Better Prompts for Grounded Tests
- "As of today, what is Singapore's GST? Include official government source URL and as_of_utc."
- "What is today's mid-market EUR/SGD rate? Include source URL and as_of_utc."

### 5. Correct Grounding Detection
```python
grounded_effective = bool(
    groundingMetadata.citations or 
    groundingMetadata.webSearchQueries
)
```

## Why It Wasn't Working

1. **No place for sources** - Schema lacked source_url field
2. **API version** - Need v1 for proper grounding
3. **Prompt not specific enough** - Need to ask for as_of_utc
4. **Wrong detection** - Must check webSearchQueries too

## Implementation Checklist

- [ ] Update GROUNDED_SCHEMA to include source_url and as_of_utc
- [ ] Add HttpOptions(api_version="v1") to client initialization
- [ ] Ensure temperature=1.0 for grounded requests
- [ ] Update prompts to request source_url and as_of_utc
- [ ] Check both citations AND webSearchQueries for grounding