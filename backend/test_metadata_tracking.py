"""
Test script to verify finish_reason and content_filtered metadata tracking
"""
import asyncio
import requests
import json

API_BASE = "http://localhost:8000"

async def test_metadata_tracking():
    """Test that finish_reason and content_filtered are properly captured"""
    
    print("Testing metadata tracking...")
    
    # First, create a test template that will trigger token exhaustion
    template_data = {
        "brand_name": "AVEA",
        "template_name": "Test Metadata Tracking",
        "prompt_text": "What are the most trusted longevity supplement brands?",  # This should trigger filtering/token issues with GPT-5
        "prompt_type": "test",
        "countries": ["US"],
        "grounding_modes": ["off"],
        "model_name": "gpt-5"  # GPT-5 has token issues with this prompt
    }
    
    # Create template
    print("\n1. Creating test template...")
    response = requests.post(f"{API_BASE}/api/prompt-tracking/templates", json=template_data)
    if response.status_code == 409:
        print("   Template already exists, that's okay")
        # Get existing template
        templates = requests.get(f"{API_BASE}/api/prompt-tracking/templates?brand_name=AVEA").json()
        template_id = next((t['id'] for t in templates['templates'] if t['template_name'] == template_data['template_name']), None)
    else:
        template_id = response.json()['id']
        print(f"   Created template ID: {template_id}")
    
    # Run the template
    print("\n2. Running template to test metadata capture...")
    run_data = {
        "template_id": template_id,
        "brand_name": "AVEA",
        "countries": ["US"],
        "grounding_modes": ["off"],
        "model_name": "gpt-5"
    }
    
    run_response = requests.post(f"{API_BASE}/api/prompt-tracking/run", json=run_data)
    if not run_response.ok:
        print(f"   ERROR: Failed to run template: {run_response.text}")
        return
    
    run_result = run_response.json()
    print(f"   Run completed for template: {run_result['template_name']}")
    
    # Get the run ID from results
    if run_result.get('results') and len(run_result['results']) > 0:
        run_id = run_result['results'][0]['run_id']
        print(f"   Run ID: {run_id}")
        
        # Fetch detailed results
        print("\n3. Fetching detailed results with metadata...")
        result_response = requests.get(f"{API_BASE}/api/prompt-tracking/results/{run_id}")
        if result_response.ok:
            detailed = result_response.json()
            result = detailed.get('result', {})
            
            print("\n   === METADATA CAPTURED ===")
            print(f"   finish_reason: {result.get('finish_reason', 'NOT CAPTURED')}")
            print(f"   content_filtered: {result.get('content_filtered', 'NOT CAPTURED')}")
            print(f"   Response length: {len(result.get('model_response', ''))}")
            
            if result.get('finish_reason') or result.get('content_filtered') is not None:
                print("\n   SUCCESS: Metadata is being captured!")
            else:
                print("\n   WARNING: Metadata fields are empty (might be a normal completion)")
                
            # Show first 200 chars of response
            response_text = result.get('model_response', '')
            if response_text:
                print(f"\n   Response preview: {response_text[:200]}...")
            else:
                print("\n   Response was empty (likely filtered or token exhaustion)")
                
    else:
        print("   ERROR: No results returned from run")
    
    # Now test with a normal prompt that should complete successfully
    print("\n4. Testing with normal prompt (should complete successfully)...")
    template_data2 = {
        "brand_name": "AVEA",
        "template_name": "Test Normal Completion",
        "prompt_text": "List 5 colors",
        "prompt_type": "test",
        "countries": ["US"],
        "grounding_modes": ["off"],
        "model_name": "gemini"  # Gemini should handle this fine
    }
    
    response2 = requests.post(f"{API_BASE}/api/prompt-tracking/templates", json=template_data2)
    if response2.status_code == 409:
        templates = requests.get(f"{API_BASE}/api/prompt-tracking/templates?brand_name=AVEA").json()
        template_id2 = next((t['id'] for t in templates['templates'] if t['template_name'] == template_data2['template_name']), None)
    else:
        template_id2 = response2.json()['id']
    
    run_data2 = {
        "template_id": template_id2,
        "brand_name": "AVEA",
        "countries": ["US"],
        "grounding_modes": ["off"],
        "model_name": "gemini"
    }
    
    run_response2 = requests.post(f"{API_BASE}/api/prompt-tracking/run", json=run_data2)
    if run_response2.ok and run_response2.json().get('results'):
        run_id2 = run_response2.json()['results'][0]['run_id']
        result_response2 = requests.get(f"{API_BASE}/api/prompt-tracking/results/{run_id2}")
        if result_response2.ok:
            result2 = result_response2.json().get('result', {})
            print(f"   finish_reason: {result2.get('finish_reason', 'NOT CAPTURED')}")
            print(f"   content_filtered: {result2.get('content_filtered', False)}")
            print(f"   Response preview: {result2.get('model_response', '')[:100]}...")

if __name__ == "__main__":
    asyncio.run(test_metadata_tracking())