"""
Test script for Prompt Tracking integration
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api/prompt-tracking"
BRAND_NAME = "AVEA"

def test_create_template():
    """Create a test template"""
    template_data = {
        "brand_name": BRAND_NAME,
        "template_name": "Brand Recognition Test",
        "prompt_text": "What do you know about {brand_name} and their products? List the main products and services.",
        "prompt_type": "recognition",
        "countries": ["US", "CH", "DE"],
        "grounding_modes": ["none", "web"],
        "is_active": True
    }
    
    response = requests.post(f"{BASE_URL}/templates", json=template_data)
    if response.ok:
        result = response.json()
        print(f"SUCCESS: Created template with ID: {result['id']}")
        return result['id']
    else:
        print(f"FAILED: Could not create template: {response.text}")
        return None

def test_get_templates():
    """Get templates for brand"""
    response = requests.get(f"{BASE_URL}/templates?brand_name={BRAND_NAME}")
    if response.ok:
        data = response.json()
        print(f"SUCCESS: Found {len(data['templates'])} templates")
        for template in data['templates']:
            print(f"  - {template['template_name']} (ID: {template['id']})")
        return data['templates']
    else:
        print(f"FAILED: Could not get templates: {response.text}")
        return []

def test_run_prompt(template_id):
    """Run a prompt test"""
    run_data = {
        "template_id": template_id,
        "brand_name": BRAND_NAME,
        "model_name": "gemini"
    }
    
    print(f"Running prompt test for template {template_id}...")
    response = requests.post(f"{BASE_URL}/run", json=run_data)
    
    if response.ok:
        data = response.json()
        print(f"SUCCESS: Prompt test completed")
        print(f"  Template: {data['template_name']}")
        print(f"  Brand: {data['brand_name']}")
        print(f"  Results: {len(data['results'])} tests")
        
        for result in data['results']:
            print(f"\n  Test: {result['country']} / {result['grounding_mode']}")
            if 'error' in result:
                print(f"    ERROR: {result['error']}")
            else:
                print(f"    Brand mentioned: {result['brand_mentioned']}")
                print(f"    Mention count: {result['mention_count']}")
                if result['response_preview']:
                    print(f"    Response preview: {result['response_preview'][:100]}...")
        return data
    else:
        print(f"FAILED: Could not run prompt: {response.text}")
        return None

def test_get_analytics():
    """Get analytics for brand"""
    response = requests.get(f"{BASE_URL}/analytics/{BRAND_NAME}")
    
    if response.ok:
        data = response.json()
        print(f"\nAnalytics for {BRAND_NAME}:")
        print(f"  Total runs: {data['statistics']['total_runs']}")
        print(f"  Successful: {data['statistics']['successful_runs']}")
        print(f"  Failed: {data['statistics']['failed_runs']}")
        print(f"  Mention rate: {data['statistics']['mention_rate']:.1f}%")
        print(f"  Avg mentions: {data['statistics']['avg_mentions_per_response']:.1f}")
        print(f"  Avg confidence: {data['statistics']['avg_confidence']:.0f}%")
        
        if data['grounding_comparison']:
            print("\n  Grounding Mode Comparison:")
            for mode, stats in data['grounding_comparison'].items():
                print(f"    {mode}: {stats['mention_rate']:.1f}% ({stats['run_count']} runs)")
        
        if data['country_comparison']:
            print("\n  Country Comparison:")
            for country, stats in data['country_comparison'].items():
                print(f"    {country}: {stats['mention_rate']:.1f}% ({stats['run_count']} runs)")
        
        return data
    else:
        print(f"FAILED: Could not get analytics: {response.text}")
        return None

def main():
    print("=" * 60)
    print("Testing Prompt Tracking Integration")
    print("=" * 60)
    
    # Test 1: Create a template
    print("\n1. Creating template...")
    template_id = test_create_template()
    
    if not template_id:
        print("Cannot continue without template ID")
        return
    
    time.sleep(1)
    
    # Test 2: Get templates
    print("\n2. Getting templates...")
    templates = test_get_templates()
    
    # Test 3: Run prompt test
    print("\n3. Running prompt test...")
    run_result = test_run_prompt(template_id)
    
    if run_result:
        # Give some time for the results to be processed
        time.sleep(2)
        
        # Test 4: Get analytics
        print("\n4. Getting analytics...")
        test_get_analytics()
    
    print("\n" + "=" * 60)
    print("Integration test completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()