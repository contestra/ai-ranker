"""Test the improved parser for France"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.api.countries import evaluate_composite_response

# Test with different response formats
test_responses = [
    # Format 1: Simple numbers without %
    '{"vat_percent":"20","plug":["E","F"],"emergency":["112","15","17","18"]}',
    
    # Format 2: With TVA prefix
    '{"vat_percent":"TVA 20","plug":["E","F"],"emergency":["112","15","17","18"]}',
    
    # Format 3: With CEE codes for plugs
    '{"vat_percent":"20%","plug":["Type E (CEE 7/5)","Type F (Schuko/CEE 7/4)"],"emergency":["112","15","17","18"]}',
    
    # Format 4: Emergency numbers in prose
    '{"vat_percent":"20%","plug":["E","F"],"emergency":["112 européen, 15 SAMU, 17 Police, 18 Pompiers"]}',
    
    # Format 5: All variations combined
    '{"vat_percent":"20","plug":["prise de type E","F"],"emergency":["112 européen","15 SAMU","17 Police","18 Pompiers"]}',
]

print("Testing France parser with various response formats:\n")
for i, response in enumerate(test_responses, 1):
    print(f"Test {i}: {response[:70]}...")
    results = evaluate_composite_response("FR", response)
    
    print(f"  VAT: Expected '20%', Found '{results['vat']['found']}', Passed: {results['vat']['passed']}")
    print(f"  Plug: Expected 'Type E/F/C', Found '{results['plug']['found']}', Passed: {results['plug']['passed']}")
    print(f"  Emergency: Expected '112/15/17/18', Found '{results['emergency']['found']}', Passed: {results['emergency']['passed']}")
    
    overall_passed = all(r['passed'] for r in results.values())
    print(f"  Overall: {'✓ PASSED' if overall_passed else '✗ FAILED'}\n")