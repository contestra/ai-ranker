"""
Test if background processing fixes the DE leak issue.
Compares regular API vs background API execution.
"""

import requests
import json
import time

print("\n" + "="*80)
print("TESTING BACKGROUND PROCESSING FIX FOR DE LEAK")
print("="*80)

# Test configuration
BASE_URL = "http://localhost:8000"
TEMPLATE_ID = 26
BRAND_NAME = "AVEA"
MODEL_NAME = "gemini"
COUNTRIES = ["DE"]
GROUNDING_MODES = ["none"]

print(f"\nTest Configuration:")
print(f"- Template ID: {TEMPLATE_ID}")
print(f"- Brand: {BRAND_NAME}")
print(f"- Model: {MODEL_NAME}")
print(f"- Country: {COUNTRIES[0]}")
print(f"- Grounding: {GROUNDING_MODES[0]}")

# Test 1: Regular API (known to leak)
print("\n" + "-"*60)
print("TEST 1: Regular API (HTTP Context)")
print("-"*60)

try:
    response = requests.post(f'{BASE_URL}/api/prompt-tracking/run', json={
        'template_id': TEMPLATE_ID,
        'brand_name': BRAND_NAME,
        'model_name': MODEL_NAME,
        'countries': COUNTRIES,
        'grounding_modes': GROUNDING_MODES
    }, timeout=120)
    
    if response.ok:
        data = response.json()
        result = data['results'][0]
        response_text = result['response_preview']
        
        # Check for leaks
        leaks_found = []
        if 'DE' in response_text:
            leaks_found.append('DE')
        if 'Germany' in response_text:
            leaks_found.append('Germany')
        if 'Deutschland' in response_text:
            leaks_found.append('Deutschland')
        if 'location context' in response_text:
            leaks_found.append('location context')
        
        print(f"Status: Success")
        print(f"Response preview: {response_text[:100]}...")
        
        if leaks_found:
            print(f"[LEAK] Regular API: {', '.join(leaks_found)} found in response")
        else:
            print(f"[OK] Regular API: No leaks detected")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"Error calling regular API: {e}")

# Test 2: Background API (should not leak)
print("\n" + "-"*60)
print("TEST 2: Background API (Thread Context)")
print("-"*60)

try:
    response = requests.post(f'{BASE_URL}/api/prompt-tracking-background/run', json={
        'template_id': TEMPLATE_ID,
        'brand_name': BRAND_NAME,
        'model_name': MODEL_NAME,
        'countries': COUNTRIES,
        'grounding_modes': GROUNDING_MODES,
        'wait_for_completion': True  # Wait for results
    }, timeout=120)
    
    if response.ok:
        data = response.json()
        
        # Check if we got results or task info
        if 'results' in data:
            result = data['results'][0]
            response_text = result['response_preview']
            leak_detected = result.get('leak_detected', False)
            leak_terms = result.get('leak_terms', [])
            
            print(f"Status: Success")
            print(f"Response preview: {response_text[:100]}...")
            
            if leak_detected:
                print(f"[LEAK] Background API: {', '.join(leak_terms)} found in response")
            else:
                print(f"[OK] Background API: No leaks detected")
            
            # Show leak summary
            if 'leak_summary' in data:
                summary = data['leak_summary']
                print(f"\nLeak Summary:")
                print(f"- Total tests: {summary['total_tests']}")
                print(f"- Tests with leaks: {summary['tests_with_leaks']}")
                
        else:
            print("Got task info instead of results:")
            print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"Error calling background API: {e}")

# Test 3: Direct background test (no API at all)
print("\n" + "-"*60)
print("TEST 3: Direct Test (Python Script)")
print("-"*60)

import asyncio
import sys
sys.path.append('.')
from app.llm.langchain_adapter import LangChainAdapter
from app.services.als import als_service

async def direct_test():
    """Test directly without any API"""
    
    # Build Ambient Block
    ambient_block = als_service.build_als_block('DE')
    
    # Create adapter
    adapter = LangChainAdapter()
    
    # Call Gemini directly
    result = await adapter.analyze_with_gemini(
        'List the top 3 longevity supplements',
        use_grounding=False,
        model_name='gemini-2.5-pro',
        temperature=0.0,
        seed=42,
        context=ambient_block
    )
    
    response_text = result['content']
    
    # Check for leaks
    leaks_found = []
    if 'DE' in response_text:
        leaks_found.append('DE')
    if 'Germany' in response_text:
        leaks_found.append('Germany')
    if 'Deutschland' in response_text:
        leaks_found.append('Deutschland')
    if 'location context' in response_text:
        leaks_found.append('location context')
    
    print(f"Response preview: {response_text[:100]}...")
    
    if leaks_found:
        print(f"[LEAK] Direct test: {', '.join(leaks_found)} found in response")
    else:
        print(f"[OK] Direct test: No leaks detected")
    
    return leaks_found

direct_leaks = asyncio.run(direct_test())

# Final Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

print("""
Expected Results:
- Regular API (HTTP): Should LEAK (known issue)
- Background API (Thread): Should NOT leak (bypasses HTTP context)
- Direct Test (Script): Should NOT leak (no API involved)

If Background API still leaks, the issue is deeper than HTTP context.
If Background API doesn't leak, we've successfully bypassed the issue!
""")