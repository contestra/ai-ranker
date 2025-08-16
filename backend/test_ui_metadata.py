"""
Create some test data to verify UI metadata display
"""
import requests
import time

API_BASE = "http://localhost:8000"

# Test 1: Normal completion with Gemini
print("Creating test scenarios for UI verification...")

template1 = {
    "brand_name": "UITest",
    "template_name": f"Normal Completion Test",
    "prompt_text": "List 3 popular smartphone brands",
    "prompt_type": "test",
    "countries": ["US"],
    "grounding_modes": ["off"],
    "model_name": "gemini"
}

r1 = requests.post(f"{API_BASE}/api/prompt-tracking/templates", json=template1)
if r1.ok:
    tid1 = r1.json()['id']
    print(f"1. Created normal test template (ID: {tid1})")
    
    # Run it
    run1 = requests.post(f"{API_BASE}/api/prompt-tracking/run", json={
        "template_id": tid1,
        "brand_name": "UITest",
        "countries": ["US"],
        "grounding_modes": ["off"],
        "model_name": "gemini"
    })
    if run1.ok:
        print("   Ran successfully - should show normal completion in UI")

print("\nTest data created! Check the UI:")
print("1. Go to http://localhost:3001")
print("2. Navigate to Prompt Tracking tab")
print("3. Go to Results sub-tab")
print("4. Look for 'UITest' runs")
print("5. Click 'View Response' to see metadata display")
print("\nExpected:")
print("- Normal completion should show green 'Response completed normally'")
print("- Timeout errors should show the error message")
print("- Any filtered content would show yellow warning box")