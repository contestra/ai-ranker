"""
Automated testing loop for Entity Strength Analysis
Tests encoding issues and stability
"""
import requests
import time
import json

def test_api(brand_name, domain=None):
    """Test the API with a brand"""
    try:
        response = requests.post(
            'http://localhost:8000/api/brand-entity-strength',
            json={
                'brand_name': brand_name,
                'domain': domain,
                'vendor': 'openai',
                'include_reasoning': True
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            classification = data.get('classification', {})
            return {
                'success': True,
                'label': classification.get('label'),
                'confidence': classification.get('confidence'),
                'disambiguation': classification.get('disambiguation_needed', False),
                'confusion': classification.get('confusion_detected', False)
            }
        else:
            return {
                'success': False,
                'error': f"Status {response.status_code}: {response.text[:100]}"
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)[:100]
        }

def run_tests():
    """Run multiple test cases"""
    test_cases = [
        ('AVEA', 'avea-life.com'),
        ('AVEA', None),  # Without domain
        ('OpenAI', None),
        ('Google', None),
        ('TestBrand123', None),  # Unknown brand
    ]
    
    print("="*60)
    print("Starting Entity Strength Analysis Test Loop")
    print("="*60)
    
    all_passed = True
    
    for i, (brand, domain) in enumerate(test_cases, 1):
        print(f"\nTest {i}: Brand='{brand}', Domain='{domain or 'None'}'")
        print("-" * 40)
        
        result = test_api(brand, domain)
        
        if result['success']:
            print(f"[PASS] SUCCESS")
            print(f"  Label: {result['label']}")
            print(f"  Confidence: {result['confidence']}%")
            if result['disambiguation']:
                print(f"  [WARNING] Disambiguation needed")
            if result['confusion']:
                print(f"  [WARNING] Confusion detected")
        else:
            print(f"[FAIL] FAILED")
            print(f"  Error: {result['error']}")
            all_passed = False
        
        # Small delay between tests
        time.sleep(2)
    
    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED - SUCCESS")
    else:
        print("SOME TESTS FAILED - ERROR")
    print("="*60)
    
    return all_passed

if __name__ == "__main__":
    # Run test loop 3 times to check stability
    for round_num in range(1, 4):
        print(f"\n\n{'#'*60}")
        print(f"ROUND {round_num} OF 3")
        print(f"{'#'*60}")
        
        success = run_tests()
        
        if not success:
            print(f"\nRound {round_num} had failures. Stopping test loop.")
            break
        
        if round_num < 3:
            print("\nWaiting 5 seconds before next round...")
            time.sleep(5)
    
    print("\n\nTest loop completed.")