# GPT-5 Known Issues and Requirements

## CRITICAL: GPT-5 Temperature Requirement

**GPT-5 models ONLY support temperature = 1.0 (default)**

This is a hard requirement from OpenAI. Any other temperature value will result in:
```
Error code: 400 - {'error': {'message': "Unsupported value: 'temperature' does not support 0.0 with this model. Only the default (1) value is supported."}}
```

### Affected Models:
- `gpt-5`
- `gpt-5-mini`
- `gpt-5-nano`

### NOT Affected:
- `gpt-4o` - Supports any temperature
- `gpt-4o-mini` - Supports any temperature

## Empty Response Issue

As of August 2025, all GPT-5 models return empty responses through the API, even with correct temperature settings. This appears to be an OpenAI-side issue.

### Workaround:
Use `gpt-4o` or Google Gemini models instead.

## Model Initialization Issue (FIXED)

**Problem**: The LangChain adapter was hardcoded to use `gpt-4o` regardless of the requested model.

**Solution**: Dynamic model initialization based on the `model_name` parameter:
```python
model = ChatOpenAI(
    model=model_name,  # Now uses the requested model
    temperature=1.0 if 'gpt-5' in model_name else temperature,
    api_key=settings.openai_api_key
)
```

## Summary

1. **Always use temperature=1.0 for GPT-5 models**
2. **GPT-5 models currently return empty responses (OpenAI issue)**
3. **Use gpt-4o or Gemini as alternatives**

Last updated: August 12, 2025