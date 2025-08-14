# Prompter V7 Fake LLM Integration
## Complete End-to-End Testing Without External APIs

**File**: `prompter_router_min_v3.py`  
**Status**: Final version with integrated fake LLM  
**Purpose**: Enable complete end-to-end testing without any external API calls

## Overview

The external model provided a final enhancement that integrates a fake in-process "LLM" directly into the router. This allows you to:
- See fingerprints flow end-to-end
- Test the complete pipeline locally
- Verify metadata extraction works correctly
- Run without any API keys or external dependencies

## Fake LLM Implementation

### Response Generation
```python
def _fake_llm_response(provider: str, model_id: str, prompt: str) -> dict:
    """Generate fake LLM response with realistic metadata"""
    
    provider = (provider or '').lower()
    meta = {}
    
    # Provider-specific metadata
    if provider == 'openai':
        # Fake OpenAI system fingerprint
        meta['system_fingerprint'] = f"fp_stub_{_hash8('openai:' + model_id)}"
    
    elif provider == 'google':  # Gemini
        # Fake Gemini model version
        meta['modelVersion'] = f"{model_id}-stub-001"
    
    elif provider == 'anthropic':
        # Anthropic returns model in metadata
        meta['model'] = model_id
    
    elif provider == 'azure-openai':
        # Often missing fingerprint - test fallback path
        meta = {}
    
    # Echo response with provider/model prefix
    return {
        'content': f"[FAKE {provider or 'unknown'}::{model_id}] " + prompt[:240],
        'response_metadata': meta,
        'usage': {
            'prompt_tokens': len(prompt)//4,
            'completion_tokens': 32,
            'total_tokens': len(prompt)//4 + 32
        },
    }
```

### Key Features

1. **Realistic Metadata Structure**
   - Each provider has correct metadata format
   - Fingerprints match expected patterns
   - Azure deliberately empty to test fallbacks

2. **Echo with Context**
   - Response includes provider and model info
   - Shows first 240 chars of prompt
   - Helps debug what was sent

3. **Usage Metrics**
   - Includes token counts
   - Simulates real API responses
   - Useful for cost estimation testing

## Integration in Run Endpoint

### Flow Through the Pipeline

```python
@router.post("/{template_id}/run")
def run_template(template_id: str, req: RunTemplateRequest):
    # 1. Get template and infer provider
    provider = tpl.provider or infer_provider(tpl.model_id)
    
    # 2. Generate fake LLM response with metadata
    response = _fake_llm_response(provider, tpl.model_id, req.rendered_prompt)
    
    # 3. Extract fingerprint from response metadata
    system_fingerprint, pvk_from_resp = extract_fingerprint(
        response, provider=provider, model_id=tpl.model_id
    )
    
    # 4. Ensure version (gets canonical provider_version_key)
    ver = ensure_version_service(...)
    provider_version_key = ver["provider_version_key"]
    
    # 5. Store result with both keys
    result = PromptResult(
        provider_version_key=provider_version_key,  # Canonical from service
        system_fingerprint=system_fingerprint,       # Extracted from response
        ...
    )
```

### Important Design Decision

The router **always uses the canonical `provider_version_key`** from `ensure_version_service` when storing results:
```python
provider_version_key = ver["provider_version_key"]  # Always use service's key
```

This ensures consistency even if the response fingerprint differs or is missing.

## Testing Different Providers

### OpenAI Example
```bash
curl -X POST http://localhost:8000/api/prompt-templates/{id}/run \
  -d '{"rendered_prompt": "Test OpenAI"}'

# Response will include:
# - system_fingerprint: "fp_stub_12345678"
# - provider_version_key from ensure_version_service
```

### Gemini Example
```bash
# Create template with Gemini model
curl -X POST http://localhost:8000/api/prompt-templates \
  -d '{"model_id": "gemini-pro", ...}'

# Run it
curl -X POST http://localhost:8000/api/prompt-templates/{id}/run \
  -d '{"rendered_prompt": "Test Gemini"}'

# Response metadata will have modelVersion: "gemini-pro-stub-001"
```

### Azure OpenAI (Testing Fallback)
```bash
# Create with Azure provider
curl -X POST http://localhost:8000/api/prompt-templates \
  -d '{"provider": "azure-openai", "model_id": "gpt-4", ...}'

# Run it - metadata will be empty, testing fallback to service key
```

## Benefits for Development

### 1. Complete Local Testing
- No API keys needed
- No network calls
- Instant responses
- Predictable results

### 2. Fingerprint Verification
```python
# You can see the complete flow:
1. Fake LLM generates fingerprint
2. extract_fingerprint() pulls it from metadata
3. ensure_version_service() provides canonical key
4. Both stored in PromptResult
5. Metrics track everything
```

### 3. Provider Behavior Testing
- Test each provider's metadata format
- Verify fallback handling
- Check version key consistency
- Validate extraction logic

## Metrics Integration

The fake LLM works seamlessly with metrics:
```python
# After storing result
try:
    record_result_insert(bool(system_fingerprint))
except Exception:
    pass
```

This tracks:
- Total results inserted
- Fingerprint presence rate
- Provider-specific patterns

## Replacing with Real LLM

For production, replace the fake LLM call:

```python
# Replace this line:
response = _fake_llm_response(provider, tpl.model_id, req.rendered_prompt)

# With your actual LLM adapter:
from app.llm.langchain_adapter import LangChainAdapter
adapter = LangChainAdapter()

if provider == "openai":
    response = await adapter.analyze_with_gpt4(
        req.rendered_prompt,
        model_name=tpl.model_id,
        **canonical.get("inference_params", {})
    )
elif provider == "google":
    response = await adapter.analyze_with_gemini(...)
# etc.
```

## Testing the Complete Flow

### 1. Create Template
```python
template = {
    "workspace_id": "test-ws",
    "name": "Test Template",
    "user_prompt_template": "Hello {{name}}",
    "model_id": "gpt-4o",
    "inference_params": {"temperature": 0.7}
}
```

### 2. Run Template
```python
run_request = {
    "rendered_prompt": "Hello Claude",
    "brand_name": "Test Brand"
}
```

### 3. Verify Results
```python
# Response includes:
{
    "result_id": "...",
    "version_id": "...",
    "provider_version_key": "fp_stub_abc12345",  # From service
    "system_fingerprint": "fp_stub_abc12345",    # From fake LLM
    "created_at": "..."
}
```

### 4. Check Metrics
```bash
curl http://localhost:8000/metrics | grep prompter
# prompter_prompt_results_insert_total 1
# prompter_openai_fingerprint_present_total 1
```

## File Version Clarification

The router versions progression:
1. `prompter_router_min.py` - Base implementation
2. `prompter_router_min v2.py` - Added metrics integration
3. **`prompter_router_min_v3.py`** - Added fake LLM (LATEST)

**Use `prompter_router_min_v3.py` for the most complete implementation.**

## Summary

The fake LLM integration provides:
- ✅ **Complete local testing** without external dependencies
- ✅ **Realistic metadata** for each provider
- ✅ **Fingerprint flow** visible end-to-end
- ✅ **Fallback testing** for missing metadata
- ✅ **Instant responses** for rapid development
- ✅ **Metrics integration** tracking all operations

This final enhancement completes the development experience, allowing you to test the entire V7 implementation locally without any external API calls while maintaining realistic behavior that matches production patterns.