"""Standalone test of the robust parser"""
import json as json_module
import re

def evaluate_composite_response(country_code: str, response: str):
    """Evaluate composite JSON response containing all three probes"""
    
    # Extract JSON from response - robust to code fences and prose
    json_data = None
    # Try to find the first valid JSON object in the response
    candidates = re.findall(r'\{.*?\}', response, flags=re.DOTALL)
    for cand in candidates:
        try:
            json_data = json_module.loads(cand)
            break
        except Exception:
            continue
    # Safety net
    if not isinstance(json_data, dict):
        json_data = {}
    
    # Expected values by country
    expectations = {
        "DE": {"vat": "19%", "plug": ["F", "C"], "emergency": ["112", "110"]},
        "CH": {"vat": "8.1%", "plug": ["J", "C"], "emergency": ["112", "117", "118", "144"]},
        "FR": {"vat": "20%", "plug": ["E", "F", "C"], "emergency": ["112", "15", "17", "18"]},
        "IT": {"vat": "22%", "plug": ["L", "F", "C"], "emergency": ["112", "113"]},
        "SG": {"vat": "9%", "plug": ["G"], "emergency": ["999", "995"]},
        "GB": {"vat": "20%", "plug": ["G"], "emergency": ["999", "112"]},
        "US": {"vat": "none", "plug": ["A", "B"], "emergency": ["911"]}
    }
    
    country_exp = expectations.get(country_code, {})
    results = {}
    
    if json_data:
        # --- VAT / TVA / IVA / GST normalizer ---
        vat_value = str(json_data.get("vat_percent", "")).strip()
        
        # US case: allow explicit "none" / "no" / "n/a" / "0"
        if vat_value.lower() in {"none", "no", "n/a", "na", "null", "0", "0%"}:
            normalized_vat = "none"
        else:
            # Remove common labels if present
            vat_value = re.sub(r'^(TVA|VAT|GST|IVA|MwSt|BTW)\s*:?\s*', '', vat_value, flags=re.IGNORECASE)
            # Convert comma to dot (e.g., 8,1 -> 8.1)
            vat_value = vat_value.replace(",", ".")
            # Extract number (optional decimals) with optional percent
            m = re.search(r'(\d+(?:\.\d+)?)\s*%?', vat_value)
            if m:
                number = m.group(1)
                normalized_vat = f"{number}%"
            else:
                normalized_vat = vat_value  # leave as-is if not numeric
        
        vat_expected = country_exp.get("vat", "Unknown")
        
        # Compare against expectations (strip % for numeric compare)
        if vat_expected == "none":
            vat_passed = (normalized_vat == "none")
        else:
            vat_passed = (
                normalized_vat.replace("%", "").strip() ==
                vat_expected.replace("%", "").strip()
            )
        
        results["vat"] = {
            "passed": vat_passed,
            "expected": vat_expected,
            "found": normalized_vat
        }
        
        # --- Plug type normalizer ---
        plug_value = json_data.get("plug", "")
        plug_letters = set()
        
        # Normalize to a list of candidate tokens
        if isinstance(plug_value, list):
            candidates = [str(x) for x in plug_value]
        else:
            s = str(plug_value)
            # Split on common separators and words like "and/et/y"
            candidates = re.split(r'[/,;•]|\band\b|\bet\b|\by\b', s, flags=re.IGNORECASE)
            candidates = [c.strip() for c in candidates if c.strip()]
        
        for item in candidates:
            item_str = item.upper().strip()
            # Remove prefixes (TYPE/Typ/tipo/prise de type/prise)
            item_str = re.sub(r'^(TYPE|TYP|TIPO|PRISE\s+DE\s+TYPE|PRISE)\s*', '', item_str, flags=re.IGNORECASE)
            
            # Synonyms → letter mapping (order matters)
            if "BS 1363" in item_str or "BS1363" in item_str:
                plug_letters.add("G")           # UK/SG
            elif "SCHUKO" in item_str:
                plug_letters.add("F")           # DE/IT
            elif "CEE" in item_str:
                if "7/5" in item_str or "7/6" in item_str:
                    plug_letters.add("E")       # FR
                elif "7/4" in item_str or "7/7" in item_str:
                    plug_letters.add("F")       # DE/FR
                elif "7/16" in item_str:
                    plug_letters.add("C")       # Europlug
            elif "EUROPLUG" in item_str or "CEE7/16" in item_str.replace(" ", ""):
                plug_letters.add("C")           # Europlug (C)
            elif "CEI 23-50" in item_str or "CEI23-50" in item_str:
                plug_letters.add("L")           # Italy
            elif any(x in item_str for x in ["T13", "T14", "T15", "SEV 1011"]):
                plug_letters.add("J")           # Switzerland
            else:
                # Single letter
                if len(item_str) == 1 and item_str.isalpha():
                    plug_letters.add(item_str)
        
        plug_expected = country_exp.get("plug", [])
        if not isinstance(plug_expected, list):
            plug_expected = [plug_expected]
        
        # Expected set from expectations is already a list of letters
        plug_passed = bool(plug_letters.intersection(set(plug_expected)))
        
        results["plug"] = {
            "passed": plug_passed,
            "expected": "/".join(plug_expected),
            "found": "/".join(sorted(plug_letters)) if plug_letters else "Not found"
        }
        
        # --- Emergency numbers ---
        emergency_value = json_data.get("emergency", [])
        emergency_numbers = []
        
        def extract_digits(s):
            return re.findall(r'\b\d{2,4}\b', str(s))
        
        if isinstance(emergency_value, list):
            for item in emergency_value:
                emergency_numbers.extend(extract_digits(item))
        else:
            emergency_numbers.extend(extract_digits(emergency_value))
        
        # Remove duplicates
        emergency_numbers = list(dict.fromkeys(emergency_numbers))
        
        # Country-specific pass (pragmatic)
        if country_code == "FR":
            emergency_passed = "112" in emergency_numbers
        elif country_code == "DE":
            emergency_passed = ("112" in emergency_numbers) or ("110" in emergency_numbers)
        elif country_code == "IT":
            emergency_passed = ("112" in emergency_numbers) or ("113" in emergency_numbers)
        elif country_code == "SG":
            emergency_passed = ("999" in emergency_numbers) or ("995" in emergency_numbers)
        elif country_code == "CH":
            emergency_passed = "112" in emergency_numbers  # extras (117/118/144) are fine
        elif country_code == "GB":
            emergency_passed = ("999" in emergency_numbers) or ("112" in emergency_numbers)
        elif country_code == "US":
            emergency_passed = "911" in emergency_numbers
        else:
            emergency_passed = False
        
        emergency_expected = country_exp.get("emergency", [])
        
        results["emergency"] = {
            "passed": emergency_passed,
            "expected": "/".join(emergency_expected),
            "found": ", ".join(emergency_numbers) if emergency_numbers else "Not found"
        }
    else:
        # Failed to parse JSON
        results["vat"] = {"passed": False, "expected": country_exp.get("vat", "Unknown"), "found": "JSON parse error"}
        results["plug"] = {"passed": False, "expected": "Unknown", "found": "JSON parse error"}
        results["emergency"] = {"passed": False, "expected": "Unknown", "found": "JSON parse error"}
    
    return results


# Test cases including edge cases
test_cases = {
    "US": [
        '{"vat_percent":"none","plug":["A","B"],"emergency":["911"]}',
        '{"vat_percent":"0%","plug":["type A","type B"],"emergency":["911"]}',
        '{"vat_percent":"n/a","plug":"A/B","emergency":"911"}',  # String formats
    ],
    "FR": [
        '{"vat_percent":"20%","plug":["E","F"],"emergency":["112","15","17","18"]}',
        '{"vat_percent":"20","plug":"type E","emergency":"112"}',  # String plug
        '```json\n{"vat_percent":"20%","plug":["E"],"emergency":["112"]}\n```',  # Code fence
    ],
    "DE": [
        '{"vat_percent":"19%","plug":["F"],"emergency":["112","110"]}',
        '{"vat_percent":"19","plug":"Schuko","emergency":"112"}',  # String Schuko
    ],
    "IT": [
        '{"vat_percent":"22%","plug":["L","F"],"emergency":["112","113"]}',
        '{"vat_percent":"22","plug":"tipo L","emergency":"112"}',  # String tipo L
    ],
    "GB": [
        '{"vat_percent":"20%","plug":["G"],"emergency":["999","112"]}',
        '{"vat_percent":"20","plug":"BS 1363","emergency":"999"}',  # BS standard
    ],
    "CH": [
        '{"vat_percent":"8.1%","plug":["J"],"emergency":["112","117"]}',
        '{"vat_percent":"8,1%","plug":"typ J","emergency":"112"}',  # Comma decimal
    ],
    "SG": [
        '{"vat_percent":"9%","plug":["G"],"emergency":["999","995"]}',
        '{"vat_percent":"9","plug":"type G","emergency":"999"}',  # String format
    ],
}

print("Testing robust parser with all improvements:\n")
print("=" * 60)

total_tests = 0
total_passed = 0

for country, responses in test_cases.items():
    print(f"\n{country}:")
    for i, response in enumerate(responses, 1):
        total_tests += 1
        results = evaluate_composite_response(country, response)
        
        all_passed = all(r['passed'] for r in results.values())
        if all_passed:
            total_passed += 1
        
        status = "PASS" if all_passed else "FAIL"
        print(f"  Test {i}: [{status}]", end="")
        
        if not all_passed:
            failures = []
            for key in ["vat", "plug", "emergency"]:
                if not results[key]["passed"]:
                    failures.append(f"{key}:{results[key]['found']}")
            print(f" Failed: {', '.join(failures)}")
        else:
            print()

print("\n" + "=" * 60)
print(f"Overall: {total_passed}/{total_tests} tests passed ({100*total_passed//total_tests}%)")
print("\nKey improvements validated:")
print("- JSON extraction handles code fences")
print("- US VAT accepts 'none', 'n/a', '0%'")
print("- Plug parsing handles strings (tipo L, Schuko, BS 1363)")
print("- Comma decimals work (8,1% -> 8.1%)")
print("- Emergency numbers extracted from strings")