"""
Debug test to see exactly what's being sent to the model
"""

import requests
import json
import time

# Create a test template
def create_test_template():
    response = requests.post(
        'http://localhost:8000/api/prompt-tracking/templates',
        json={
            'brand_name': 'AVEA',
            'template_name': 'Debug Location Test',
            'prompt_text': 'What are the top 3 longevity supplements?',
            'prompt_type': 'recognition',
            'countries': ['NONE', 'CH', 'US'],
            'grounding_modes': ['none']
        }
    )
    
    if response.ok:
        template_id = response.json()['id']
        print(f"Created template ID: {template_id}")
        return template_id
    else:
        print(f"Failed to create template: {response.status_code}")
        return None

# Run and analyze
def run_debug_test(template_id):
    print("\nRunning template with debugging...")
    response = requests.post(
        'http://localhost:8000/api/prompt-tracking/run',
        json={
            'template_id': template_id,
            'brand_name': 'AVEA',
            'model_name': 'gemini'
        },
        timeout=120
    )
    
    if not response.ok:
        print(f"Failed to run: {response.status_code}")
        if response.text:
            print(f"Error: {response.text}")
        return
    
    results = response.json()
    
    for result in results['results']:
        country = result['country']
        print(f"\n{'='*60}")
        print(f"COUNTRY: {country if country != 'NONE' else 'BASE MODEL (NONE)'}")
        print(f"{'='*60}")
        
        if 'error' in result:
            print(f"ERROR: {result['error']}")
            continue
            
        # Get full response details
        if result.get('run_id'):
            details_response = requests.get(
                f"http://localhost:8000/api/prompt-tracking/results/{result['run_id']}"
            )
            if details_response.ok:
                data = details_response.json()
                if data.get('result'):
                    response_text = data['result']['model_response']
                    prompt_text = data['result']['prompt_text']
                    
                    # Show the actual prompt sent
                    print("\nPROMPT SENT TO MODEL:")
                    print("-" * 40)
                    print(prompt_text[:500])
                    if len(prompt_text) > 500:
                        print("... [truncated]")
                    
                    # Analyze response
                    print("\nRESPONSE ANALYSIS:")
                    print("-" * 40)
                    
                    # Check for location markers
                    location_mentions = []
                    if 'location context' in response_text.lower():
                        location_mentions.append("EXPLICIT: 'location context' mentioned")
                    if 'switzerland' in response_text.lower() or 'swiss' in response_text.lower():
                        location_mentions.append("Switzerland/Swiss mentioned")
                    if 'chf' in response_text.lower():
                        location_mentions.append("CHF currency mentioned")
                    if 'migros' in response_text.lower():
                        location_mentions.append("Migros mentioned")
                    if 'swissmedic' in response_text.lower():
                        location_mentions.append("Swissmedic mentioned")
                    if 'united states' in response_text.lower() or ' us ' in response_text.lower():
                        location_mentions.append("United States/US mentioned")
                    if 'fda' in response_text.lower():
                        location_mentions.append("FDA mentioned")
                    if 'cvs' in response_text.lower():
                        location_mentions.append("CVS mentioned")
                    if '$' in response_text or 'usd' in response_text.lower():
                        location_mentions.append("USD currency mentioned")
                    
                    if location_mentions:
                        for mention in location_mentions:
                            print(f"  • {mention}")
                    else:
                        print("  No location markers found")
                    
                    # Show first part of response
                    print("\nRESPONSE PREVIEW:")
                    print("-" * 40)
                    print(response_text[:400])
                    if len(response_text) > 400:
                        print("... [truncated]")

if __name__ == "__main__":
    print("LOCATION INFERENCE DEBUG TEST")
    print("=" * 60)
    
    template_id = create_test_template()
    if template_id:
        time.sleep(1)
        run_debug_test(template_id)
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")