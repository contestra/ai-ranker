"""Test the API endpoint directly to see debug output"""

import requests
import json

# Test with Germany
response = requests.post('http://localhost:8000/api/prompt-tracking/run', json={
    'template_id': 26,  # Debug Location Test
    'brand_name': 'AVEA',
    'model_name': 'gemini',
    'countries': ['DE'],
    'grounding_modes': ['none']
}, timeout=120)

if response.ok:
    data = response.json()
    result = data['results'][0]
    
    print("\n" + "="*80)
    print("API RESPONSE ANALYSIS")
    print("="*80)
    
    print(f"\nCountry tested: {result['country']}")
    print(f"Model: gemini")
    print(f"Brand mentioned: {result['brand_mentioned']}")
    print(f"Mention count: {result['mention_count']}")
    
    print("\n--- Response Text (first 600 chars) ---")
    print(result['response_preview'][:600])
    
    # Check for DE leak
    response_text = result['response_preview']
    leak_indicators = ['DE', 'Germany', 'Deutschland', 'location context']
    
    print("\n--- Leak Analysis ---")
    for indicator in leak_indicators:
        if indicator in response_text:
            print(f"[LEAK] Found '{indicator}' in response")
            # Find the sentence
            sentences = response_text.split('.')
            for sentence in sentences:
                if indicator in sentence:
                    print(f"   -> {sentence.strip()[:100]}...")
                    break
    
    # Get full result details
    if 'run_id' in result:
        full_response = requests.get(f'http://localhost:8000/api/prompt-tracking/results/{result["run_id"]}')
        if full_response.ok:
            full_data = full_response.json()
            prompt_text = full_data['result']['prompt_text']
            
            print("\n--- Prompt Sent ---")
            print(prompt_text[:200])
            
            # Check if prompt contains DE
            if 'DE' in prompt_text or 'Germany' in prompt_text:
                print("\n[WARNING] Prompt itself contains location identifiers!")
else:
    print(f"Error: {response.status_code}")
    print(response.text)