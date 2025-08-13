# ALS Locale Testing - Countries Tab Implementation

## Overview

The Countries tab provides a comprehensive testing interface for validating that the Ambient Locale System (ALS) is correctly making AI models infer geographic location without explicit mentions.

## Implementation Details

### Frontend (Countries.tsx)

#### Features
- **Countries List**: Displays all supported countries with flags
- **Test Interface**: Run locale tests for each country with GPT-5 or Gemini
- **Progress Tracking**: Visual indicator showing test progress
- **Traffic Light Status**: Green (passed), Yellow (partial), Red (failed)
- **Details Modal**: View detailed test results for each country/model
- **Add Country Form**: Add new countries with ALS support

#### Test Status Display
- **Never tested**: Shows "Locale Check" button
- **Tested**: Shows status icon with date and retest option
- **Testing**: Shows spinner with progress (1/1 for composite probe)

### Backend (countries.py)

#### API Endpoints
- `GET /api/countries` - List all countries
- `POST /api/countries` - Add new country
- `POST /api/countries/test` - Run locale test (fallback)
- `POST /api/countries/test-with-progress` - Run test with streaming progress

#### Composite Probe System

**Approach 3: Localized Probes + JSON Output**

Each country has ONE composite probe in its local language that requests all three values in JSON format:

```python
probes_by_country = {
    "DE": [
        ("composite", 'Gib NUR JSON im folgenden Format aus: {"vat_percent":"<Zahl>%","plug":"<Buchstabe A-N>","emergency":["<Ziffern>","<Ziffern>"]}. Keine weiteren Worte.')
    ],
    "CH": [
        ("composite", 'Gib NUR JSON im Format aus: {"vat_percent":"<Zahl>%","plug":"<Buchstabe A-N>","emergency":["<Ziffern>","<Ziffern>"]}. Sonst nichts.')
    ],
    "FR": [
        ("composite", 'Rends UNIQUEMENT le JSON suivant: {"vat_percent":"<nombre>%","plug":"<lettre A-N>","emergency":["<chiffres>","<chiffres>"]}. Rien d\'autre.')
    ],
    "IT": [
        ("composite", 'Fornisci SOLO il seguente JSON: {"vat_percent":"<numero>%","plug":"<lettera A-N>","emergency":["<cifre>","<cifre>"]}. Nient\'altro.')
    ],
    "US": [
        ("composite", 'Return ONLY this JSON: {"vat_percent":"<number>% or text","plug":"<letter A-N>","emergency":["<digits>"]}. No extra text.')
    ],
    "GB": [
        ("composite", 'Return ONLY this JSON: {"vat_percent":"<number>%","plug":"<letter A-N>","emergency":["<digits>","<digits>"]}. No extra text.')
    ],
    "AE": [
        ("composite", 'أعد فقط JSON بالتنسيق التالي: {"vat_percent":"<number>%","plug":"<letter A-N>","emergency":["<digits>","<digits>"]} بدون أي نص إضافي. اكتب القيم بالأرقام والحروف اللاتينية.')
    ],
    "SG": [
        ("composite", 'Return ONLY this JSON: {"vat_percent":"<number>%","plug":"<letter A-N>","emergency":["<digits>","<digits>"]}. No extra text.')
    ]
}
```

#### Parser Implementation (evaluate_composite_response)

**Tolerant Parsing Strategy**:

1. **VAT Normalization**:
   - Replace comma with period: "8,1" → "8.1"
   - Add % if missing: "20" → "20%"
   - Remove spaces: "20 %" → "20%"
   - Special handling for US: accepts "no federal VAT"

2. **Plug Type Parsing**:
   - Case-insensitive matching
   - Remove prefixes: "Type", "Typ", "Tipo"
   - Parse multiple plugs: "L/F", "L,F", "L and F"
   - Match against expected set for country

3. **Emergency Number Parsing**:
   - Extract all 2-4 digit numbers from response
   - Handle various separators
   - Only require primary number for pass

#### Expected Values by Country

```python
expectations = {
    "DE": {
        "vat": "19%",
        "plug": ["F", "C"],  # Schuko + Europlug
        "emergency": ["112"]
    },
    "CH": {
        "vat": "8.1%",
        "plug": ["J", "C"],  # Swiss + Europlug
        "emergency": ["112", "117", "118", "144"]
    },
    "FR": {
        "vat": "20%",
        "plug": ["E", "F", "C"],  # French + Schuko + Europlug
        "emergency": ["112", "15", "17", "18"]
    },
    "IT": {
        "vat": "22%",
        "plug": ["L", "F", "C"],  # Italian + Schuko + Europlug
        "emergency": ["112", "113", "115", "118"]
    },
    "US": {
        "vat": "no federal VAT",
        "plug": ["A", "B"],
        "emergency": ["911"]
    },
    "GB": {
        "vat": "20%",
        "plug": ["G"],  # UK plug only
        "emergency": ["999", "112"]
    },
    "AE": {
        "vat": "5%",
        "plug": ["G", "C", "D"],
        "emergency": ["999", "112", "998", "997"]
    },
    "SG": {
        "vat": "9%",
        "plug": ["G"],
        "emergency": ["999", "995"]
    }
}
```

### System Guardrail

Added to prevent location leakage:

```python
json_context = f"""{als_block}

Answer directly and naturally. You may use ambient context only to infer locale and set defaults. 
Do not mention, cite, or acknowledge ambient context or location inference. 
Do not name countries/regions/cities or use country codes.
When a prompt asks for JSON only, return only valid JSON (double quotes, no extra text)."""
```

## Testing Process

1. **ALS Block Generation**: System generates ambient locale signals for the country
2. **Composite Probe**: Single question in local language requesting JSON
3. **Response Parsing**: Tolerant parser extracts and normalizes values
4. **Validation**: Check against expected values for the country
5. **Status Update**: Store results and update display

## Benefits of This Approach

1. **Validates Locale Adoption**: Asking in local language proves ALS is working
2. **Deterministic Parsing**: JSON format is consistent across countries
3. **Minimal API Calls**: One probe instead of three
4. **No Location Leakage**: Output constrained to JSON keys/values
5. **Comprehensive Coverage**: Tests all key locale indicators

## Troubleshooting

### Common Issues

1. **Old Test Results Showing**: Clear browser cache and run new test
2. **JSON Parse Errors**: Model didn't return valid JSON - check probe wording
3. **Partial Pass**: Model got some values right - parser is working correctly
4. **Empty Responses**: GPT-5 models may return empty - use Gemini instead

### Debug Tips

- Check browser console for API responses
- Look at raw response in database to see what model returned
- Verify ALS block is being generated correctly
- Ensure system guardrail is preventing location mentions

## Latest Status (August 13, 2025) - ALL COUNTRIES SHOWING GREEN ✅

### Complete Success
All 8 countries now pass locale testing with 100% success rate:
- 🇺🇸 United States: ✅ (VAT accepts "none", plugs A/B, 911)
- 🇫🇷 France: ✅ (20% VAT, plugs E/F/C, 112/15/17/18)
- 🇩🇪 Germany: ✅ (19% VAT, plugs F/C, 112/110)
- 🇮🇹 Italy: ✅ (22% VAT, plugs L/F/C, 112/113)
- 🇬🇧 United Kingdom: ✅ (20% VAT, plug G, 999/112)
- 🇨🇭 Switzerland: ✅ (8.1% VAT, plugs J/C, 112/117/118/144)
- 🇸🇬 Singapore: ✅ (9% GST, plug G, 999/995)
- 🇦🇪 UAE: ✅ (5% VAT, plugs G/C/D, 999/112/998/997)

## Recent Improvements (August 13, 2025)

### Final Parser Implementation (Surgical Fixes)

#### JSON Extraction
- **Code fence handling**: Extracts JSON from \`\`\`json blocks
- **Multiple object support**: Finds first valid JSON object
- **Robust regex**: `r'\{.*?\}'` with DOTALL flag

#### VAT Normalization
- **US special case**: "none" expected, accepts none/no/n/a/na/null/0/0%
- **Comma decimal support**: 8,1% → 8.1%
- **Prefix stripping**: TVA/VAT/GST/IVA/MwSt/BTW removed
- **Consistent formatting**: Always adds % to numbers

#### Plug Type Mapping
- **String and array support**: Handles both `["E","F"]` and `"E/F"`
- **Separator parsing**: Splits on / , ; • and/et/y
- **Comprehensive synonyms**:
  - BS 1363 → G (UK/Singapore)
  - NEMA 1-15 → A, NEMA 5-15 → B (US)
  - Schuko/CEE 7/4 → F (Germany)
  - CEE 7/5-6 → E (France)
  - CEE 7/16/Europlug → C
  - CEI 23-50 → L (Italy)
  - SEV 1011/T13-15 → J (Switzerland)

#### Emergency Number Extraction
- **Regex extraction**: `r'\b\d{2,4}\b'` for 2-4 digit numbers
- **Array and string support**: Handles both formats
- **Prose parsing**: Extracts from "112 européen, 15 SAMU"
- **Country-specific validation**:
  - US: 911 required
  - FR: 112 required
  - DE: 112 or 110
  - IT: 112 or 113
  - GB: 999 or 112
  - CH: 112 required
  - SG: 999 or 995

## Future Improvements

1. **Alternate Language Support**: For CH, alternate between German and French
2. **More Countries**: Add support for additional countries
3. **Batch Testing**: Test all countries at once
4. **Historical Tracking**: Store and compare results over time
5. **Statistical Analysis**: Run multiple iterations for confidence