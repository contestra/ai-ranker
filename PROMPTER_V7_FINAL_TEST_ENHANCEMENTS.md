# Prompter V7 Final Test Enhancements
## Complete Test Coverage with Fingerprint and Metrics Validation

**File**: `test_prompter_router_min_v2.py`  
**Status**: Enhanced test suite with fingerprint and metrics assertions  
**Purpose**: Verify the complete flow including fake LLM fingerprints and metrics endpoint

## Overview

The external model provided final test enhancements that:
- Verify system fingerprints flow through correctly
- Assert OpenAI fingerprints are captured
- Test the metrics endpoint exists and works
- Provide complete end-to-end validation

## Enhanced Test Coverage

### 1. System Fingerprint Assertion

The updated `test_run_route_creates_result` now verifies fingerprints:

```python
def test_run_route_creates_result(client: TestClient, patch_version_service):
    """Test that /run endpoint creates result with system_fingerprint for OpenAI"""
    
    # Create and run template...
    r = client.post(f"/api/prompt-templates/{template_id}/run", json=run_req)
    out = r.json()
    
    # Basic assertions
    assert out["result_id"]
    assert out["version_id"] == "00000000-0000-0000-0000-000000000001"
    assert out["provider_version_key"] == "stub-pvk"
    
    # NEW: Assert system_fingerprint is present for OpenAI
    assert "system_fingerprint" in out
    assert out["system_fingerprint"] is not None
    assert out["system_fingerprint"].startswith("fp_stub_"), \
        f"Expected OpenAI fingerprint to start with 'fp_stub_', got: {out['system_fingerprint']}"
```

### Key Validations

1. **Fingerprint Exists**: Verifies the field is present in response
2. **Not None**: Ensures it has a value (not null)
3. **Correct Format**: Validates it starts with `fp_stub_` (our fake LLM pattern)
4. **Descriptive Error**: Clear message if assertion fails

### 2. Metrics Endpoint Test

New test to verify Prometheus metrics are exposed:

```python
def test_metrics_endpoint_exists(client: TestClient):
    """Test that /metrics endpoint responds successfully"""
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers.get("content-type", "")
    
    # Check for key metrics
    metrics_text = r.text
    assert "starlette_requests_total" in metrics_text
    assert "prompter_probe_attempts_total" in metrics_text
    assert "prompter_prompt_results_insert_total" in metrics_text
```

### Verifications

1. **Endpoint Exists**: Returns 200 OK
2. **Correct Content Type**: text/plain for Prometheus
3. **HTTP Metrics**: `starlette_requests_total` present
4. **Domain Metrics**: Probe and result metrics present

## Complete Test Flow

### What Gets Tested End-to-End

```
1. Create Template
   ↓
2. Check for Duplicates (409 on same workspace)
   ↓
3. Verify Duplicate Check Endpoint
   ↓
4. Ensure Version (with stubbed service)
   ↓
5. Run Template
   ↓
6. Verify Result Contains:
   - result_id
   - version_id
   - provider_version_key
   - system_fingerprint (NEW!)
   ↓
7. Check Metrics Endpoint (NEW!)
```

## Running the Enhanced Tests

### Prerequisites
```bash
pip install pytest fastapi httpx sqlalchemy
```

### Run All Tests
```bash
# Using the enhanced test file
pytest test_prompter_router_min_v2.py -v

# Expected output:
test_create_template_and_duplicate_409 PASSED
test_check_duplicate_endpoint PASSED
test_ensure_version_stubbed PASSED
test_run_route_creates_result PASSED  # Now with fingerprint check
test_metrics_endpoint_exists PASSED    # NEW test
```

### Run Specific Test
```bash
# Test just the fingerprint flow
pytest test_prompter_router_min_v2.py::test_run_route_creates_result -v

# Test just metrics
pytest test_prompter_router_min_v2.py::test_metrics_endpoint_exists -v
```

## Provider-Specific Testing

### Testing Different Providers

You can extend the tests to verify provider-specific behavior:

```python
def test_gemini_model_version(client: TestClient, patch_version_service):
    """Test Gemini returns modelVersion instead of fingerprint"""
    payload = make_template_payload()
    payload["provider"] = "google"
    payload["model_id"] = "gemini-pro"
    
    created = create_and_expect_201(client, payload)
    # Run and verify modelVersion in metadata...

def test_azure_missing_fingerprint(client: TestClient, patch_version_service):
    """Test Azure OpenAI with missing fingerprint (fallback case)"""
    payload = make_template_payload()
    payload["provider"] = "azure-openai"
    
    # Should handle missing fingerprint gracefully...
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
name: Prompter V7 Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run enhanced tests
        run: |
          pytest test_prompter_router_min_v2.py -v --cov=prompter_router_min_v3
      
      - name: Check fingerprint flow
        run: |
          pytest test_prompter_router_min_v2.py::test_run_route_creates_result -v
```

## Benefits of Enhanced Tests

### 1. Complete Validation
- Verifies the entire pipeline works
- Confirms fingerprints flow through
- Validates metrics are exposed

### 2. Regression Prevention
- Catches if fingerprint extraction breaks
- Alerts if metrics disappear
- Ensures API contract stability

### 3. Documentation
- Tests serve as usage examples
- Show expected response format
- Demonstrate proper API usage

## Test File Versions

1. `test_prompter_router_min.py` - Original tests
2. **`test_prompter_router_min_v2.py`** - Enhanced with fingerprint + metrics (USE THIS)

## Troubleshooting

### Fingerprint Assertion Fails
```python
AssertionError: Expected OpenAI fingerprint to start with 'fp_stub_', got: None
```
**Solution**: Check that `prompter_router_min_v3.py` is being used (has fake LLM)

### Metrics Test Fails
```python
AssertionError: assert "starlette_requests_total" in metrics_text
```
**Solution**: Ensure `setup_metrics(app)` is called in the router

### Import Errors
```python
ModuleNotFoundError: No module named 'prompter_metrics'
```
**Solution**: Ensure all V7 files are in PYTHONPATH

## Summary

The enhanced test suite provides:
- ✅ **Fingerprint validation** for OpenAI responses
- ✅ **Metrics endpoint testing** for observability
- ✅ **Complete coverage** of all V7 features
- ✅ **Clear assertions** with descriptive errors
- ✅ **CI/CD ready** for automated testing
- ✅ **Extensible design** for provider-specific tests

These final test enhancements ensure that the complete V7 solution works end-to-end, from API requests through fingerprint extraction to metrics exposure. The tests validate that the fake LLM integration works correctly and that observability is properly configured.