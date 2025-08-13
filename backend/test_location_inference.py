"""
Comprehensive test suite for location inference from evidence packs
Tests whether models can infer geographic location from context without being told
"""

import requests
import json
from typing import Dict, List
import time

def create_test_templates():
    """Create various test templates to showcase location inference"""
    
    templates = [
        {
            'template_name': 'Generic Question Test',
            'prompt_text': 'What are the most popular longevity supplements?',
            'prompt_type': 'recognition',
            'countries': ['NONE', 'CH', 'US', 'DE'],
            'grounding_modes': ['none']
        },
        {
            'template_name': 'Price Sensitive Test',
            'prompt_text': 'What do longevity supplements typically cost?',
            'prompt_type': 'recognition',
            'countries': ['NONE', 'CH', 'US'],
            'grounding_modes': ['none']
        },
        {
            'template_name': 'Where to Buy Test',
            'prompt_text': 'Where can I buy quality longevity supplements?',
            'prompt_type': 'recognition',
            'countries': ['NONE', 'CH', 'US', 'DE'],
            'grounding_modes': ['none']
        },
        {
            'template_name': 'Regulation Aware Test',
            'prompt_text': 'Are there any regulations I should know about for longevity supplements?',
            'prompt_type': 'recognition',
            'countries': ['NONE', 'CH', 'US'],
            'grounding_modes': ['none']
        },
        {
            'template_name': 'Brand Recognition Test',
            'prompt_text': 'What are the leading brands in longevity supplements? Have you heard of {brand_name}?',
            'prompt_type': 'recognition',
            'countries': ['NONE', 'CH'],
            'grounding_modes': ['none']
        }
    ]
    
    created_templates = []
    for template in templates:
        response = requests.post(
            'http://localhost:8000/api/prompt-tracking/templates',
            json={
                'brand_name': 'AVEA',
                **template
            }
        )
        if response.ok:
            template_id = response.json()['id']
            created_templates.append({
                'id': template_id,
                'name': template['template_name']
            })
            print(f"[OK] Created template: {template['template_name']} (ID: {template_id})")
        else:
            print(f"[FAIL] Failed to create: {template['template_name']}")
    
    return created_templates

def analyze_location_inference(response_text: str, country: str) -> Dict:
    """Analyze response for location inference markers"""
    
    # Define location-specific markers
    markers = {
        'CH': {
            'currency': ['CHF', 'Swiss franc', 'francs'],
            'regulatory': ['Swissmedic', 'Swiss regulations', 'Swiss Federal'],
            'retailers': ['Migros', 'Coop', 'Swiss pharmacy'],
            'geographic': ['Switzerland', 'Swiss', 'Zurich', 'Geneva'],
            'language': ['Schweiz', 'Suisse']
        },
        'US': {
            'currency': ['$', 'USD', 'dollars'],
            'regulatory': ['FDA', 'Food and Drug Administration'],
            'retailers': ['CVS', 'Walgreens', 'Walmart', 'Amazon'],
            'geographic': ['United States', 'America', 'US'],
            'language': []
        },
        'DE': {
            'currency': ['€', 'EUR', 'Euro'],
            'regulatory': ['BfArM', 'German regulations'],
            'retailers': ['Apotheke', 'dm', 'Rossmann'],
            'geographic': ['Germany', 'German', 'Deutschland', 'Berlin'],
            'language': ['Nahrungsergänzungsmittel']
        }
    }
    
    found_markers = {}
    
    if country in markers:
        for category, terms in markers[country].items():
            found = [term for term in terms if term.lower() in response_text.lower()]
            if found:
                found_markers[category] = found
    
    # Calculate inference score
    score = len(found_markers)
    inference_level = 'NONE'
    if score >= 3:
        inference_level = 'STRONG'
    elif score >= 2:
        inference_level = 'MODERATE'
    elif score >= 1:
        inference_level = 'WEAK'
    
    return {
        'country': country,
        'inference_level': inference_level,
        'found_markers': found_markers,
        'marker_categories': score
    }

def run_comprehensive_test(template_id: int, template_name: str):
    """Run a template and analyze results for location inference"""
    
    print(f"\n{'='*70}")
    print(f"Testing: {template_name}")
    print(f"{'='*70}")
    
    # Run the template
    run_response = requests.post(
        'http://localhost:8000/api/prompt-tracking/run',
        json={
            'template_id': template_id,
            'brand_name': 'AVEA',
            'model_name': 'gemini'
        },
        timeout=120  # 2 minute timeout
    )
    
    if not run_response.ok:
        print(f"Failed to run template: {run_response.status_code}")
        return
    
    results = run_response.json()
    
    # Analyze each country's response
    for result in results['results']:
        country = result['country']
        response_text = result.get('response_preview', '')
        
        # Get full response if available
        if result.get('run_id'):
            full_response = requests.get(
                f"http://localhost:8000/api/prompt-tracking/results/{result['run_id']}"
            )
            if full_response.ok:
                data = full_response.json()
                if data.get('result'):
                    response_text = data['result']['model_response']
        
        # Analyze location inference
        analysis = analyze_location_inference(response_text, country if country != 'NONE' else None)
        
        # Display results
        print(f"\n[{country if country != 'NONE' else 'BASE MODEL'}]")
        print("-" * 40)
        
        if country == 'NONE':
            # Check that base model has no location markers
            all_markers_found = []
            for c in ['CH', 'US', 'DE']:
                c_analysis = analyze_location_inference(response_text, c)
                if c_analysis['found_markers']:
                    all_markers_found.append(f"{c}: {c_analysis['found_markers']}")
            
            if all_markers_found:
                print(f"[WARNING] Base model contains location markers: {all_markers_found}")
            else:
                print("[OK] Base model is location-neutral (as expected)")
        else:
            # Check for location inference
            if analysis['inference_level'] == 'STRONG':
                print(f"[STRONG] Location inference detected!")
            elif analysis['inference_level'] == 'MODERATE':
                print(f"[MODERATE] Location inference detected")
            elif analysis['inference_level'] == 'WEAK':
                print(f"[WEAK] Location inference detected")
            else:
                print(f"[NONE] No location inference detected")
            
            if analysis['found_markers']:
                print(f"\nLocation markers found:")
                for category, markers in analysis['found_markers'].items():
                    print(f"  • {category}: {', '.join(markers)}")
        
        # Show response preview
        print(f"\nResponse preview:")
        print(f"  {response_text[:200]}...")
        
        # Add delay to avoid rate limiting
        time.sleep(2)

def main():
    """Main test execution"""
    
    print("\n" + "="*70)
    print("LOCATION INFERENCE TEST SUITE")
    print("Testing if models can infer location from evidence without being told")
    print("="*70)
    
    # Create test templates
    print("\nCreating test templates...")
    templates = create_test_templates()
    
    if not templates:
        print("No templates created. Exiting.")
        return
    
    print(f"\nCreated {len(templates)} templates successfully")
    
    # Run tests
    print("\nStarting comprehensive tests...")
    print("(Each dot represents a 2-second delay to avoid rate limiting)")
    
    for template in templates:
        try:
            run_comprehensive_test(template['id'], template['name'])
            print("\n[WAITING] Pausing before next test...", end='')
            time.sleep(5)  # 5 second delay between templates
            print(" Ready!")
        except Exception as e:
            print(f"\nError testing {template['name']}: {str(e)}")
            if '429' in str(e):
                print("Rate limit hit. Stopping tests.")
                break
    
    print("\n" + "="*70)
    print("TEST SUITE COMPLETE")
    print("="*70)
    print("\nSummary:")
    print("The model should show location-specific content when given evidence packs")
    print("without ever being explicitly told the location.")
    print("\nKey indicators of success:")
    print("  • Currency mentions (CHF for CH, USD for US, EUR for DE)")
    print("  • Regulatory bodies (Swissmedic, FDA, BfArM)")
    print("  • Local retailers (Migros, CVS, Apotheke)")
    print("  • Geographic references without being prompted")

if __name__ == "__main__":
    main()