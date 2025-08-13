"""
Quick test to verify location inference is working
"""

import requests
import json
import time

# Create a simple test template
def create_test_template():
    response = requests.post(
        'http://localhost:8000/api/prompt-tracking/templates',
        json={
            'brand_name': 'AVEA',
            'template_name': 'Quick Location Test',
            'prompt_text': 'What are the most popular longevity supplements?',
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

# Run the template
def run_test(template_id):
    print("\nRunning template...")
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
        return
    
    results = response.json()
    print(f"\nTemplate: {results['template_name']}")
    print("=" * 60)
    
    for result in results['results']:
        country = result['country']
        print(f"\n[{country if country != 'NONE' else 'BASE MODEL'}]")
        print("-" * 40)
        
        if 'error' in result:
            print(f"Error: {result['error']}")
        else:
            # Get full response
            if result.get('run_id'):
                full_response = requests.get(
                    f"http://localhost:8000/api/prompt-tracking/results/{result['run_id']}"
                )
                if full_response.ok:
                    data = full_response.json()
                    if data.get('result'):
                        response_text = data['result']['model_response']
                        
                        # Check for location-specific markers
                        markers_found = []
                        
                        # Swiss markers
                        if country == 'CH':
                            swiss_markers = ['CHF', 'Swiss', 'Switzerland', 'Migros', 'Swissmedic']
                            for marker in swiss_markers:
                                if marker.lower() in response_text.lower():
                                    markers_found.append(marker)
                        
                        # US markers
                        elif country == 'US':
                            us_markers = ['$', 'USD', 'FDA', 'CVS', 'United States']
                            for marker in us_markers:
                                if marker.lower() in response_text.lower():
                                    markers_found.append(marker)
                        
                        # Display results
                        if country == 'NONE':
                            # Check that base model has no location markers
                            all_markers = ['CHF', 'Swiss', 'Migros', '$', 'USD', 'FDA', 'CVS']
                            found = [m for m in all_markers if m.lower() in response_text.lower()]
                            if found:
                                print(f"[WARNING] Base model contains: {found}")
                            else:
                                print("[OK] Base model is location-neutral")
                        else:
                            if markers_found:
                                print(f"[SUCCESS] Location markers found: {markers_found}")
                            else:
                                print("[FAIL] No location markers found")
                        
                        # Show first 300 chars of response
                        print(f"\nResponse preview:")
                        print(response_text[:300])
                        
                        # Check if model explicitly mentions context
                        if 'location context' in response_text.lower() or 'based on the context' in response_text.lower():
                            print("\n[NOTE] Model explicitly mentions receiving context")

# Main execution
if __name__ == "__main__":
    print("LOCATION INFERENCE QUICK TEST")
    print("=" * 60)
    
    template_id = create_test_template()
    if template_id:
        time.sleep(2)  # Small delay before running
        run_test(template_id)
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("\nExpected behavior:")
    print("- BASE MODEL: Should be location-neutral")
    print("- CH: Should mention CHF, Swiss retailers, or Swissmedic")
    print("- US: Should mention USD, US retailers, or FDA")
    print("\nIf the model explicitly mentions 'location context',")
    print("it's being too obvious about the evidence pack.")