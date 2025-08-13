# Ambient Blocks Service (ALS)

## Overview

The Ambient Blocks service provides minimal civic/government signals to make AI models naturally infer geographic location WITHOUT any mention of brands, products, or commercial content.

## Architecture

```
als/
├── __init__.py           # Service entry point
├── als_builder.py        # Main builder - generates Ambient Blocks
├── als_templates.py      # Pre-built Ambient Blocks (curated quarterly)
├── als_harvester.py      # Exa harvester for refreshing Ambient Blocks
└── README.md            # This file
```

## How It Works

### 1. Ambient Blocks (Pre-built, Static)
- Curated civic terms for each country
- Updated quarterly or when adding countries
- Stored in `als_templates.py`
- NO live search during testing

### 2. Builder (Runtime)
- Generates Ambient Blocks from templates
- Randomizes selections for variety
- Validates for contamination
- Used by prompt tracker

### 3. Harvester (Offline Tool)
- Uses Exa to find authentic civic terms
- Searches ONLY government/civic domains
- Runs quarterly to refresh Ambient Blocks
- NOT used during testing

## Usage

### Basic Usage (in prompt tracker or other features)

```python
from app.services.als import als_service

# Generate Ambient Block for Germany
ambient_block = als_service.build_als_block('DE')

# Send as SEPARATE messages (critical!)
messages = [
    {"role": "system", "content": "Answer in user's language. If locale ambiguous, use Ambient Context. Do not cite it."},
    {"role": "user", "content": ambient_block},    # Ambient signals
    {"role": "user", "content": "What is AVEA?"}   # NAKED prompt
]
```

### Minimal Ambient Block (≤200 chars)

```python
# Ultra-minimal for token-constrained scenarios
minimal_block = als_service.build_minimal_als('CH')
# Returns: "Context: 14:05 UTC+01:00 • AHV-Nummer beantragen • CHF 12.90"
```

### Validation

```python
# Check for contamination issues
is_valid, issues = als_service.validate_als_block(ambient_block)
if not is_valid:
    print(f"Ambient Block validation failed: {issues}")

# Check for leakage after response
leaked_phrases = als_service.detect_leakage(ambient_block, model_response)
if leaked_phrases:
    print(f"Response leaked Ambient Block phrases: {leaked_phrases}")
```

## Refreshing Ambient Blocks (Quarterly)

Run the harvester to update Ambient Blocks:

```python
from app.services.als import ALSHarvester

harvester = ALSHarvester()

# Harvest for one country
data = await harvester.harvest_country('DE')

# Or refresh all countries
await harvester.refresh_all_templates('harvested_als_data.json')
```

Then manually review and update Ambient Blocks in `als_templates.py`.

## Example Ambient Blocks

### Germany (DE)
```
Ambient Context (localization only; do not cite):
- 2025-08-12 14:05, UTC+02:00
- "Personalausweis verlängern" • "Führerschein umtausch"
- 10115 Berlin • +49 30 xxx xx xx • 12,90 €
- bund.de
- national weather service shows Berlin
```

### Switzerland (CH)
```
Ambient Context (localization only; do not cite):
- 2025-08-12 14:05, UTC+02:00
- "Führerausweis erneuern" • "AHV-Nummer beantragen"
- 8001 Zürich • +41 44 xxx xx xx • CHF 89.00
- admin.ch
- national weather service shows Zürich
```

## Key Principles

1. **Purely Civic/Government**
   - Only government portals, civic services
   - NO commercial sites or brands
   - NO industry-specific content

2. **Ultra-Minimal**
   - ≤350 chars total
   - Just enough to infer location
   - Avoid steering content

3. **Pre-Built Templates**
   - NOT live search during tests
   - Curated and validated offline
   - Refreshed quarterly

4. **Separate Messages**
   - NEVER concatenate to prompt
   - Send as independent context
   - Keep prompt naked

## Testing Localization

After using ALS, validate with probe questions:

```python
# Probe questions to confirm location inference
probes = [
    "What's the standard VAT rate?",
    "What electrical plug type is used?",
    "What's the emergency phone number?"
]
```

Expected answers:
- DE: 19% VAT, Type F plug, 112
- CH: 7.7% VAT, Type J plug, 112
- US: No federal VAT, Type A/B plug, 911
- GB: 20% VAT, Type G plug, 999

## Maintenance Schedule

- **Daily**: Use pre-built templates
- **Quarterly**: Run harvester, review results, update templates
- **Annually**: Review supported countries, add new ones

## Countries Supported

- 🇩🇪 **DE** - Germany
- 🇨🇭 **CH** - Switzerland  
- 🇺🇸 **US** - United States
- 🇬🇧 **GB** - United Kingdom
- 🇦🇪 **AE** - United Arab Emirates
- 🇸🇬 **SG** - Singapore

## Adding New Countries

### Method 1: Using AI Generation (Recommended)
1. Use the **[ALS Expansion Prompt](../../../../ALS_EXPANSION_PROMPT.md)** with an AI model
2. Review generated YAML for accuracy
3. Verify agency-task matching and phone/city consistency
4. Add validated templates to `als_templates.py`
5. Test with probe questions

### Method 2: Manual Harvesting
1. Add civic domains to `als_harvester.py`
2. Add harvest queries in local language
3. Run harvester for the new country
4. Review and add to `als_templates.py`
5. Test with probe questions

## Troubleshooting

### Ambient Blocks not working?
- Check character count (≤350)
- Validate no commercial content
- Ensure separate messages
- Test with probe questions

### Response leaking Ambient Block phrases?
- Reduce ALS block size
- Use more generic terms
- Check with leak detector

### Need to debug?
- Enable validation checks
- Log Ambient Blocks sent
- Compare probe answers