"""
Test that all metadata displays correctly in the UI using Playwright
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright
import time
import json

def test_metadata_display():
    """Verify all metadata is displayed in the UI"""
    print("=" * 60)
    print("METADATA DISPLAY TEST")
    print("Testing: SHA-256, parameters, citations, provider badges, etc.")
    print("=" * 60)
    
    with sync_playwright() as p:
        print("\n[SETUP] Launching browser...")
        browser = p.chromium.launch(
            headless=False,
            slow_mo=100
        )
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        # Monitor console for errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)
        
        try:
            # Navigate to the app
            print("\n[STEP 1] Navigating to application...")
            page.goto("http://localhost:3001", wait_until="domcontentloaded", timeout=15000)
            time.sleep(2)
            
            # Enter brand name
            print("\n[STEP 2] Entering brand name...")
            brand_input = page.locator('input[type="text"]').first
            if brand_input.count() > 0:
                brand_input.fill("AVEA")
                brand_input.press("Enter")
                time.sleep(2)
                print("  ✓ Brand entered: AVEA")
            
            # Go to Templates tab
            print("\n[STEP 3] Checking Templates tab metadata...")
            templates_tab = page.locator('button').filter(has_text="templates")
            if templates_tab.count() == 0:
                templates_tab = page.locator('button').filter(has_text="Templates")
            
            if templates_tab.count() > 0:
                templates_tab.first.click()
                time.sleep(2)
            
            # Check for template metadata
            print("\n[TEMPLATES TAB METADATA]")
            
            # Check for SHA-256 hashes
            sha_elements = page.locator('text=/SHA-256.*/')
            if sha_elements.count() > 0:
                print(f"  ✓ SHA-256 hashes: {sha_elements.count()} found")
            else:
                print("  ✗ SHA-256 hashes: NOT FOUND")
            
            # Check for temperature/seed/top_p
            temp_elements = page.locator('text=/Temp:.*/')
            seed_elements = page.locator('text=/Seed:.*/')
            top_p_elements = page.locator('text=/Top-p:.*/')
            
            print(f"  {'✓' if temp_elements.count() > 0 else '✗'} Temperature: {temp_elements.count()} found")
            print(f"  {'✓' if seed_elements.count() > 0 else '✗'} Seed: {seed_elements.count()} found")
            print(f"  {'✓' if top_p_elements.count() > 0 else '✗'} Top-p: {top_p_elements.count()} found")
            
            # Check for run statistics
            run_stats = page.locator('text=/\\d+ runs.*successful/')
            if run_stats.count() > 0:
                print(f"  ✓ Run statistics: {run_stats.count()} found")
            else:
                print("  ✗ Run statistics: NOT FOUND")
            
            # Check for canonical JSON button - look for Show/Hide Canonical JSON
            canonical_btns = page.locator('button').filter(has_text="Canonical JSON")
            if canonical_btns.count() > 0:
                print(f"  ✓ Canonical JSON buttons: {canonical_btns.count()} found")
                # Try clicking one
                canonical_btns.first.click()
                time.sleep(1)
                # Check if JSON is displayed
                json_display = page.locator('pre.text-xs.font-mono')
                if json_display.count() > 0:
                    print("    ✓ Canonical JSON expands correctly")
            else:
                print("  ✗ Canonical JSON buttons: NOT FOUND (may not have canonical JSON data)")
            
            page.screenshot(path="metadata_templates.png")
            
            # Go to Results tab
            print("\n[STEP 4] Checking Results tab metadata...")
            results_tab = page.locator('button').filter(has_text="results")
            if results_tab.count() == 0:
                results_tab = page.locator('button').filter(has_text="Results")
            
            if results_tab.count() > 0:
                results_tab.first.click()
                time.sleep(2)
            
            print("\n[RESULTS TAB METADATA]")
            
            # Check for provider badges - look for colored model names
            provider_badges = page.locator('.text-green-600, .text-blue-600, .text-indigo-600')
            if provider_badges.count() > 0:
                print(f"  ✓ Provider badges: {provider_badges.count()} found")
                # Check specific providers
                gemini_badges = page.locator('span').filter(has_text="gemini-2.5-pro")
                gpt_badges = page.locator('span').filter(has_text="gpt-5")
                print(f"    - Gemini badges: {gemini_badges.count()}")
                print(f"    - GPT badges: {gpt_badges.count()}")
            else:
                print("  ✗ Provider badges: NOT FOUND")
            
            # Check for grounding badges
            grounding_badges = page.locator('text=/Model Knowledge|Grounded/')
            if grounding_badges.count() > 0:
                print(f"  ✓ Grounding badges: {grounding_badges.count()} found")
            else:
                print("  ✗ Grounding badges: NOT FOUND")
            
            # Check for tool call counts
            tool_calls = page.locator('text=/\\d+ tool calls/')
            if tool_calls.count() > 0:
                print(f"  ✓ Tool call counts: {tool_calls.count()} found")
            else:
                print("  ✗ Tool call counts: NOT FOUND")
            
            # Check for citation counts
            citation_counts = page.locator('text=/\\d+ citations/')
            if citation_counts.count() > 0:
                print(f"  ✓ Citation counts: {citation_counts.count()} found")
            else:
                print("  ✗ Citation counts: NOT FOUND")
            
            # Check for finish reasons
            finish_reasons = page.locator('text=/Token limit|Complete/')
            if finish_reasons.count() > 0:
                print(f"  ✓ Finish reasons: {finish_reasons.count()} found")
            else:
                print("  ✗ Finish reasons: NOT FOUND")
            
            # Try to view a response
            view_btns = page.locator('button:has-text("View Response")')
            if view_btns.count() > 0:
                print(f"\n  Clicking View Response button...")
                view_btns.first.click()
                time.sleep(2)
                
                # Check for expanded metadata
                print("\n[EXPANDED RESULT METADATA]")
                
                # Check for brand mention status
                brand_mention = page.locator('text=/Brand mentioned:.*Yes|No/')
                if brand_mention.count() > 0:
                    print("  ✓ Brand mention status: FOUND")
                
                # Check for confidence score
                confidence = page.locator('text=/Confidence:.*%/')
                if confidence.count() > 0:
                    print("  ✓ Confidence score: FOUND")
                
                # Check for citations section
                citations_section = page.locator('h4:has-text("Citations")')
                if citations_section.count() > 0:
                    print("  ✓ Citations section: FOUND")
                    # Check for clickable citation links
                    citation_links = page.locator('a[href][target="_blank"]').filter(has_text="🔗")
                    if citation_links.count() > 0:
                        print(f"    ✓ Clickable citation links: {citation_links.count()} found")
                
                # Check for grounding metadata section
                grounding_section = page.locator('h4:has-text("Grounding Metadata")')
                if grounding_section.count() > 0:
                    print("  ✓ Grounding metadata section: FOUND")
                
                # Check for fingerprint
                fingerprint = page.locator('text=/Fingerprint:/')
                if fingerprint.count() > 0:
                    print("  ✓ System fingerprint: FOUND")
                
                # Check for full SHA-256
                full_sha = page.locator('.font-mono').filter(has_text="SHA-256:")
                if full_sha.count() > 0:
                    print("  ✓ Full SHA-256 hash: FOUND")
            
            page.screenshot(path="metadata_results.png")
            
            # Check console errors
            print("\n[CONSOLE ERRORS]")
            if console_errors:
                print(f"  ✗ Found {len(console_errors)} console errors:")
                for error in console_errors[:5]:  # Show first 5
                    print(f"    - {error.text}")
            else:
                print("  ✓ No console errors detected")
            
            # Final summary
            print("\n" + "=" * 60)
            print("METADATA DISPLAY TEST SUMMARY")
            print("=" * 60)
            
            metadata_found = []
            metadata_missing = []
            
            # Templates tab checks
            if sha_elements.count() > 0: metadata_found.append("SHA-256 hashes")
            else: metadata_missing.append("SHA-256 hashes")
            
            if temp_elements.count() > 0: metadata_found.append("Temperature values")
            else: metadata_missing.append("Temperature values")
            
            if canonical_btns.count() > 0: metadata_found.append("Canonical JSON")
            else: metadata_missing.append("Canonical JSON")
            
            # Results tab checks
            if provider_badges.count() > 0: metadata_found.append("Provider badges")
            else: metadata_missing.append("Provider badges")
            
            if grounding_badges.count() > 0: metadata_found.append("Grounding badges")
            else: metadata_missing.append("Grounding badges")
            
            if citation_counts.count() > 0: metadata_found.append("Citation counts")
            else: metadata_missing.append("Citation counts")
            
            print("\n✅ FOUND:")
            for item in metadata_found:
                print(f"  - {item}")
            
            if metadata_missing:
                print("\n❌ MISSING:")
                for item in metadata_missing:
                    print(f"  - {item}")
            
            print(f"\nScore: {len(metadata_found)}/{len(metadata_found) + len(metadata_missing)}")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            page.screenshot(path="metadata_error.png")
            print("Error screenshot: metadata_error.png")
        
        finally:
            print("\n[END] Browser will stay open for manual inspection.")
            print("Press Enter to close...")
            input()
            browser.close()

if __name__ == "__main__":
    test_metadata_display()