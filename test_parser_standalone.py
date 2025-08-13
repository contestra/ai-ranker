"""Standalone test of the improved parser for France"""
import json as json_module
import re

def evaluate_composite_response(country_code: str, response: str):
    """Evaluate composite JSON response containing all three probes"""
    
    # Extract JSON from response
    json_data = None
    if "{" in response and "}" in response:
        try:
            # Extract JSON from response (might have extra text)
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                json_data = json_module.loads(json_match.group())
        except:
            pass  # Fall back to individual parsing
    
    # Expected values for France
    expectations = {
        "FR": {
            "vat": "20%",
            "plug": ["E", "F", "C"],  # Type E is French, Type F and C also common
            "emergency": ["112", "15", "17", "18"]  # 112 general, 15 medical, 17 police, 18 fire
        }
    }
    
    country_exp = expectations.get(country_code, {})
    results = {}
    
    if json_data:
        # Check VAT
        vat_value = str(json_data.get("vat_percent", ""))
        
        # Normalize VAT value
        vat_value = vat_value.strip()
        # Remove TVA/VAT/GST labels if present
        vat_value = re.sub(r'^(TVA|VAT|GST|IVA|MwSt|BTW)\s*:?\s*', '', vat_value, flags=re.IGNORECASE)
        # Replace comma with period for decimal (e.g., "8,1" -> "8.1")
        vat_value = vat_value.replace(",", ".")
        # Extract just the number if there's extra text
        number_match = re.search(r'(\d+(?:\.\d+)?)\s*%?', vat_value)
        if number_match:
            vat_value = number_match.group(1)
        # Add % if missing and it's a number
        if vat_value and "%" not in vat_value and vat_value.replace(".", "").replace(" ", "").isdigit():
            vat_value = f"{vat_value}%"
        # Remove spaces between number and % (e.g., "20 %" -> "20%")
        vat_value = vat_value.replace(" %", "%")
        
        vat_expected = country_exp.get("vat", "Unknown")
        vat_passed = vat_value.replace("%", "").strip() == vat_expected.replace("%", "").strip()
        
        results["vat"] = {
            "question": "VAT/GST Rate",
            "response": response[:200],
            "passed": vat_passed,
            "expected": vat_expected,
            "found": vat_value
        }
        
        # Check Plug
        plug_value = json_data.get("plug", "")
        
        # Parse multiple plugs - handle both array and string formats
        plug_letters = set()
        
        if isinstance(plug_value, list):
            # Handle array format ["E", "F"]
            for item in plug_value:
                item_str = str(item).upper().strip()
                # Remove prefixes and extract letter
                item_str = re.sub(r'^(TYPE|TYP|TIPO|PRISE\s+DE\s+TYPE|PRISE)\s*', '', item_str, flags=re.IGNORECASE)
                # Handle CEE notations
                if "CEE" in item_str.upper():
                    # Map CEE codes to plug types
                    if "7/5" in item_str or "7/6" in item_str:
                        plug_letters.add("E")
                    elif "7/4" in item_str or "7/7" in item_str or "SCHUKO" in item_str.upper():
                        plug_letters.add("F")
                elif item_str and len(item_str) == 1 and item_str.isalpha():
                    plug_letters.add(item_str)
        else:
            # Handle string format
            plug_value = str(plug_value).upper().strip()
            # Remove prefixes
            plug_value = re.sub(r'^(TYPE|TYP|TIPO|PRISE\s+DE\s+TYPE|PRISE)\s*', '', plug_value, flags=re.IGNORECASE)
            
            # Check for CEE codes
            if "CEE" in plug_value:
                if "7/5" in plug_value or "7/6" in plug_value:
                    plug_letters.add("E")
                if "7/4" in plug_value or "7/7" in plug_value or "SCHUKO" in plug_value:
                    plug_letters.add("F")
            else:
                # Parse multiple plugs from string
                for separator in ["/", ",", " AND ", " ET ", " E ", " Y ", " OU ", " UND "]:
                    if separator in plug_value:
                        parts = plug_value.split(separator)
                        for part in parts:
                            cleaned = part.strip()
                            if cleaned and len(cleaned) == 1 and cleaned.isalpha():
                                plug_letters.add(cleaned)
                        break
                
                # If no separator found, treat as single letter
                if not plug_letters and plug_value and len(plug_value) == 1 and plug_value.isalpha():
                    plug_letters.add(plug_value)
        
        plug_expected = country_exp.get("plug", [])
        if not isinstance(plug_expected, list):
            plug_expected = [plug_expected]
        
        # Check if any expected plugs match
        plug_passed = bool(plug_letters.intersection(set(plug_expected)))
        
        # Format expected and found for display
        expected_display = "/".join([f"Type {p}" for p in plug_expected])
        found_display = "/".join([f"Type {p}" for p in sorted(plug_letters)]) if plug_letters else "Not found"
        
        results["plug"] = {
            "question": "Plug Type",
            "response": response[:200],
            "passed": plug_passed,
            "expected": expected_display,
            "found": found_display
        }
        
        # Check Emergency
        emergency_value = json_data.get("emergency", [])
        emergency_numbers = []
        
        if isinstance(emergency_value, list):
            # Handle array format - might contain prose or just numbers
            for item in emergency_value:
                item_str = str(item)
                # Extract all 2-4 digit numbers from each item
                found_numbers = re.findall(r'\b\d{2,4}\b', item_str)
                emergency_numbers.extend(found_numbers)
        else:
            # Handle string format - extract all 2-4 digit numbers
            emergency_str = str(emergency_value)
            # Look for patterns like "112 européen, 15 SAMU, 17 Police, 18 Pompiers"
            found_numbers = re.findall(r'\b\d{2,4}\b', emergency_str)
            emergency_numbers.extend(found_numbers)
        
        # Remove duplicates while preserving order
        seen = set()
        emergency_numbers = [x for x in emergency_numbers if not (x in seen or seen.add(x))]
        
        emergency_expected = country_exp.get("emergency", [])
        
        # Check if primary emergency number is present
        emergency_passed = False
        if emergency_numbers and emergency_expected:
            # Primary emergency number should be first in expected list
            primary = str(emergency_expected[0])
            emergency_passed = primary in emergency_numbers
        
        results["emergency"] = {
            "question": "Emergency Number",
            "response": response[:200],
            "passed": emergency_passed,
            "expected": "/".join([str(e) for e in emergency_expected]),
            "found": ", ".join(emergency_numbers) if emergency_numbers else "Not found"
        }
    else:
        # Failed to parse JSON - mark all as failed
        results["vat"] = {
            "question": "VAT/GST Rate",
            "response": response[:200],
            "passed": False,
            "expected": country_exp.get("vat", "Unknown"),
            "found": "JSON parse error"
        }
        results["plug"] = {
            "question": "Plug Type",
            "response": response[:200],
            "passed": False,
            "expected": f"Type {country_exp.get('plug', 'Unknown')}",
            "found": "JSON parse error"
        }
        results["emergency"] = {
            "question": "Emergency Number",
            "response": response[:200],
            "passed": False,
            "expected": "/".join(country_exp.get("emergency", [])),
            "found": "JSON parse error"
        }
    
    return results


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
    print(f"  Overall: {'PASSED' if overall_passed else 'FAILED'}\n")