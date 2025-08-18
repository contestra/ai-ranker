"""
Test actual functionality with real API calls
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_api_functionality():
    print("=" * 70)
    print("TESTING PROMPT TRACKING API FUNCTIONALITY")
    print("=" * 70)
    
    brand_name = "AVEA"
    results = []
    
    # Test 1: Create GPT-5 OFF template
    print("\n1. Creating GPT-5 OFF template...")
    template_data = {
        "template_name": "Test GPT-5 OFF",
        "prompt_text": "What is AVEA? Describe what you know about this brand.",
        "model_name": "gpt-5",
        "countries": ["US"],
        "grounding_modes": ["off"],
        "prompt_type": "recognition",
        "brand_name": brand_name
    }
    
    response = requests.post(f"{BASE_URL}/api/prompt-tracking/templates", json=template_data)
    if response.status_code in [200, 201]:
        gpt_template = response.json()
        print(f"   ✓ Created template ID: {gpt_template.get('id', 'unknown')}")
        results.append(("GPT-5 OFF template", "PASS"))
    else:
        print(f"   ✗ Failed: {response.status_code} - {response.text[:100]}")
        results.append(("GPT-5 OFF template", "FAIL"))
    
    # Test 2: Create Gemini Model Knowledge template
    print("\n2. Creating Gemini Model Knowledge template...")
    template_data = {
        "template_name": "Test Gemini Knowledge",
        "prompt_text": "What is AVEA? Describe what you know about this brand.",
        "model_name": "gemini-2.5-pro",
        "countries": ["US"],
        "grounding_modes": ["none"],  # Model Knowledge Only
        "prompt_type": "recognition",
        "brand_name": brand_name
    }
    
    response = requests.post(f"{BASE_URL}/api/prompt-tracking/templates", json=template_data)
    if response.status_code in [200, 201]:
        gemini_template = response.json()
        print(f"   ✓ Created template ID: {gemini_template.get('id', 'unknown')}")
        results.append(("Gemini Model Knowledge template", "PASS"))
    else:
        print(f"   ✗ Failed: {response.status_code} - {response.text[:100]}")
        results.append(("Gemini Model Knowledge template", "FAIL"))
    
    # Test 3: Run GPT-5 template
    print("\n3. Running GPT-5 OFF template...")
    if 'gpt_template' in locals():
        run_data = {
            "template_id": gpt_template['id'],
            "brand_name": brand_name
        }
        response = requests.post(f"{BASE_URL}/api/prompt-tracking/run", json=run_data)
        if response.status_code == 200:
            gpt_run = response.json()
            print(f"   ✓ Run ID: {gpt_run['run_id']}")
            print(f"   Status: {gpt_run.get('status', 'unknown')}")
            results.append(("GPT-5 run", "PASS"))
            
            # Wait for completion
            time.sleep(5)
            
            # Get results
            result_response = requests.get(f"{BASE_URL}/api/prompt-tracking/results/{gpt_run['run_id']}")
            if result_response.status_code == 200:
                result_data = result_response.json()
                print(f"   Model: {result_data.get('model_name')}")
                print(f"   Grounding: {result_data.get('grounding_mode')}")
                print(f"   Response length: {len(result_data.get('response', ''))} chars")
                if result_data.get('response'):
                    results.append(("GPT-5 response", "PASS"))
                else:
                    results.append(("GPT-5 response", "EMPTY"))
        else:
            print(f"   ✗ Failed to run: {response.status_code}")
            results.append(("GPT-5 run", "FAIL"))
    
    # Test 4: Run Gemini template
    print("\n4. Running Gemini Model Knowledge template...")
    if 'gemini_template' in locals():
        run_data = {
            "template_id": gemini_template['id'],
            "brand_name": brand_name
        }
        response = requests.post(f"{BASE_URL}/api/prompt-tracking/run", json=run_data)
        if response.status_code == 200:
            gemini_run = response.json()
            print(f"   ✓ Run ID: {gemini_run['run_id']}")
            print(f"   Status: {gemini_run.get('status', 'unknown')}")
            results.append(("Gemini run", "PASS"))
            
            # Wait for completion
            time.sleep(5)
            
            # Get results
            result_response = requests.get(f"{BASE_URL}/api/prompt-tracking/results/{gemini_run['run_id']}")
            if result_response.status_code == 200:
                result_data = result_response.json()
                print(f"   Model: {result_data.get('model_name')}")
                print(f"   Grounding: {result_data.get('grounding_mode')}")
                print(f"   Response length: {len(result_data.get('response', ''))} chars")
                if result_data.get('response'):
                    results.append(("Gemini response", "PASS"))
                else:
                    results.append(("Gemini response", "EMPTY"))
        else:
            print(f"   ✗ Failed to run: {response.status_code}")
            results.append(("Gemini run", "FAIL"))
    
    # Test 5: Get analytics
    print("\n5. Getting analytics...")
    response = requests.get(f"{BASE_URL}/api/prompt-tracking/analytics/{brand_name}")
    if response.status_code == 200:
        analytics = response.json()
        print(f"   Total runs: {analytics.get('total_runs', 0)}")
        print(f"   Mention rate: {analytics.get('overall_mention_rate', 0):.1f}%")
        print(f"   Avg confidence: {analytics.get('average_confidence', 0):.1f}%")
        results.append(("Analytics", "PASS"))
    else:
        print(f"   ✗ Failed: {response.status_code}")
        results.append(("Analytics", "FAIL"))
    
    # Test 6: List templates
    print("\n6. Listing templates...")
    response = requests.get(f"{BASE_URL}/api/prompt-tracking/templates?brand_name={brand_name}")
    if response.status_code == 200:
        data = response.json()
        # Handle both list and dict responses
        templates = data if isinstance(data, list) else data.get('templates', [])
        print(f"   Total templates: {len(templates) if isinstance(templates, list) else 0}")
        if isinstance(templates, list) and templates:
            for t in templates[:3]:
                print(f"   • {t.get('template_name', 'Unknown')} ({t.get('model_name', 'Unknown')}) - {t.get('grounding_modes', [])}")
        results.append(("List templates", "PASS"))
    else:
        print(f"   ✗ Failed: {response.status_code}")
        results.append(("List templates", "FAIL"))
    
    # Test 7: List runs
    print("\n7. Listing recent runs...")
    response = requests.get(f"{BASE_URL}/api/prompt-tracking/runs?brand_name={brand_name}&limit=5")
    if response.status_code == 200:
        data = response.json()
        # Handle both list and dict responses
        runs = data if isinstance(data, list) else data.get('runs', [])
        print(f"   Recent runs: {len(runs) if isinstance(runs, list) else 0}")
        if isinstance(runs, list) and runs:
            for r in runs[:3]:
                print(f"   • Run {r.get('id', '?')}: {r.get('status', '?')} - {r.get('model_name', 'unknown')}")
        results.append(("List runs", "PASS"))
    else:
        print(f"   ✗ Failed: {response.status_code}")
        results.append(("List runs", "FAIL"))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, status in results if status == "PASS")
    failed = sum(1 for _, status in results if status == "FAIL")
    empty = sum(1 for _, status in results if status == "EMPTY")
    
    print(f"\n✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Empty responses: {empty}")
    
    print("\nDetailed Results:")
    for test, status in results:
        symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠"
        print(f"   {symbol} {test}: {status}")
    
    return passed, failed, empty

if __name__ == "__main__":
    test_api_functionality()