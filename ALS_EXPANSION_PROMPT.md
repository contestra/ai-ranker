# ALS Expansion Prompt - Creating New Country Templates

## Purpose
Use this prompt with an AI model to generate new Ambient Location Signal templates for additional countries.

## The Prompt

You are expanding our Ambient Location Signals (ALS) library for cross-market brand-visibility measurement.

GOAL
Create clean, neutral Ambient Blocks for NEW countries we specify. Each block helps models assume a locale WITHOUT topical priming. The user's test prompt stays naked in a separate message.

INPUT
- A list of target countries with ISO codes (e.g., ES, SE, NL), and optionally a primary city.

DEFINITIONS
- ALS block = 3–5 bullets (≤ 350 total characters) containing ONLY:
  1) Fresh local timestamp placeholder + UTC offset (no real-time values; use {{STAMP}} and {{OFFSET}})
  2) ONE civic portal keyword + ONE short local-language civic phrase (e.g., driver's licence renewal, passport appointment, tax ID). NO URLs.
  3) ONE formatting line showing postal/phone/currency conventions for that country.
  4) OPTIONAL: a generic national weather office stub in the local language (no temperatures, no links, no agency names spelled out; just "national weather service: <city>").
- Civic portal keyword: a short, non-clickable label (e.g., "GOV.UK", "ch.ch", "Bundesportal"). If unsure, use a neutral agency descriptor (e.g., "national portal" in local language).

GUARDRAILS (CRITICAL)
- No URLs, no news outlets, no retailer or product names, no politicians, no brands, no headlines.
- Keep everything in the LOCAL LANGUAGE where applicable (except currency symbols).
- Avoid category words related to our measurement topics (e.g., supplements) in the ALS itself.
- Keep each block ≤ 350 chars; each bullet ≤ 90 chars.
- Provide rotation pools (4–6 synonymous civic phrases per country) for robustness.
- For multilingual countries, include variants where appropriate (e.g., CH German/French/Italian).

OUTPUT FORMAT (RETURN ONLY THIS; NO EXTRA COMMENTARY)
Produce a single YAML document with two top-level keys:

```yaml
ALS_TEMPLATES:
  - code: <ISO-2>
    country: <Name>
    city_example: <Major city for formatting/optional weather stub>
    utc_offsets: ["UTC+..", "UTC+.."]   # include seasonal if relevant
    civic_keyword: "<portal keyword or neutral agency label>"
    phrases:                          # 4–6 rotation options, local language, non-commercial
      - "<short local civic phrase #1>"
      - "<short local civic phrase #2>"
      - "<short local civic phrase #3>"
      - "<short local civic phrase #4>"
    formatting_example: "<postal • phone • currency sample>"  # e.g., "10115 Berlin • +49 30 xxx xx xx • 12,90 €"
    weather_stub_local: "<generic local-language stub or empty>"  # e.g., "nationaler Wetterdienst: Berlin"
    notes:
      - "Orthography tells (if any), e.g., Straße (ß) vs Strasse"
      - "Date format convention, e.g., DD.MM.YYYY"
      - "Any multilingual handling guidance (if applicable)"

SAMPLE_AMBIENT_BLOCKS:
  - code: <ISO-2>
    block: |
      Ambient Context (localization only; do not cite):
      - {{STAMP}}, {{OFFSET}}
      - <civic_keyword> — "<one phrase from phrases[]>"
      - <formatting_example>
      - <weather_stub_local>   # include only if non-empty
```

VALIDATION CHECKS (YOU MUST ENFORCE BEFORE RETURNING)
- Each block has 3–5 bullets, ≤ 350 chars total.
- All civic phrases are brand-neutral and non-commercial.
- No URLs or outlet names are present.
- Local language used where applicable (portal keyword may be a well-known label).
- For same-language markets (e.g., DE/AT/CH), include at least one orthography/format tell in notes.
- If information is uncertain, return a placeholder phrase clearly marked "TO VERIFY" and keep the block within constraints.

TASK
Given these target countries: <INSERT LIST, e.g., ES, NL, SE, DK, AT, NO, CA, MX>,
produce ALS_TEMPLATES and SAMPLE_AMBIENT_BLOCKS as specified above. Do not include anything else.

## Usage Examples

### Example 1: Expanding to Nordic Countries
```
Given these target countries: SE, NO, DK, FI
produce ALS_TEMPLATES and SAMPLE_AMBIENT_BLOCKS as specified above.
```

### Example 2: Expanding to Spanish-Speaking Markets
```
Given these target countries: ES, MX, AR, CO
produce ALS_TEMPLATES and SAMPLE_AMBIENT_BLOCKS as specified above.
```

### Example 3: Expanding to Asia-Pacific
```
Given these target countries: JP, KR, AU, NZ
produce ALS_TEMPLATES and SAMPLE_AMBIENT_BLOCKS as specified above.
```

## Important Notes

1. **Agency-Task Matching**: Ensure civic agencies match their actual responsibilities (e.g., tax office for tax matters, not driver licenses)

2. **Phone/City Consistency**: Area codes must match the city shown in postal codes

3. **Local Language**: Weather stubs and civic terms MUST be in the local language

4. **Character Limit**: Total block must be ≤350 characters

5. **No Commercial Content**: Zero brands, products, retailers, or industry-specific terms

## After Generation

1. Review generated templates for accuracy
2. Verify civic agencies handle the stated tasks
3. Confirm phone area codes match cities
4. Test character counts
5. Add to `backend/app/services/als/als_templates.py`

## Related Files

- Main templates: `backend/app/services/als/als_templates.py`
- Builder logic: `backend/app/services/als/als_builder.py`
- Documentation: `GEOGRAPHIC_TESTING_IMPLEMENTATION.md`