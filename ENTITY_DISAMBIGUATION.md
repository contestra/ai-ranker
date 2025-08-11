# Entity Disambiguation System

## Overview

The Entity Strength Analysis tool now includes advanced entity disambiguation to detect when AI models (like GPT-5) confuse brands with similar names. This is critical for accurate brand strength measurement.

## Problem Statement

When testing brand recognition, AI models may confidently identify the wrong entity. For example:
- **AVEA Life** (longevity supplements company) gets confused with **Avea** (former Turkish telecom operator)
- **Delta** (airline) might be confused with **Delta** (faucets) or **Delta** (COVID variant)
- **Apple** (tech company) vs **Apple Records** (music label)

Without disambiguation, the tool might incorrectly report that a brand has "strong entity" status when the AI is actually talking about a completely different company.

## Solution Architecture

The solution works in two independent phases:
1. **Testing Phase**: Query AI with naked brand token (no hints)
2. **Verification Phase**: Compare AI's response against actual brand website

### 1. Website Verification System (POST-Response Only)

When a user provides a domain, the system:

```python
async def fetch_brand_info(domain: str) -> Dict[str, Any]:
    # Fetches website and analyzes content
    # This is used ONLY AFTER the AI responds, for verification
    # NEVER used to influence the AI query
    # Returns: {
    #     "primary_industry": "health/wellness",
    #     "industry_confidence": 90,
    #     "title": "avea | longevity supplements",
    #     "description": "..."
    # }
```

**Key Features:**
- Fetches website HTML content
- Extracts text from multiple sources:
  - Meta tags and descriptions
  - Open Graph tags (common in Shopify)
  - Page titles and headings
  - Content sections (hero, banner, products)
  - General page text
- Works with JavaScript-heavy sites (Shopify, React, etc.)
- Detects industry based on keyword analysis

### 2. Industry Detection

The system categorizes brands into industries based on keyword presence:

```python
industries = {
    "health/wellness": ["supplement", "health", "wellness", "nutrition", 
                       "vitamin", "longevity", "nmn", "nad+", "collagen"],
    "telecommunications": ["telecom", "mobile", "carrier", "network", 
                          "5g", "4g", "sim", "roaming"],
    "software/tech": ["software", "app", "platform", "api", "cloud", "saas"],
    # ... more industries
}
```

### 3. Naked Brand Token Testing

**CRITICAL**: The system ALWAYS queries AI models with the "naked brand token" - just the brand name without any hints or context. This ensures we're measuring genuine, unbiased brand recognition:

```python
# ALWAYS use naked brand token for authentic measurement:
"Tell me about AVEA. What do they do..."

# NEVER prime the prompt with industry hints:
# "Tell me about AVEA (the health company)..."  # DON'T DO THIS - IT BIASES THE TEST!
```

The website information is collected ONLY for post-response verification, never to influence the AI query.

### 4. Wrong Entity Detection

After receiving the AI's response, the system:

1. **Analyzes the response** for industry-specific keywords
2. **Compares** against the actual website's industry
3. **Detects mismatches** when AI talks about wrong industry
4. **Adjusts classification** accordingly:
   - Downgrades "KNOWN_STRONG" to "UNKNOWN" if wrong entity
   - Reduces confidence score
   - Updates reasoning to explain the confusion

```python
def classify_response(response_data, brand_name, brand_info):
    # Check if AI is talking about the wrong company
    if brand_info and brand_info.get("primary_industry"):
        actual_industry = brand_info["primary_industry"]
        
        # Analyze what industry the AI is describing
        ai_described_industry = detect_industry_from_response(response_text)
        
        if ai_described_industry != actual_industry:
            # AI is confused - talking about wrong entity
            label = "UNKNOWN"
            confidence = 20
            reasoning = f"Model identified a {ai_described_industry} company, but actual brand is {actual_industry}"
```

## How to Use

### In the UI (Frontend)

1. Navigate to **Entity Strength Analysis**
2. Enter your brand name (e.g., "AVEA")
3. Enter your website domain (e.g., "www.avea-life.com")
4. Click **Check Strength**

The system will:
- Verify what your brand actually does
- Query the AI model
- Detect if the AI is confused
- Show accurate strength classification

### Via API

```python
# Without domain verification (may get confused)
POST /api/brand-entity-strength
{
    "brand_name": "AVEA",
    "vendor": "openai",
    "include_reasoning": true
}

# With domain verification (disambiguation enabled)
POST /api/brand-entity-strength
{
    "brand_name": "AVEA",
    "domain": "www.avea-life.com",  # Enables disambiguation
    "vendor": "openai",
    "include_reasoning": true
}
```

## Response Classifications

- **KNOWN_STRONG**: AI has specific, verifiable knowledge about YOUR brand
- **KNOWN_WEAK**: AI recognizes the name but may be confused or lack details
- **UNKNOWN**: AI doesn't know your brand (or is talking about wrong entity)
- **EMPTY**: No response from AI

## Confidence Scoring

The confidence score reflects both:
1. How confident the AI is about the brand
2. Whether it's talking about the correct entity

Examples:
- **High confidence (80-100%)**: AI knows the specific brand well
- **Medium confidence (40-70%)**: Some knowledge but may be confused
- **Low confidence (0-30%)**: Unknown brand or wrong entity detected

## Technical Implementation

### Files Modified

1. **backend/app/api/brand_entity_strength.py**
   - Added `fetch_brand_info()` function for website analysis
   - Modified `create_probe_prompt()` to accept industry hints
   - Enhanced `classify_response()` with wrong entity detection

2. **frontend/src/components/EntityStrengthDashboard.tsx**
   - Added domain input field
   - Shows disambiguation warning when detected
   - Passes domain to API for verification

### Dependencies

- `httpx`: For fetching website content
- `beautifulsoup4`: For HTML parsing
- `langchain`: For AI model interactions

## Benefits

1. **Accurate Brand Strength Measurement**: No false positives from confused entities
2. **Competitive Intelligence**: Know if competitors have better AI recognition
3. **SEO/Content Strategy**: Understand what content helps AI identify your brand
4. **Brand Monitoring**: Track if AI models learn about your brand over time

## Future Enhancements

1. **Multi-source verification**: Check multiple pages beyond homepage
2. **Logo/image analysis**: Use visual cues for disambiguation
3. **Historical tracking**: Monitor how entity confusion changes over time
4. **Automated alerts**: Notify when AI starts confusing your brand
5. **Industry-specific prompts**: Tailored questions for different sectors

## Testing

To test the disambiguation system:

```python
# Test script: backend/test_avea_disambiguation.py
python test_avea_disambiguation.py

# This will:
# 1. Fetch the AVEA Life website
# 2. Detect it as health/wellness
# 3. Show how the system prevents confusion with Turkish telecom
```

## Conclusion

This entity disambiguation system ensures that brand strength measurements are accurate and meaningful. By verifying what a brand actually does and comparing it against AI responses, we can detect when AI models are confused and provide reliable brand intelligence.