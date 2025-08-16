"""
Test script to trigger token exhaustion and verify metadata capture
"""
import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_token_exhaustion():
    """Test with a prompt that should cause token exhaustion"""
    
    print("Testing token exhaustion scenario...")
    
    # Create a template with a complex prompt that needs lots of reasoning
    template_data = {
        "brand_name": "TestBrand",
        "template_name": f"Token Exhaustion Test {int(time.time())}",
        "prompt_text": "What are the most trusted companies in technology, healthcare, finance, retail, and automotive industries? Provide detailed analysis with specific examples, market share data, customer satisfaction scores, and explain the methodology for determining trust. Include at least 5 companies per industry with comprehensive justification.",
        "prompt_type": "test",
        "countries": ["US"],
        "grounding_modes": ["off"],
        "model_name": "gpt-5"  # GPT-5 with limited tokens should struggle
    }
    
    # Create and run template
    print("\n1. Creating complex template...")
    response = requests.post(f"{API_BASE}/api/prompt-tracking/templates", json=template_data)
    if not response.ok:
        print(f"   ERROR creating template: {response.text}")
        return
    
    template_id = response.json()['id']
    print(f"   Created template ID: {template_id}")
    
    print("\n2. Running template (this may take 30-60 seconds)...")
    run_data = {
        "template_id": template_id,
        "brand_name": "TestBrand",
        "countries": ["US"],
        "grounding_modes": ["off"],
        "model_name": "gpt-5"
    }
    
    run_response = requests.post(f"{API_BASE}/api/prompt-tracking/run", json=run_data)
    if not run_response.ok:
        print(f"   ERROR running template: {run_response.text}")
        return
    
    results = run_response.json().get('results', [])
    if not results:
        print("   ERROR: No results returned")
        return
    
    run_id = results[0]['run_id']
    print(f"   Run completed, ID: {run_id}")
    
    # Get detailed results
    print("\n3. Checking metadata...")
    details = requests.get(f"{API_BASE}/api/prompt-tracking/results/{run_id}")
    if details.ok:
        result = details.json().get('result', {})
        
        print(f"   finish_reason: {result.get('finish_reason')}")
        print(f"   content_filtered: {result.get('content_filtered')}")
        print(f"   Response length: {len(result.get('model_response', ''))}")
        
        if result.get('finish_reason') == 'length':
            print("\n   TOKEN EXHAUSTION DETECTED!")
            print("   This indicates the model ran out of tokens before completing.")
        elif result.get('content_filtered'):
            print("\n   CONTENT FILTERING DETECTED!")
        else:
            print("\n   Normal completion (finish_reason: stop)")
            
        # Show response preview
        response_text = result.get('model_response', '')
        if response_text:
            print(f"\n   Response preview: {response_text[:300]}...")
        else:
            print("\n   Response was empty")

if __name__ == "__main__":
    test_token_exhaustion()