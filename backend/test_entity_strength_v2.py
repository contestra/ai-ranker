#!/usr/bin/env python3
"""
Test the two-step entity strength checker v2 endpoint
"""

import requests
import json
import sys

# Force UTF-8 output for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def test_brand(brand_name, domain=None):
    """Test a brand with the v2 endpoint"""
    
    print(f"\n{'='*60}")
    print(f"Testing: {brand_name}")
    if domain:
        print(f"Domain: {domain}")
    print('='*60)
    
    # Test the v2 endpoint
    response = requests.post(
        'http://localhost:8000/api/brand-entity-strength-v2',
        json={
            'brand_name': brand_name,
            'domain': domain,
            'information_vendor': 'google',  # Gemini 2.5 Pro
            'classifier_vendor': 'openai'    # GPT-4o-mini
        }
    )
    
    if response.ok:
        data = response.json()
        
        print(f"\n✅ SUCCESS - Two-Step Analysis Complete")
        print(f"Information Model: {data.get('information_vendor', 'N/A')}")
        print(f"Classifier Model: {data.get('classifier_vendor', 'N/A')}")
        
        classification = data.get('classification', {})
        
        print(f"\n📊 CLASSIFICATION RESULT:")
        print(f"  Label: {classification.get('label', 'N/A')}")
        print(f"  Confidence: {classification.get('confidence', 0)}%")
        print(f"  Methodology: {classification.get('methodology', 'N/A')}")
        
        # Show natural response
        print(f"\n📝 STEP 1 - NATURAL RESPONSE (Gemini 2.5 Pro):")
        print('-'*50)
        natural = classification.get('natural_response', 'No response')
        if len(natural) > 500:
            print(natural[:500] + '...')
        else:
            print(natural)
        
        # Show classifier analysis
        print(f"\n🔍 STEP 2 - CLASSIFICATION ANALYSIS (GPT-4o-mini):")
        print('-'*50)
        analysis = classification.get('classifier_analysis', {})
        print(f"  Specific Facts Count: {analysis.get('specific_facts', 0)}")
        print(f"  Generic Claims Count: {analysis.get('generic_claims', 0)}")
        print(f"  Entities Mentioned: {analysis.get('entities_mentioned', 0)}")
        print(f"  Multiple Entities: {'Yes' if analysis.get('multiple_entities', False) else 'No'}")
        print(f"  Classifier Result: {analysis.get('classification', 'N/A')}")
        print(f"  Reasoning: {analysis.get('reasoning', 'N/A')}")
        
        # Show warnings
        if classification.get('disambiguation_needed'):
            print(f"\n⚠️  DISAMBIGUATION NEEDED - Multiple entities share the name '{brand_name}'")
            entities = classification.get('entities_mentioned', [])
            if entities:
                print("  Entities found:")
                for entity in entities[:5]:
                    print(f"    • {entity}")
        
        if classification.get('confusion_detected'):
            print(f"\n⚠️  CONFUSION DETECTED - AI may be identifying wrong company")
            if classification.get('actual_industry') and classification.get('ai_thinks_industry'):
                print(f"  Your industry: {classification.get('actual_industry')}")
                print(f"  AI thinks: {classification.get('ai_thinks_industry')}")
        
        # Show fact ratio
        facts = classification.get('specific_facts_count', 0)
        claims = classification.get('generic_claims_count', 0)
        total = facts + claims
        if total > 0:
            ratio = (facts / total) * 100
            print(f"\n📈 KNOWLEDGE QUALITY:")
            print(f"  Fact Ratio: {ratio:.1f}% ({facts} facts / {total} total statements)")
        
        return data
        
    else:
        print(f"\n❌ ERROR {response.status_code}: {response.text}")
        return None

def main():
    """Run tests on multiple brands"""
    
    print("\n" + "="*60)
    print("ENTITY STRENGTH V2 - TWO-STEP ANALYSIS TEST")
    print("="*60)
    print("\nThis test demonstrates the two-step approach:")
    print("1. Natural information gathering (Gemini 2.5 Pro)")
    print("2. Independent classification (GPT-4o-mini)")
    
    # Test brands
    test_cases = [
        ("AVEA", "avea-life.com"),  # Swiss supplements company
        ("OpenAI", None),  # Well-known AI company
        ("Contestra", None),  # Your company - likely unknown
        ("Tesla", None),  # Well-known car/tech company
    ]
    
    results = []
    for brand, domain in test_cases:
        result = test_brand(brand, domain)
        if result:
            results.append({
                'brand': brand,
                'label': result['classification']['label'],
                'confidence': result['classification']['confidence'],
                'facts': result['classification'].get('specific_facts_count', 0),
                'disambiguation': result['classification'].get('disambiguation_needed', False)
            })
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY OF RESULTS")
    print("="*60)
    
    if results:
        print("\n{:<15} {:<15} {:<12} {:<8} {:<15}".format(
            "Brand", "Classification", "Confidence", "Facts", "Disambiguation"
        ))
        print("-"*70)
        
        for r in results:
            print("{:<15} {:<15} {:<12} {:<8} {:<15}".format(
                r['brand'],
                r['label'],
                f"{r['confidence']}%",
                str(r['facts']),
                "Yes" if r['disambiguation'] else "No"
            ))
    
    print("\n✅ Test complete!")

if __name__ == "__main__":
    main()