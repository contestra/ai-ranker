"""
Test all grounding modes for GPT-5 and Gemini
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_all_modes():
    print("=" * 70)
    print("TESTING ALL GROUNDING MODES")
    print("=" * 70)
    
    brand_name = "AVEA"
    test_results = []
    
    # Test configurations
    test_configs = [
        # GPT-5 modes
        {"name": "GPT-5 PREFERRED", "model": "gpt-5", "modes": ["preferred"]},
        {"name": "GPT-5 REQUIRED", "model": "gpt-5", "modes": ["required"]},
        # Gemini modes
        {"name": "Gemini Grounded", "model": "gemini-2.5-pro", "modes": ["web"]},
        {"name": "Gemini Multi-Mode", "model": "gemini-2.5-pro", "modes": ["none", "web"]},
    ]
    
    for config in test_configs:
        print(f"\n{'='*50}")
        print(f"Testing: {config['name']}")
        print('='*50)
        
        # Create template
        template_data = {
            "template_name": f"Test {config['name']}",
            "prompt_text": "What is AVEA? Describe what you know about this brand.",
            "model_name": config['model'],
            "countries": ["US"],
            "grounding_modes": config['modes'],
            "prompt_type": "recognition",
            "brand_name": brand_name
        }
        
        print(f"Creating template...")
        response = requests.post(f"{BASE_URL}/api/prompt-tracking/templates", json=template_data)
        
        if response.status_code in [200, 201]:
            template = response.json()
            template_id = template.get('id')
            print(f"✓ Template created: ID {template_id}")
            test_results.append((config['name'], "Template", "PASS"))
            
            # Run the template
            print(f"Running template...")
            run_data = {
                "template_id": template_id,
                "brand_name": brand_name
            }
            
            run_response = requests.post(f"{BASE_URL}/api/prompt-tracking/run", json=run_data)
            
            if run_response.status_code == 200:
                run_result = run_response.json()
                run_id = run_result.get('run_id')
                print(f"✓ Run started: ID {run_id}")
                test_results.append((config['name'], "Run", "PASS"))
                
                # Wait for completion
                print("Waiting for completion...")
                time.sleep(10)
                
                # Get results
                result_response = requests.get(f"{BASE_URL}/api/prompt-tracking/results/{run_id}")
                if result_response.status_code == 200:
                    result_data = result_response.json()
                    
                    print(f"\nResults:")
                    print(f"  Status: {result_data.get('status', 'unknown')}")
                    print(f"  Model: {result_data.get('model_name', 'unknown')}")
                    print(f"  Grounding: {result_data.get('grounding_mode', 'unknown')}")
                    print(f"  Response length: {len(result_data.get('response', ''))} chars")
                    
                    if result_data.get('grounding_signals'):
                        print(f"  Grounding signals: {json.dumps(result_data['grounding_signals'], indent=2)[:200]}...")
                    
                    if result_data.get('response'):
                        print(f"  Response preview: {result_data['response'][:200]}...")
                        test_results.append((config['name'], "Response", "PASS"))
                    else:
                        print("  ⚠ Empty response")
                        test_results.append((config['name'], "Response", "EMPTY"))
                else:
                    print(f"✗ Failed to get results: {result_response.status_code}")
                    test_results.append((config['name'], "Response", "FAIL"))
            else:
                print(f"✗ Failed to run: {run_response.status_code}")
                test_results.append((config['name'], "Run", "FAIL"))
                
        elif response.status_code == 409:
            print(f"⚠ Template already exists (duplicate)")
            # Try to get existing template and run it
            list_response = requests.get(f"{BASE_URL}/api/prompt-tracking/templates?brand_name={brand_name}")
            if list_response.status_code == 200:
                templates = list_response.json()
                if isinstance(templates, dict):
                    templates = templates.get('templates', [])
                
                # Find matching template
                matching = [t for t in templates if config['name'] in t.get('template_name', '')]
                if matching:
                    template_id = matching[0]['id']
                    print(f"Using existing template: ID {template_id}")
                    
                    # Run it
                    run_data = {
                        "template_id": template_id,
                        "brand_name": brand_name
                    }
                    
                    run_response = requests.post(f"{BASE_URL}/api/prompt-tracking/run", json=run_data)
                    if run_response.status_code == 200:
                        run_result = run_response.json()
                        run_id = run_result.get('run_id')
                        print(f"✓ Run started: ID {run_id}")
                        test_results.append((config['name'], "Run", "PASS"))
                    else:
                        print(f"✗ Failed to run: {run_response.status_code}")
                        test_results.append((config['name'], "Run", "FAIL"))
        else:
            print(f"✗ Failed to create: {response.status_code}")
            test_results.append((config['name'], "Template", "FAIL"))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, _, status in test_results if status == "PASS")
    failed = sum(1 for _, _, status in test_results if status == "FAIL")
    empty = sum(1 for _, _, status in test_results if status == "EMPTY")
    
    print(f"\n✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Empty: {empty}")
    
    print("\nDetailed Results:")
    for name, test_type, status in test_results:
        symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠"
        print(f"  {symbol} {name} - {test_type}: {status}")
    
    return passed, failed, empty

if __name__ == "__main__":
    test_all_modes()