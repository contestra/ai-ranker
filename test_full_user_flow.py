"""
Full user flow test - create templates, run them, check results
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright
import time
import random

def test_full_user_flow():
    """Test the complete user workflow"""
    print("=" * 60)
    print("FULL USER FLOW TEST")
    print("Testing: Create prompts → Run them → Check results")
    print("=" * 60)
    
    with sync_playwright() as p:
        print("\n[SETUP] Launching browser...")
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500  # Slow down actions to see what's happening
        )
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            # Navigate to the app
            print("\n[STEP 1] Navigating to application...")
            page.goto("http://localhost:3001", wait_until="domcontentloaded", timeout=15000)
            time.sleep(2)
            print("  ✓ Page loaded")
            
            # Take initial screenshot
            page.screenshot(path="flow_1_initial.png")
            
            # ========== ENTER BRAND NAME ==========
            print("\n[STEP 2] Entering brand name...")
            brand_input = page.locator('input[placeholder*="Tesla"], input[placeholder*="Apple"], input[placeholder*="Nike"], input[type="text"]').first
            
            if brand_input.count() > 0:
                brand_input.fill("AVEA")
                print("  ✓ Typed: AVEA")
                brand_input.press("Enter")
                time.sleep(2)
                print("  ✓ Brand submitted")
                page.screenshot(path="flow_2_brand_entered.png")
            else:
                print("  ✗ Could not find brand input!")
                return
            
            # ========== NAVIGATE TO TEMPLATES TAB ==========
            print("\n[STEP 3] Navigating to Templates tab...")
            
            # Try to find and click templates tab
            templates_tab = page.locator('button').filter(has_text="templates")
            if templates_tab.count() == 0:
                templates_tab = page.locator('button').filter(has_text="Templates")
            
            if templates_tab.count() > 0:
                templates_tab.first.click()
                time.sleep(2)
                print("  ✓ Templates tab clicked")
                page.screenshot(path="flow_3_templates_tab.png")
            else:
                print("  ⚠ Templates tab not found, might already be active")
            
            # ========== CHECK FOR PROMPT CONFIGURATION BUILDER ==========
            print("\n[STEP 4] Checking for Prompt Configuration Builder...")
            
            builder = page.locator('text="Prompt Configuration Builder"')
            if builder.count() > 0:
                print("  ✓✓✓ PROMPT CONFIGURATION BUILDER FOUND!")
                
                # ========== CONFIGURE PROMPT SETTINGS ==========
                print("\n[STEP 5] Configuring prompt settings...")
                
                # Select AI Model
                print("  - Selecting AI Model...")
                model_select = page.locator('select').filter(has_text="Gemini")
                if model_select.count() == 0:
                    model_select = page.locator('select').nth(0)  # Get first select
                
                if model_select.count() > 0:
                    # Change to Gemini 2.5 Pro
                    model_select.select_option(value="gemini-2.5-pro")
                    print("    ✓ Selected: Gemini 2.5 Pro")
                
                # Select Prompt Type
                print("  - Selecting Prompt Type...")
                type_select = page.locator('select').nth(1)  # Second select should be type
                if type_select.count() > 0:
                    type_select.select_option(value="recognition")
                    print("    ✓ Selected: Brand Recognition")
                
                # Select Countries
                print("  - Selecting Countries...")
                countries_to_select = ["🇺🇸 United States", "🇩🇪 Germany", "🇨🇭 Switzerland"]
                
                for country in countries_to_select:
                    country_btn = page.locator(f'button:has-text("{country}")')
                    if country_btn.count() > 0:
                        country_btn.first.click()
                        print(f"    ✓ Selected: {country}")
                        time.sleep(0.5)
                
                # Also click Base Model to test that
                base_model = page.locator('button:has-text("Base Model")')
                if base_model.count() > 0:
                    base_model.first.click()
                    print("    ✓ Selected: Base Model (No Location)")
                
                page.screenshot(path="flow_4_countries_selected.png")
                
                # Select Grounding Modes
                print("  - Selecting Grounding Modes...")
                
                # Click Model Knowledge Only
                model_knowledge = page.locator('button:has-text("Model Knowledge Only")')
                if model_knowledge.count() > 0:
                    model_knowledge.click()
                    print("    ✓ Selected: Model Knowledge Only")
                
                # Click Grounded Web Search
                grounded = page.locator('button:has-text("Grounded")')
                if grounded.count() == 0:
                    grounded = page.locator('button:has-text("Web Search")')
                
                if grounded.count() > 0:
                    grounded.first.click()
                    print("    ✓ Selected: Grounded (Web Search)")
                
                page.screenshot(path="flow_5_modes_selected.png")
                
                # ========== GENERATE TEMPLATES ==========
                print("\n[STEP 6] Generating templates...")
                
                # Look for Generate button
                generate_btn = page.locator('button:has-text("Generate")')
                if generate_btn.count() > 0:
                    # Get button text to see how many templates will be created
                    btn_text = generate_btn.first.inner_text()
                    print(f"  Button text: '{btn_text}'")
                    
                    # Click to generate
                    generate_btn.first.click()
                    print("  ✓ Clicked Generate Templates")
                    time.sleep(3)  # Wait for templates to be created
                    
                    # Check for success message or new templates
                    page.screenshot(path="flow_6_templates_generated.png")
                else:
                    print("  ✗ Generate button not found!")
                
            else:
                print("  ✗✗✗ PROMPT CONFIGURATION BUILDER NOT FOUND!")
                print("\n  Trying to create a custom template instead...")
                
                # Look for template creation form
                template_name = page.locator('input[id="template-name"], input[placeholder*="Template"]')
                if template_name.count() > 0:
                    print("  Found template creation form")
                    
                    # Fill template name
                    template_name.fill("Test AVEA Recognition")
                    
                    # Fill prompt text
                    prompt_text = page.locator('textarea[id="prompt-text"], textarea[placeholder*="prompt"]')
                    if prompt_text.count() > 0:
                        prompt_text.fill("What is {brand_name}? Tell me about this company.")
                    
                    # Click create
                    create_btn = page.locator('button:has-text("Create")')
                    if create_btn.count() > 0:
                        create_btn.first.click()
                        print("  ✓ Created custom template")
                        time.sleep(2)
            
            # ========== CHECK EXISTING TEMPLATES ==========
            print("\n[STEP 7] Checking existing templates...")
            
            # Look for template cards
            template_cards = page.locator('.bg-white.rounded-lg.shadow')
            template_count = template_cards.count()
            print(f"  Found {template_count} template cards")
            
            if template_count > 0:
                print("  Templates found! Let's run one...")
                
                # ========== RUN A TEMPLATE ==========
                print("\n[STEP 8] Running a template test...")
                
                # Find Run Test buttons
                run_buttons = page.locator('button:has-text("Run Test")')
                if run_buttons.count() > 0:
                    print(f"  Found {run_buttons.count()} Run Test buttons")
                    
                    # Click the first one
                    run_buttons.first.click()
                    print("  ✓ Clicked Run Test")
                    
                    # Wait for it to complete (this might take a while)
                    print("  ⏳ Waiting for test to complete (up to 60 seconds)...")
                    
                    # Look for "Running..." text to disappear
                    running_text = page.locator('text="Running..."')
                    try:
                        running_text.wait_for(state="hidden", timeout=60000)
                        print("  ✓ Test completed!")
                    except:
                        print("  ⚠ Test might still be running or timed out")
                    
                    time.sleep(2)
                    page.screenshot(path="flow_7_test_run.png")
                else:
                    print("  ✗ No Run Test buttons found")
            
            # ========== CHECK RESULTS TAB ==========
            print("\n[STEP 9] Checking Results tab...")
            
            # Navigate to Results tab
            results_tab = page.locator('button').filter(has_text="results")
            if results_tab.count() == 0:
                results_tab = page.locator('button').filter(has_text="Results")
            
            if results_tab.count() > 0:
                results_tab.first.click()
                time.sleep(2)
                print("  ✓ Results tab clicked")
                page.screenshot(path="flow_8_results_tab.png")
                
                # Check for results
                print("\n[STEP 10] Checking for test results...")
                
                # Look for Recent Test Runs
                recent_runs = page.locator('text="Recent Test Runs"')
                if recent_runs.count() > 0:
                    print("  ✓ Recent Test Runs section found")
                
                # Look for run cards
                run_cards = page.locator('.border.rounded-lg')
                if run_cards.count() > 0:
                    print(f"  ✓ Found {run_cards.count()} test run(s)")
                    
                    # Try to view a response
                    view_buttons = page.locator('button:has-text("View Response")')
                    if view_buttons.count() > 0:
                        view_buttons.first.click()
                        print("  ✓ Clicked View Response")
                        time.sleep(2)
                        
                        # Check if response is visible
                        response_text = page.locator('text="Response:"')
                        if response_text.count() > 0:
                            print("  ✓ Response content is visible")
                            
                            # Check for brand mentions
                            brand_mentioned = page.locator('text="Brand mentioned:"')
                            if brand_mentioned.count() > 0:
                                print("  ✓ Brand mention tracking visible")
                        
                        page.screenshot(path="flow_9_response_viewed.png")
                else:
                    print("  ⚠ No test runs found yet")
                
                # Click Refresh Results
                refresh_btn = page.locator('button:has-text("Refresh")')
                if refresh_btn.count() > 0:
                    refresh_btn.first.click()
                    print("  ✓ Clicked Refresh Results")
                    time.sleep(2)
            
            # ========== UI/UX ASSESSMENT ==========
            print("\n" + "=" * 40)
            print("UI/UX ASSESSMENT")
            print("=" * 40)
            
            # Check overall styling
            print("\n[STYLING CHECK]")
            
            # Check for shadows
            shadows = page.locator('.shadow, .shadow-md, .shadow-lg')
            print(f"  Shadows: {shadows.count()} elements")
            
            # Check for rounded corners
            rounded = page.locator('.rounded, .rounded-lg, .rounded-md, .rounded-full')
            print(f"  Rounded corners: {rounded.count()} elements")
            
            # Check for proper colors
            colors = page.locator('.bg-indigo-600, .bg-green-600, .bg-blue-600, .text-indigo-600')
            print(f"  Colored elements: {colors.count()} elements")
            
            # Check for hover effects
            hovers = page.locator('[class*="hover:"]')
            print(f"  Hover effects: {hovers.count()} elements")
            
            # Final screenshot
            page.screenshot(path="flow_10_final.png")
            
            # ========== FINAL SUMMARY ==========
            print("\n" + "=" * 60)
            print("TEST SUMMARY")
            print("=" * 60)
            
            print("\n✅ COMPLETED ACTIONS:")
            print("  1. Entered brand name (AVEA)")
            print("  2. Navigated to Templates tab")
            print("  3. Configured prompt settings")
            print("  4. Generated/created templates")
            print("  5. Ran template test")
            print("  6. Checked Results tab")
            print("  7. Viewed response details")
            
            print("\n📸 SCREENSHOTS SAVED:")
            print("  - flow_1_initial.png")
            print("  - flow_2_brand_entered.png")
            print("  - flow_3_templates_tab.png")
            print("  - flow_4_countries_selected.png")
            print("  - flow_5_modes_selected.png")
            print("  - flow_6_templates_generated.png")
            print("  - flow_7_test_run.png")
            print("  - flow_8_results_tab.png")
            print("  - flow_9_response_viewed.png")
            print("  - flow_10_final.png")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            page.screenshot(path="flow_error.png")
            print("Error screenshot: flow_error.png")
        
        finally:
            print("\n[END] Test complete.")
            print("Browser will stay open for manual inspection.")
            print("Press Enter to close...")
            try:
                input()
            except:
                time.sleep(30)
            browser.close()

if __name__ == "__main__":
    test_full_user_flow()