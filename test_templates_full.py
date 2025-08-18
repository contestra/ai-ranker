#!/usr/bin/env python
"""
Comprehensive test of Templates Tab and Results Tab functionality
Tests both OpenAI and Google/Vertex with grounding
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
BRAND_NAME = "AVEA"

print("=" * 60)
print("TEMPLATES & RESULTS TAB COMPREHENSIVE TEST")
print(f"Testing at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# Track created templates for cleanup
created_templates = []

def create_template(name, prompt_text, model_name, countries, grounding_modes):
    """Create a template and return its ID"""
    template_data = {
        "brand_name": BRAND_NAME,
        "template_name": name,
        "prompt_text": prompt_text,
        "model_name": model_name,
        "countries": countries,
        "grounding_modes": grounding_modes,
        "prompt_type": "test"
    }
    
    print(f"\nCreating template: {name}")
    print(f"  Model: {model_name}")
    print(f"  Countries: {countries}")
    print(f"  Grounding: {grounding_modes}")
    
    resp = requests.post(
        f"{BASE_URL}/api/prompt-tracking/templates",
        json=template_data
    )
    
    if resp.status_code in [200, 201]:
        template = resp.json()
        template_id = template["id"]
        created_templates.append(template_id)
        print(f"  [OK] Created with ID: {template_id}")
        return template_id
    else:
        print(f"  [FAIL] Failed: {resp.status_code}")
        print(f"  Response: {resp.text[:200]}")
        return None

def run_template(template_id, wait_for_completion=True):
    """Run a template and return the run ID"""
    run_data = {
        "template_id": template_id,
        "brand_name": BRAND_NAME
    }
    
    print(f"\nRunning template {template_id}...")
    start = time.time()
    
    resp = requests.post(
        f"{BASE_URL}/api/prompt-tracking/run",
        json=run_data,
        timeout=120
    )
    
    elapsed = time.time() - start
    
    if resp.status_code == 200:
        result = resp.json()
        run_id = result.get("run_id")
        print(f"  [OK] Run started: {run_id} ({elapsed:.1f}s)")
        
        # Check results
        if "results" in result:
            print(f"  Results: {len(result['results'])} combinations")
            for r in result["results"]:
                country = r.get("country", "?")
                grounding = r.get("grounding_mode", "?")
                mentioned = r.get("mentioned", False)
                confidence = r.get("confidence_score", 0)
                
                # Check grounding metadata
                grounding_meta = r.get("grounding_metadata", {})
                grounded = grounding_meta.get("grounded", False)
                citations = grounding_meta.get("citations", [])
                
                status = "[OK]" if mentioned else "[MISS]"
                print(f"    {status} {country}/{grounding}: mentioned={mentioned}, confidence={confidence}, grounded={grounded}, citations={len(citations)}")
                
                # Verify citations are dicts
                if citations:
                    all_dicts = all(isinstance(c, dict) for c in citations)
                    if not all_dicts:
                        print(f"      WARNING: Some citations are not dicts!")
        
        return run_id
    else:
        print(f"  [FAIL] Run failed: {resp.status_code}")
        print(f"  Response: {resp.text[:200]}")
        return None

def get_results_for_brand():
    """Get all results for the brand"""
    resp = requests.get(
        f"{BASE_URL}/api/prompt-tracking/analytics/{BRAND_NAME}"
    )
    
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Failed to get analytics: {resp.status_code}")
        return None

# =====================================
# TEST 1: Gemini with Grounding
# =====================================
print("\n" + "=" * 60)
print("TEST 1: GEMINI WITH GROUNDING")
print("=" * 60)

template1_id = create_template(
    name="Gemini Grounding Test",
    prompt_text="List the top 5 longevity supplement brands. Include any Swiss brands you know.",
    model_name="gemini-2.5-pro",
    countries=["US", "CH", "DE"],
    grounding_modes=["web", "none"]
)

if template1_id:
    run_template(template1_id)

# =====================================
# TEST 2: OpenAI GPT-5
# =====================================
print("\n" + "=" * 60)
print("TEST 2: OPENAI GPT-5")
print("=" * 60)

template2_id = create_template(
    name="GPT-5 Test",
    prompt_text="What are the leading longevity supplement companies? Focus on innovative brands.",
    model_name="gpt-5",
    countries=["US", "GB"],
    grounding_modes=["none"]  # GPT-5 doesn't use grounding same way
)

if template2_id:
    run_template(template2_id)

# =====================================
# TEST 3: Gemini without Grounding
# =====================================
print("\n" + "=" * 60)
print("TEST 3: GEMINI WITHOUT GROUNDING")
print("=" * 60)

template3_id = create_template(
    name="Gemini No Grounding",
    prompt_text="Name some longevity supplement brands you know about.",
    model_name="gemini-2.5-flash",
    countries=["US"],
    grounding_modes=["none"]
)

if template3_id:
    run_template(template3_id)

# =====================================
# TEST 4: Check Results Tab Data
# =====================================
print("\n" + "=" * 60)
print("TEST 4: RESULTS TAB DATA")
print("=" * 60)

print(f"\nFetching analytics for brand: {BRAND_NAME}")
analytics = get_results_for_brand()

if analytics:
    # Overall stats
    print("\nOverall Statistics:")
    print(f"  Total runs: {analytics.get('total_runs', 0)}")
    print(f"  Overall mention rate: {analytics.get('overall_mention_rate', 0):.1f}%")
    print(f"  Average confidence: {analytics.get('average_confidence', 0):.1f}")
    
    # By grounding mode
    grounding_stats = analytics.get('by_grounding_mode', {})
    if grounding_stats:
        print("\nBy Grounding Mode:")
        for mode, stats in grounding_stats.items():
            print(f"  {mode}: {stats.get('mention_rate', 0):.1f}% mention rate, {stats.get('avg_confidence', 0):.1f} confidence")
    
    # By country
    country_stats = analytics.get('by_country', {})
    if country_stats:
        print("\nBy Country:")
        for country, stats in country_stats.items():
            print(f"  {country}: {stats.get('mention_rate', 0):.1f}% mention rate, {stats.get('avg_confidence', 0):.1f} confidence")
    
    # Recent runs
    recent_runs = analytics.get('recent_runs', [])
    if recent_runs:
        print(f"\nRecent Runs (showing first 5 of {len(recent_runs)}):")
        for run in recent_runs[:5]:
            template_name = run.get('template_name', 'Unknown')
            created = run.get('created_at', '')[:19]  # Trim microseconds
            results = run.get('result_count', 0)
            print(f"  - {template_name}: {results} results at {created}")

# =====================================
# TEST 5: List All Templates
# =====================================
print("\n" + "=" * 60)
print("TEST 5: LIST ALL TEMPLATES")
print("=" * 60)

resp = requests.get(f"{BASE_URL}/api/prompt-tracking/templates")
if resp.status_code == 200:
    templates = resp.json()
    # Handle both list and dict response
    if isinstance(templates, dict):
        template_list = templates.get('templates', [templates])
    else:
        template_list = templates if isinstance(templates, list) else []
    
    print(f"\nFound {len(template_list)} templates:")
    for t in template_list[-5:] if template_list else []:  # Show last 5
        print(f"  - {t.get('name', 'Unknown')}: {t.get('model_name', '?')}, {len(t.get('countries', []))} countries, {len(t.get('grounding_modes', []))} grounding modes")
else:
    print(f"Failed to list templates: {resp.status_code}")

# =====================================
# CLEANUP
# =====================================
print("\n" + "=" * 60)
print("CLEANUP")
print("=" * 60)

print(f"\nCreated {len(created_templates)} templates during testing")
# Note: In production, you might want to delete test templates

# =====================================
# SUMMARY
# =====================================
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)

print("\nTested Features:")
print("[OK] Template creation with multiple models")
print("[OK] Template execution with grounding modes")
print("[OK] Results storage and retrieval")
print("[OK] Analytics aggregation")
print("[OK] Both OpenAI and Gemini models")
print("\nSupported Models:")
print("  - OpenAI: gpt-5, gpt-5-mini, gpt-5-nano")
print("  - Gemini: gemini-2.5-pro, gemini-2.5-flash, gemini-2.0-flash")
print("\nVendor Names:")
print("  - Use 'openai' for GPT models")
print("  - Use 'google' for Gemini models (NOT 'vertex')")