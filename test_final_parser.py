"""Test the final parser with all recommended fixes"""
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
            pass
    
    # Expected values by country
    expectations = {
        "US": {
            "vat": "No federal VAT",
            "plug": ["A", "B"],
            "emergency": ["911"]
        },
        "FR": {
            "vat": "20%",
            "plug": ["E", "F", "C"],
            "emergency": ["112", "15", "17", "18"]
        },
        "DE": {
            "vat": "19%",
            "plug": ["F", "C"],
            "emergency": ["112", "110"]
        },
        "IT": {
            "vat": "22%",
            "plug": ["L", "F", "C"],
            "emergency": ["112", "113"]
        },
        "GB": {
            "vat": "20%",
            "plug": ["G"],
            "emergency": ["999", "112"]
        },
        "CH": {
            "vat": "8.1%",
            "plug": ["J", "C"],
            "emergency": ["112", "117", "118", "144"]
        },
        "SG": {
            "vat": "9%",
            "plug": ["G"],
            "emergency": ["999", "995"]
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
        # Replace comma with period for decimal
        vat_value = vat_value.replace(",", ".")
        # Extract just the number if there's extra text
        number_match = re.search(r'(\d+(?:\.\d+)?)\s*%?', vat_value)
        if number_match:
            vat_value = number_match.group(1)
        # Add % if missing and it's a number
        if vat_value and "%" not in vat_value and vat_value.replace(".", "").replace(" ", "").isdigit():
            vat_value = f"{vat_value}%"
        # Remove spaces between number and %
        vat_value = vat_value.replace(" %", "%")
        
        vat_expected = country_exp.get("vat", "Unknown")
        vat_passed = False
        
        # Special case for US - handle various "no VAT" responses
        if country_code == "US":
            no_vat_values = ["none", "no", "n/a", "na", "null", "0", "0%"]
            if vat_value.lower() in no_vat_values or any(x in vat_value.lower() for x in ["no federal", "none", "n/a"]):
                vat_passed = True
                vat_value = "No federal VAT"  # Normalize display
        # Compare normalized values
        elif vat_value.replace("%", "").strip() == vat_expected.replace("%", "").strip():
            vat_passed = True
        elif vat_value.lower() == vat_expected.lower():
            vat_passed = True
        
        results["vat"] = {
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
                
                # Comprehensive plug synonym mapping
                if "BS 1363" in item_str or "BS1363" in item_str:
                    plug_letters.add("G")
                elif "NEMA" in item_str:
                    if "1-15" in item_str:
                        plug_letters.add("A")
                    elif "5-15" in item_str:
                        plug_letters.add("B")
                elif "CEE" in item_str:
                    if "7/5" in item_str or "7/6" in item_str:
                        plug_letters.add("E")
                    elif "7/4" in item_str or "7/7" in item_str:
                        plug_letters.add("F")
                elif "SCHUKO" in item_str:
                    plug_letters.add("F")
                elif "CEI 23-50" in item_str:
                    plug_letters.add("L")
                elif any(x in item_str for x in ["T13", "T14", "T15", "SEV 1011"]):
                    plug_letters.add("J")
                elif item_str and len(item_str) == 1 and item_str.isalpha():
                    plug_letters.add(item_str)
        else:
            # Handle string format
            plug_value = str(plug_value).upper().strip()
            # Remove prefixes
            plug_value = re.sub(r'^(TYPE|TYP|TIPO|PRISE\s+DE\s+TYPE|PRISE)\s*', '', plug_value, flags=re.IGNORECASE)
            
            # Check for specific standards
            if "BS 1363" in plug_value or "BS1363" in plug_value:
                plug_letters.add("G")
            elif "NEMA" in plug_value:
                if "1-15" in plug_value:
                    plug_letters.add("A")
                if "5-15" in plug_value:
                    plug_letters.add("B")
            elif "CEE" in plug_value:
                if "7/5" in plug_value or "7/6" in plug_value:
                    plug_letters.add("E")
                if "7/4" in plug_value or "7/7" in plug_value:
                    plug_letters.add("F")
            elif "SCHUKO" in plug_value:
                plug_letters.add("F")
            elif "CEI 23-50" in plug_value:
                plug_letters.add("L")
            elif any(x in plug_value for x in ["T13", "T14", "T15", "SEV 1011"]):
                plug_letters.add("J")
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
            "passed": plug_passed,
            "expected": expected_display,
            "found": found_display
        }
        
        # Check Emergency
        emergency_value = json_data.get("emergency", [])
        emergency_numbers = []
        
        if isinstance(emergency_value, list):
            for item in emergency_value:
                item_str = str(item)
                # Extract all 2-3 digit numbers (not 4)
                found_numbers = re.findall(r'\b\d{2,3}\b', item_str)
                emergency_numbers.extend(found_numbers)
        else:
            emergency_str = str(emergency_value)
            found_numbers = re.findall(r'\b\d{2,3}\b', emergency_str)
            emergency_numbers.extend(found_numbers)
        
        # Remove duplicates while preserving order
        seen = set()
        emergency_numbers = [x for x in emergency_numbers if not (x in seen or seen.add(x))]
        
        emergency_expected = country_exp.get("emergency", [])
        
        # Country-specific emergency pass conditions
        emergency_passed = False
        if emergency_numbers and emergency_expected:
            if country_code == "US":
                emergency_passed = "911" in emergency_numbers
            elif country_code == "FR":
                emergency_passed = "112" in emergency_numbers
            elif country_code == "DE":
                emergency_passed = "112" in emergency_numbers or "110" in emergency_numbers
            elif country_code == "IT":
                emergency_passed = "112" in emergency_numbers or "113" in emergency_numbers
            elif country_code == "GB":
                emergency_passed = "999" in emergency_numbers or "112" in emergency_numbers
            elif country_code == "CH":
                emergency_passed = "112" in emergency_numbers
            elif country_code == "SG":
                emergency_passed = "999" in emergency_numbers or "995" in emergency_numbers
            else:
                primary = str(emergency_expected[0])
                emergency_passed = primary in emergency_numbers
        
        results["emergency"] = {
            "passed": emergency_passed,
            "expected": "/".join([str(e) for e in emergency_expected]),
            "found": ", ".join(emergency_numbers) if emergency_numbers else "Not found"
        }
    else:
        # Failed to parse JSON
        results["vat"] = {"passed": False, "expected": country_exp.get("vat", "Unknown"), "found": "JSON parse error"}
        results["plug"] = {"passed": False, "expected": "Unknown", "found": "JSON parse error"}
        results["emergency"] = {"passed": False, "expected": "Unknown", "found": "JSON parse error"}
    
    return results


# Test cases including problematic responses
test_cases = {
    "US": [
        # What models should return with new probe
        '{"vat_percent":"none","plug":["A","B"],"emergency":["911"]}',
        # Other variations
        '{"vat_percent":"no","plug":["type A","type B"],"emergency":["911"]}',
        '{"vat_percent":"0%","plug":["NEMA 1-15","NEMA 5-15"],"emergency":["911"]}',
        '{"vat_percent":"n/a","plug":["A","B"],"emergency":["911"]}',
    ],
    "FR": [
        '{"vat_percent":"20%","plug":["E","F"],"emergency":["112","15","17","18"]}',
        '{"vat_percent":"20","plug":["type E"],"emergency":["112"]}',
        '{"vat_percent":"TVA 20","plug":["E"],"emergency":["112 européen","15 SAMU"]}',
    ],
    "DE": [
        '{"vat_percent":"19%","plug":["F"],"emergency":["112","110"]}',
        '{"vat_percent":"19","plug":["Schuko"],"emergency":["112"]}',
        '{"vat_percent":"19%","plug":["typ F"],"emergency":["110","112"]}',
    ],
    "IT": [
        '{"vat_percent":"22%","plug":["L","F"],"emergency":["112","113"]}',
        '{"vat_percent":"22","plug":["tipo L"],"emergency":["112"]}',
        '{"vat_percent":"IVA 22%","plug":["CEI 23-50","Schuko"],"emergency":["113"]}',
    ],
    "GB": [
        '{"vat_percent":"20%","plug":["G"],"emergency":["999","112"]}',
        '{"vat_percent":"20","plug":["type G"],"emergency":["999"]}',
        '{"vat_percent":"VAT 20%","plug":["BS 1363"],"emergency":["112"]}',
    ],
}

print("Testing final parser with all fixes:\n")
print("=" * 60)
for country, responses in test_cases.items():
    print(f"\n{country}:")
    print("-" * 40)
    for i, response in enumerate(responses, 1):
        results = evaluate_composite_response(country, response)
        
        all_passed = all(r['passed'] for r in results.values())
        
        # Show status
        status_icons = {
            "vat": "PASS" if results["vat"]["passed"] else "FAIL",
            "plug": "PASS" if results["plug"]["passed"] else "FAIL", 
            "emergency": "PASS" if results["emergency"]["passed"] else "FAIL"
        }
        
        print(f"  Test {i}: VAT[{status_icons['vat']}] Plug[{status_icons['plug']}] Emergency[{status_icons['emergency']}]")
        
        # Show failures
        if not all_passed:
            for key, result in results.items():
                if not result['passed']:
                    print(f"    {key}: Expected '{result['expected']}', Found '{result['found']}'")

print("\n" + "=" * 60)
print("Summary: All tests should pass with [PASS] marks")