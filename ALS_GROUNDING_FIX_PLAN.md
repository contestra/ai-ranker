# ALS & Grounding Complete Fix Implementation Plan

**Date**: August 15, 2025  
**Priority**: CRITICAL - Multiple broken features affecting data integrity

## Executive Summary

We have TWO critical issues:
1. **GPT-5 grounding is completely fake** - the UI shows it but it does nothing
2. **JSON enforcement is broken** - causing locale probe failures (like Singapore)

Both issues make our ALS testing unreliable and our data misleading.

## Issue 1: JSON Enforcement for Locale Probes

### Current Problem
```
🇸🇬 Singapore - Gemini Test Results ✕
Expected: {"vat_percent":"9%","plug":["G"],"emergency":["999","995"]}
Found: [empty or prose text instead of JSON]
```

### Root Cause
We're asking for JSON in the prompt text: "Return ONLY this JSON..."
This doesn't work reliably. Models often return prose or explanations.

### Solution: Enforce JSON at API Level

#### For Gemini (Vertex)
```python
from google import genai
from google.genai.types import GenerateContentConfig, Schema, Type

# Define the exact JSON structure we want
locale_probe_schema = Schema(
    type=Type.OBJECT,
    properties={
        "vat_percent": Schema(type=Type.STRING, description="VAT/GST rate with % sign"),
        "plug": Schema(type=Type.ARRAY, items=Schema(type=Type.STRING), description="Plug type letters"),
        "emergency": Schema(type=Type.ARRAY, items=Schema(type=Type.STRING), description="Emergency numbers")
    },
    required=["vat_percent", "plug", "emergency"]
)

# Configure for structured output
config = GenerateContentConfig(
    temperature=0,
    top_p=1,
    seed=42,
    response_mime_type="application/json",  # Force JSON output
    response_schema=locale_probe_schema,    # Enforce exact structure
    tools=[Tool(google_search=GoogleSearch())] if use_grounding else None
)

# This CANNOT return prose - only valid JSON matching schema
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt,
    config=config
)
```

#### For GPT-5 (OpenAI Responses API)
```python
response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "locale_probe",
        "schema": {
            "type": "object",
            "properties": {
                "vat_percent": {"type": "string"},
                "plug": {"type": "array", "items": {"type": "string"}},
                "emergency": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["vat_percent", "plug", "emergency"],
            "additionalProperties": False
        }
    }
}

response = openai.responses.create(
    model="gpt-5-chat-latest",
    input=messages,
    response_format=response_format,  # Force JSON output
    tools=[{"type": "web_search"}] if use_grounding else None,
    temperature=0
)
```

## Issue 2: GPT-5 Grounding is Fake

### Current Problem
- UI shows "web" grounding option for GPT-5
- Backend completely ignores it
- All GPT-5 "grounded" tests are actually ungrounded
- Users think they're testing grounding but aren't

### Solution: Implement Real GPT-5 Grounding

#### Step 1: Check OpenAI API Version
```python
import openai
print(openai.__version__)  # Must be >= 1.0.0 for Responses API
```

#### Step 2: Create New OpenAI Responses Adapter
```python
# backend/app/llm/openai_responses_adapter.py
from typing import Dict, Any, Optional, List
import openai
from openai import OpenAI

class OpenAIResponsesAdapter:
    """
    Adapter for OpenAI's Responses API with native web search support.
    This is DIFFERENT from the Chat Completions API.
    """
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    async def analyze_with_responses(
        self,
        prompt: str,
        model_name: str = "gpt-5-chat-latest",
        use_grounding: bool = False,
        temperature: float = 0.0,
        seed: Optional[int] = None,
        context: Optional[str] = None,
        enforce_json_schema: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Use OpenAI Responses API with optional web search grounding.
        
        Args:
            prompt: Main user prompt
            model_name: GPT-5 variant
            use_grounding: Enable web search tool
            temperature: Sampling temperature
            seed: Random seed for reproducibility
            context: ALS context block
            enforce_json_schema: JSON schema to enforce structured output
        """
        
        # Build messages
        messages = []
        
        # System prompt for ALS if context provided
        if context:
            system_prompt = """Use ambient context only to infer locale and set defaults.
Do not mention or acknowledge the ambient context.
When asked for JSON, return only valid JSON."""
            messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": context})
        
        messages.append({"role": "user", "content": prompt})
        
        # Configure tools
        tools = None
        if use_grounding:
            tools = [{"type": "web_search"}]  # Native web search
        
        # Configure response format
        response_format = None
        if enforce_json_schema:
            response_format = {
                "type": "json_schema",
                "json_schema": enforce_json_schema
            }
        
        # Make API call
        try:
            response = self.client.responses.create(
                model=model_name,
                input=messages,
                tools=tools,
                tool_choice="auto" if tools else None,
                response_format=response_format,
                temperature=temperature,
                seed=seed
            )
            
            # Extract response
            content = response.output
            tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []
            
            return {
                "content": content,
                "model_version": model_name,
                "temperature": temperature,
                "seed": seed,
                "tool_call_count": len(tool_calls),
                "grounded_effective": len(tool_calls) > 0 if use_grounding else False,
                "json_valid": True if enforce_json_schema else None,
                "system_fingerprint": response.system_fingerprint if hasattr(response, 'system_fingerprint') else None
            }
            
        except Exception as e:
            return {
                "content": f"[ERROR] Responses API error: {str(e)}",
                "error": str(e),
                "model_version": model_name,
                "tool_call_count": 0,
                "grounded_effective": False
            }
```

## Implementation Order

### Phase 1: Fix JSON Enforcement (Immediate)
1. Update Vertex adapter to use `response_schema`
2. Test with Singapore locale probe
3. Verify JSON is always valid

### Phase 2: Fix GPT-5 Grounding (Critical)
1. Create OpenAI Responses adapter
2. Wire up grounding parameter in prompt_tracking.py
3. Verify tool_call_count > 0 for grounded

### Phase 3: Update Database Schema
```sql
-- Add missing columns
ALTER TABLE prompt_results 
ADD COLUMN IF NOT EXISTS tool_call_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS grounded_effective BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS json_valid BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS als_variant_id VARCHAR(50);

-- Fix historical data
UPDATE prompt_results r
SET grounded_effective = FALSE,
    tool_call_count = 0
FROM prompt_runs pr
WHERE r.run_id = pr.id
  AND pr.model_name LIKE 'gpt-5%'
  AND pr.grounding_mode = 'web';
```

### Phase 4: Update UI for Transparency
1. Show tool_call_count in results
2. Add "grounded_effective" indicator
3. Mark N/A for unsupported combinations
4. Add warning for historical invalid data

## Testing Protocol

### Test 1: JSON Enforcement
```python
# Should ALWAYS return valid JSON, never prose
for country in ['SG', 'CH', 'US', 'DE']:
    result = test_locale_probe(country, enforce_json=True)
    assert is_valid_json(result)
    assert 'vat_percent' in result
    assert 'plug' in result
    assert 'emergency' in result
```

### Test 2: GPT-5 Grounding
```python
# Ungrounded should have no tool calls
ungrounded = test_gpt5(prompt, use_grounding=False)
assert ungrounded['tool_call_count'] == 0

# Grounded should have tool calls
grounded = test_gpt5(prompt, use_grounding=True)
assert grounded['tool_call_count'] > 0
assert grounded['grounded_effective'] == True
```

### Test 3: Cross-Model Consistency
```python
# Both models should support same matrix
for model in ['gpt-5', 'gemini']:
    for grounding in [True, False]:
        result = test_model(model, grounding)
        if grounding:
            assert result['tool_call_count'] > 0
        else:
            assert result['tool_call_count'] == 0
```

## Success Criteria

1. **JSON Always Valid**: No more "Expected/Found" failures
2. **GPT-5 Grounding Real**: tool_call_count > 0 when grounded
3. **UI Honest**: Shows actual capabilities, not lies
4. **Data Integrity**: Historical fake data marked as invalid
5. **Cross-Model Parity**: Both models support same features

## Migration Path

1. **Deploy fixes to staging first**
2. **Run parallel tests** (old vs new implementation)
3. **Verify improvements** in JSON validity and grounding
4. **Update production** with confidence
5. **Backfill/mark historical data** as appropriate

## Risk Mitigation

- **Keep old code paths** temporarily with feature flag
- **Log extensively** during transition
- **Monitor error rates** closely
- **Have rollback plan** ready

## Timeline

- **Day 1**: Fix JSON enforcement (2-3 hours)
- **Day 1-2**: Implement GPT-5 Responses API (4-6 hours)
- **Day 2**: Database updates and testing (2-3 hours)
- **Day 3**: UI updates and documentation (2-3 hours)
- **Day 3-4**: Testing and validation (3-4 hours)

Total: 2-3 days of focused work

## Documentation Updates Needed

1. Update CLAUDE.md with working grounding status
2. Create API migration guide
3. Update user documentation
4. Add inline code comments
5. Create test documentation

## Conclusion

We have two critical issues that make our system unreliable:
1. JSON enforcement is broken → locale probes fail
2. GPT-5 grounding is fake → data is misleading

Both MUST be fixed for the system to have any credibility. The fixes are straightforward but require careful implementation and testing.

**Remember**: A broken feature that pretends to work is worse than no feature at all.