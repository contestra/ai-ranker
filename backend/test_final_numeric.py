"""Final test of numeric country codes through the API"""

import requests
import json

print("\n" + "="*80)
print("FINAL TEST: Numeric Country Codes")
print("="*80)

# Make the API call
response = requests.post('http://localhost:8000/api/prompt-tracking/run', json={
    'template_id': 26,
    'brand_name': 'AVEA',
    'model_name': 'gemini',
    'countries': ['DE'],  # API accepts ISO
    'grounding_modes': ['none']
}, timeout=120)

if response.ok:
    data = response.json()
    result = data['results'][0]
    
    print("\nAPI Response:")
    print(f"- Run ID: {result['run_id']}")
    print(f"- Country returned: {result['country']}")
    print(f"- Model: gemini")
    
    response_text = result['response_preview']
    
    print("\n--- Response Text (first 600 chars) ---")
    print(response_text[:600])
    
    print("\n--- Leak Analysis ---")
    leaks_found = []
    
    # Check for specific leak indicators
    if 'DE' in response_text:
        leaks_found.append('DE')
        # Find where it appears
        idx = response_text.find('DE')
        print(f"[LEAK] Found 'DE' at position {idx}")
        print(f"  Context: ...{response_text[max(0, idx-20):idx+30]}...")
    
    if 'Germany' in response_text:
        leaks_found.append('Germany')
        idx = response_text.find('Germany')
        print(f"[LEAK] Found 'Germany' at position {idx}")
        print(f"  Context: ...{response_text[max(0, idx-20):idx+30]}...")
        
    if 'Deutschland' in response_text:
        leaks_found.append('Deutschland')
        
    if 'location context' in response_text:
        leaks_found.append('location context')
        idx = response_text.find('location context')
        print(f"[LEAK] Found 'location context' at position {idx}")
        print(f"  Context: ...{response_text[max(0, idx-20):idx+50]}...")
    
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    
    if leaks_found:
        print(f"[X] FAILED: Leaks detected: {', '.join(leaks_found)}")
        print("\nThe numeric country codes are NOT preventing the leak.")
        print("The issue appears to be at a deeper level than we can control.")
    else:
        print("[OK] SUCCESS: No leaks detected!")
        print("The numeric country codes are working correctly.")
else:
    print(f"Error: {response.status_code}")
    print(response.text)