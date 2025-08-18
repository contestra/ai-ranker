#!/usr/bin/env python
"""
Test the Templates and Results tabs through the API (simulating frontend interactions)
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

print("=" * 60)
print("TESTING FRONTEND TEMPLATES & RESULTS FUNCTIONALITY")
print("=" * 60)

# Step 1: Get existing templates
print("\n1. FETCHING EXISTING TEMPLATES...")
resp = requests.get(f"{BASE_URL}/api/prompt-tracking/templates")
if resp.status_code == 200:
    templates = resp.json()
    if isinstance(templates, dict):
        template_list = templates.get('templates', [])
    else:
        template_list = templates if isinstance(templates, list) else []
    
    print(f"   Found {len(template_list)} templates")
    
    # Show templates with grounding enabled
    grounding_templates = [t for t in template_list if 'web' in t.get('grounding_modes', [])]
    if grounding_templates:
        print(f"   Templates with grounding enabled: {len(grounding_templates)}")
        for t in grounding_templates[:3]:
            print(f"   - ID {t['id']}: {t['template_name']} (Model: {t.get('model_name', 'unknown')})")
else:
    print(f"   [ERROR] Failed to fetch templates: {resp.status_code}")
    template_list = []

# Step 2: Create a new template with grounding
print("\n2. CREATING NEW TEMPLATE WITH GROUNDING...")
new_template = {
    "template_name": f"Frontend Test - Grounding {int(time.time())}",
    "prompt_text": "What are the top 5 electric vehicle companies? Provide current market information.",
    "brand_name": "Tesla",  # Required field
    "model_name": "gemini-2.5-pro",  # Use a model that definitely supports grounding
    "countries": ["US", "GB"],
    "grounding_modes": ["web", "none"],
    "prompt_type": "recognition"
}

resp = requests.post(
    f"{BASE_URL}/api/prompt-tracking/templates",
    json=new_template
)

if resp.status_code in [200, 201]:
    created = resp.json()
    template_id = created.get('id')
    print(f"   [OK] Created template ID: {template_id}")
else:
    print(f"   [ERROR] Failed to create template: {resp.status_code}")
    print(f"   Response: {resp.text[:200]}")
    template_id = None

# Step 3: Run the template with grounding
if template_id:
    print("\n3. RUNNING TEMPLATE WITH GROUNDING...")
    print("   This will test both 'web' and 'none' modes for US and GB")
    
    run_data = {
        "template_id": template_id,
        "brand_name": "Tesla"
    }
    
    print("   Sending run request (this may take 30-60 seconds)...")
    start = time.time()
    resp = requests.post(
        f"{BASE_URL}/api/prompt-tracking/run",
        json=run_data,
        timeout=120
    )
    elapsed = time.time() - start
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"   [OK] Completed in {elapsed:.1f}s")
        
        # Check each result
        if "results" in result and result["results"]:
            print(f"\n   Results Summary:")
            print(f"   Template: {result.get('template_name', 'Unknown')}")
            print(f"   Brand: {result.get('brand_name', 'Unknown')}")
            print(f"   Total runs: {len(result['results'])}")
            
            grounded_count = 0
            citations_total = 0
            
            for r in result["results"]:
                country = r.get("country", "??")
                mode = r.get("grounding_mode", "??")
                grounded = r.get("grounded", False)
                grounding_meta = r.get("grounding_metadata", {})
                
                if grounding_meta:
                    actual_grounded = grounding_meta.get("grounded", False)
                    citations = grounding_meta.get("citations", [])
                    queries = grounding_meta.get("web_search_queries", [])
                else:
                    actual_grounded = grounded
                    citations = []
                    queries = []
                
                status = "[OK]" if (mode == "web" and actual_grounded) or (mode == "none" and not actual_grounded) else "[FAIL]"
                
                print(f"\n   {status} {country}/{mode}:")
                print(f"      Grounded: {actual_grounded}")
                print(f"      Citations: {len(citations)}")
                print(f"      Web queries: {len(queries)}")
                print(f"      Brand mentioned: {r.get('brand_mentioned', False)}")
                print(f"      Confidence: {r.get('confidence_score', 0)}")
                
                if actual_grounded:
                    grounded_count += 1
                    citations_total += len(citations)
                
                # Check citation format
                if citations and len(citations) > 0:
                    first = citations[0]
                    if isinstance(first, dict):
                        print(f"      Citation format: [OK] Dict with keys: {list(first.keys())[:3]}")
                    else:
                        print(f"      Citation format: [FAIL] Not a dict: {type(first)}")
            
            # Overall assessment
            print(f"\n   GROUNDING SUMMARY:")
            print(f"   - Runs with grounding active: {grounded_count}")
            print(f"   - Total citations collected: {citations_total}")
            print(f"   - Average citations per grounded run: {citations_total/grounded_count:.1f}" if grounded_count > 0 else "N/A")
            
            # Check if grounding worked for 'web' mode
            web_runs = [r for r in result["results"] if r.get("grounding_mode") == "web"]
            web_grounded = [r for r in web_runs if r.get("grounding_metadata", {}).get("grounded", False)]
            
            if web_runs:
                success_rate = len(web_grounded) / len(web_runs) * 100
                print(f"   - Web mode grounding success rate: {success_rate:.0f}%")
                
                if success_rate >= 50:
                    print(f"\n   [PASS] FRONTEND GROUNDING TEST PASSED!")
                else:
                    print(f"\n   [PARTIAL] GROUNDING PARTIALLY WORKING ({success_rate:.0f}% success)")
            else:
                print(f"\n   [FAIL] NO WEB MODE RUNS FOUND")
        else:
            print("   [ERROR] No results returned")
    else:
        print(f"   [ERROR] Run failed: {resp.status_code}")
        print(f"   Response: {resp.text[:500]}")

# Step 4: Test analytics endpoint
if template_id:
    print("\n4. TESTING ANALYTICS ENDPOINT...")
    resp = requests.get(f"{BASE_URL}/api/prompt-tracking/analytics/Tesla")
    
    if resp.status_code == 200:
        analytics = resp.json()
        print(f"   [OK] Analytics retrieved")
        print(f"   - Total runs: {analytics.get('overall', {}).get('total_runs', 0)}")
        print(f"   - Mention rate: {analytics.get('overall', {}).get('mention_rate', 0):.1f}%")
        print(f"   - Avg confidence: {analytics.get('overall', {}).get('average_confidence', 0):.2f}")
        
        by_grounding = analytics.get('by_grounding_mode', {})
        if by_grounding:
            print(f"   By grounding mode:")
            for mode, stats in by_grounding.items():
                print(f"   - {mode}: {stats.get('mention_rate', 0):.1f}% mention rate")
    else:
        print(f"   [ERROR] Analytics failed: {resp.status_code}")

print("\n" + "=" * 60)
print("FRONTEND FUNCTIONALITY TEST COMPLETE")
print("=" * 60)