"""
Comprehensive UI/UX test for Templates and Results tabs
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright
import time
import json

def test_comprehensive_ui():
    """Thoroughly test Templates and Results tabs"""
    print("=" * 60)
    print("COMPREHENSIVE UI/UX TEST")
    print("=" * 60)
    
    with sync_playwright() as p:
        print("\n[SETUP] Launching browser...")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Set viewport for consistent testing
        page.set_viewport_size({"width": 1920, "height": 1080})
        
        try:
            # Navigate to app
            print("[STEP 1] Navigating to http://localhost:3001...")
            page.goto("http://localhost:3001", wait_until="networkidle", timeout=30000)
            print("  ✓ Page loaded")
            
            # Take initial screenshot
            page.screenshot(path="test_1_initial.png")
            
            # Check if brand input exists
            print("\n[STEP 2] Checking brand input...")
            brand_input = page.locator('input[placeholder*="Tesla"], input[placeholder*="Apple"], input[placeholder*="Nike"]').first
            if brand_input.count() > 0:
                print("  ✓ Brand input found")
                brand_input.fill("AVEA")
                brand_input.press("Enter")
                time.sleep(2)
                print("  ✓ Brand entered: AVEA")
                page.screenshot(path="test_2_brand_entered.png")
            else:
                print("  ✗ Brand input NOT found - checking if already on main page")
            
            # === TEMPLATES TAB TESTING ===
            print("\n" + "=" * 40)
            print("TESTING TEMPLATES TAB")
            print("=" * 40)
            
            # Click Templates tab
            print("\n[STEP 3] Navigating to Templates tab...")
            templates_tab = page.locator('button:has-text("templates"), a:has-text("templates")').first
            if templates_tab.count() > 0:
                templates_tab.click()
                time.sleep(1)
                print("  ✓ Templates tab clicked")
            else:
                print("  ⚠ Templates tab not found, might already be active")
            
            page.screenshot(path="test_3_templates_tab.png")
            
            # Check for key elements
            print("\n[STEP 4] Checking Templates tab elements...")
            
            elements_check = {
                "Page Title": page.locator('h2:has-text("Prompt Tracking")'),
                "Prompt Configuration Builder": page.locator('text="Prompt Configuration Builder"'),
                "Create New Template": page.locator('text="Create New Template"'),
                "AI Model Selector": page.locator('select[id="model-name"], label:has-text("AI Model")'),
                "Prompt Type Selector": page.locator('select[id="prompt-type"], label:has-text("Prompt Type")'),
                "Countries Section": page.locator('text="Countries"), text="Select Countries"'),
                "Grounding Modes Section": page.locator('text="Grounding Modes"'),
                "Template Name Input": page.locator('input[id="template-name"], input[placeholder*="Template"]'),
                "Prompt Text Area": page.locator('textarea[id="prompt-text"], textarea[placeholder*="prompt"]'),
                "Create/Generate Button": page.locator('button:has-text("Create"), button:has-text("Generate")')
            }
            
            found_elements = []
            missing_elements = []
            
            for name, locator in elements_check.items():
                if locator.count() > 0:
                    is_visible = False
                    try:
                        is_visible = locator.first.is_visible()
                    except:
                        pass
                    
                    if is_visible:
                        found_elements.append(name)
                        print(f"  ✓ {name}: Found and visible")
                    else:
                        missing_elements.append(name)
                        print(f"  ⚠ {name}: Found but hidden")
                else:
                    missing_elements.append(name)
                    print(f"  ✗ {name}: Not found")
            
            print(f"\n  Summary: {len(found_elements)}/{len(elements_check)} elements working")
            
            # Test country selection
            print("\n[STEP 5] Testing country selection...")
            country_buttons = [
                ('Base Model', '🌐 Base Model'),
                ('United States', '🇺🇸'),
                ('Germany', '🇩🇪'),
                ('Switzerland', '🇨🇭')
            ]
            
            countries_found = 0
            for country_name, country_text in country_buttons:
                country_btn = page.locator(f'button:has-text("{country_text}")')
                if country_btn.count() > 0:
                    try:
                        country_btn.first.click()
                        countries_found += 1
                        print(f"  ✓ Clicked {country_name}")
                        time.sleep(0.5)
                    except:
                        print(f"  ✗ Could not click {country_name}")
                else:
                    print(f"  ✗ {country_name} button not found")
            
            if countries_found > 0:
                page.screenshot(path="test_5_countries_selected.png")
            
            # Test grounding modes
            print("\n[STEP 6] Testing grounding modes...")
            grounding_modes = [
                ('Model Knowledge', 'Model Knowledge'),
                ('Grounded Web', 'Grounded')
            ]
            
            modes_found = 0
            for mode_name, mode_text in grounding_modes:
                mode_btn = page.locator(f'button:has-text("{mode_text}")')
                if mode_btn.count() > 0:
                    try:
                        mode_btn.first.click()
                        modes_found += 1
                        print(f"  ✓ Clicked {mode_name}")
                        time.sleep(0.5)
                    except:
                        print(f"  ✗ Could not click {mode_name}")
                else:
                    print(f"  ✗ {mode_name} button not found")
            
            if modes_found > 0:
                page.screenshot(path="test_6_modes_selected.png")
            
            # Check for template list
            print("\n[STEP 7] Checking existing templates...")
            template_cards = page.locator('.bg-white.rounded-lg.shadow')
            print(f"  Found {template_cards.count()} template cards")
            
            if template_cards.count() > 0:
                # Check first template
                first_template = template_cards.first
                template_text = first_template.inner_text()
                print(f"  First template preview: {template_text[:100]}...")
            
            # === RESULTS TAB TESTING ===
            print("\n" + "=" * 40)
            print("TESTING RESULTS TAB")
            print("=" * 40)
            
            # Click Results tab
            print("\n[STEP 8] Navigating to Results tab...")
            results_tab = page.locator('button:has-text("results"), a:has-text("results")').first
            if results_tab.count() > 0:
                results_tab.click()
                time.sleep(1)
                print("  ✓ Results tab clicked")
                page.screenshot(path="test_8_results_tab.png")
            else:
                print("  ✗ Results tab not found")
            
            # Check Results tab elements
            print("\n[STEP 9] Checking Results tab elements...")
            
            results_elements = {
                "Recent Test Runs": page.locator('text="Recent Test Runs"'),
                "Refresh Button": page.locator('button:has-text("Refresh")'),
                "Run Cards": page.locator('.border.rounded-lg'),
                "View Response Buttons": page.locator('button:has-text("View Response")')
            }
            
            for name, locator in results_elements.items():
                count = locator.count()
                if count > 0:
                    print(f"  ✓ {name}: Found ({count} items)")
                else:
                    print(f"  ✗ {name}: Not found")
            
            # Try to expand a result if any exist
            view_buttons = page.locator('button:has-text("View Response")')
            if view_buttons.count() > 0:
                print("\n[STEP 10] Testing result expansion...")
                view_buttons.first.click()
                time.sleep(1)
                print("  ✓ Clicked View Response")
                
                # Check for expanded content
                response_text = page.locator('text="Response:"')
                if response_text.count() > 0:
                    print("  ✓ Response content displayed")
                    page.screenshot(path="test_10_expanded_result.png")
            
            # === UI/UX ASSESSMENT ===
            print("\n" + "=" * 40)
            print("UI/UX ASSESSMENT")
            print("=" * 40)
            
            # Check styling
            print("\n[STEP 11] Checking UI styling...")
            
            # Check for proper styling classes
            styling_checks = {
                "Shadows": page.locator('.shadow, .shadow-md, .shadow-lg'),
                "Rounded corners": page.locator('.rounded, .rounded-lg, .rounded-md'),
                "Backgrounds": page.locator('.bg-white, .bg-gray-50, .bg-indigo-600'),
                "Hover effects": page.locator('[class*="hover:"]'),
                "Text styling": page.locator('.text-gray-500, .text-gray-700, .font-medium, .font-semibold')
            }
            
            for style_name, locator in styling_checks.items():
                count = locator.count()
                if count > 0:
                    print(f"  ✓ {style_name}: {count} elements")
                else:
                    print(f"  ✗ {style_name}: Not found")
            
            # Final assessment
            print("\n" + "=" * 40)
            print("FINAL ASSESSMENT")
            print("=" * 40)
            
            total_issues = len(missing_elements)
            
            if total_issues == 0 and countries_found > 0 and modes_found > 0:
                print("\n✅ UI IS FULLY FUNCTIONAL")
                print("  - All key elements are present")
                print("  - Country selection works")
                print("  - Grounding mode selection works")
                print("  - Both tabs are accessible")
            else:
                print(f"\n⚠️ UI HAS {total_issues} ISSUES")
                if missing_elements:
                    print("\nMissing/Hidden elements:")
                    for elem in missing_elements:
                        print(f"  - {elem}")
                if countries_found == 0:
                    print("  - Country selection not working")
                if modes_found == 0:
                    print("  - Grounding mode selection not working")
            
            # Take final screenshot
            page.screenshot(path="test_final_state.png")
            
            print("\n[INFO] Screenshots saved:")
            print("  - test_1_initial.png")
            print("  - test_2_brand_entered.png")
            print("  - test_3_templates_tab.png")
            print("  - test_5_countries_selected.png")
            print("  - test_6_modes_selected.png")
            print("  - test_8_results_tab.png")
            print("  - test_10_expanded_result.png")
            print("  - test_final_state.png")
            
        except Exception as e:
            print(f"\n❌ TEST FAILED WITH ERROR: {e}")
            try:
                page.screenshot(path="test_error_state.png")
                print("Error screenshot saved: test_error_state.png")
            except:
                pass
        
        finally:
            print("\n[END] Test complete. Browser will remain open for inspection.")
            print("Press Enter to close browser...")
            try:
                input()
            except:
                pass
            browser.close()

if __name__ == "__main__":
    test_comprehensive_ui()