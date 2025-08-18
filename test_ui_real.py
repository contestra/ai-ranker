"""
Real UI test - properly navigate to localhost:3001
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright
import time

def test_ui_real():
    """Actually test the real UI at localhost:3001"""
    print("REAL UI TEST - http://localhost:3001")
    print("=" * 50)
    
    with sync_playwright() as p:
        print("\n[1] Launching browser with URL...")
        
        # Launch browser with the URL directly
        browser = p.chromium.launch(
            headless=False,
            args=['--start-maximized', '--disable-blink-features=AutomationControlled']
        )
        
        # Create context and page
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        page = context.new_page()
        
        print("[2] Going to http://localhost:3001...")
        
        # Navigate with multiple fallback approaches
        success = False
        
        # Approach 1: Standard navigation
        try:
            page.goto("http://localhost:3001/", timeout=10000)
            time.sleep(2)
            if "localhost" in page.url:
                success = True
                print("  ✓ Successfully navigated to localhost:3001")
        except Exception as e:
            print(f"  First attempt failed: {e}")
        
        # Approach 2: Navigate without waiting
        if not success:
            try:
                print("  Trying without wait...")
                page.evaluate('window.location.href = "http://localhost:3001/"')
                time.sleep(3)
                if "localhost" in page.url:
                    success = True
                    print("  ✓ Navigation successful via JavaScript")
            except:
                pass
        
        # Approach 3: Force navigation
        if not success:
            print("  Using force navigation...")
            page.goto("http://127.0.0.1:3001/", timeout=5000, wait_until="commit")
            time.sleep(2)
            if "127.0.0.1" in page.url or "localhost" in page.url:
                success = True
                print("  ✓ Navigation successful via 127.0.0.1")
        
        current_url = page.url
        print(f"\n[3] Current URL: {current_url}")
        
        if not success or "blank" in current_url:
            print("\n⚠️ NAVIGATION ISSUE DETECTED")
            print("The frontend server might not be running properly.")
            print("Please ensure:")
            print("  1. Frontend is running on port 3001")
            print("  2. No firewall blocking localhost")
            print("  3. Next.js compiled successfully")
            
            # Try one more time with a fresh page
            print("\n[4] Creating fresh page...")
            page2 = context.new_page()
            page2.goto("http://localhost:3001", wait_until="commit")
            time.sleep(2)
            
            if "localhost" in page2.url:
                page = page2
                success = True
                print("  ✓ Fresh page worked!")
        
        if success:
            # Now actually test the UI
            print("\n[5] Testing the actual UI...")
            
            # Take screenshot
            page.screenshot(path="ui_real_1.png")
            print("  Screenshot: ui_real_1.png")
            
            # Get page title
            title = page.title()
            print(f"  Page title: '{title}'")
            
            # Check for React app
            react_root = page.locator('#__next, #root, div[data-reactroot]')
            if react_root.count() > 0:
                print("  ✓ React app detected")
            
            # Look for brand input
            print("\n[6] Looking for brand input...")
            brand_input = page.locator('input[placeholder*="Tesla"], input[placeholder*="Apple"], input[placeholder*="Nike"], input[placeholder*="brand"]')
            
            if brand_input.count() > 0:
                print(f"  ✓ Found brand input")
                placeholder = brand_input.first.get_attribute("placeholder")
                print(f"  Placeholder: '{placeholder}'")
                
                # Fill brand name
                brand_input.first.fill("AVEA")
                brand_input.first.press("Enter")
                print("  ✓ Entered brand: AVEA")
                
                time.sleep(2)
                page.screenshot(path="ui_real_2_brand.png")
                
                # Now check for tabs
                print("\n[7] Checking for tabs...")
                
                # Look for templates tab
                templates = page.locator('button:text-is("templates"), button:text-is("Templates"), a:text-is("templates"), a:text-is("Templates")')
                if templates.count() > 0:
                    print("  ✓ Templates tab found")
                    templates.first.click()
                    time.sleep(1)
                    page.screenshot(path="ui_real_3_templates.png")
                    
                    # CHECK FOR PROMPT CONFIGURATION BUILDER
                    print("\n[8] CHECKING FOR PROMPT CONFIGURATION BUILDER...")
                    
                    builder_selectors = [
                        'text="Prompt Configuration Builder"',
                        'h3:text("Prompt Configuration Builder")',
                        'text="Generate immutable test prompts"',
                        'text="Select Countries"',
                        'text="Grounding Modes"'
                    ]
                    
                    builder_found = False
                    for selector in builder_selectors:
                        elem = page.locator(selector)
                        if elem.count() > 0:
                            print(f"  ✓✓✓ FOUND: {selector}")
                            builder_found = True
                            break
                    
                    if not builder_found:
                        print("  ✗✗✗ PROMPT CONFIGURATION BUILDER NOT FOUND!")
                        print("\n  Checking what IS visible in Templates tab:")
                        
                        # Get all visible text
                        visible_text = page.locator('body').inner_text()
                        
                        # Check for template-related keywords
                        keywords = ["Template", "Create", "Prompt", "Country", "Countries", "Grounding", "Model", "Generate"]
                        for keyword in keywords:
                            if keyword.lower() in visible_text.lower():
                                print(f"    Found keyword: {keyword}")
                    
                    # Test country buttons
                    print("\n[9] Testing country selection...")
                    countries_to_test = ["🇺🇸", "🇩🇪", "🇨🇭", "Base Model"]
                    
                    for country in countries_to_test:
                        btn = page.locator(f'button:has-text("{country}")')
                        if btn.count() > 0:
                            btn.first.click()
                            print(f"  ✓ Clicked {country}")
                            time.sleep(0.5)
                    
                    page.screenshot(path="ui_real_4_countries.png")
                    
                    # Test grounding modes
                    print("\n[10] Testing grounding modes...")
                    modes = ["Model Knowledge", "Grounded", "Web Search"]
                    
                    for mode in modes:
                        btn = page.locator(f'button:has-text("{mode}")')
                        if btn.count() > 0:
                            btn.first.click()
                            print(f"  ✓ Clicked {mode}")
                            time.sleep(0.5)
                    
                    page.screenshot(path="ui_real_5_modes.png")
                    
                    # Check Results tab
                    print("\n[11] Checking Results tab...")
                    results = page.locator('button:text-is("results"), button:text-is("Results"), a:text-is("results"), a:text-is("Results")')
                    if results.count() > 0:
                        results.first.click()
                        time.sleep(1)
                        page.screenshot(path="ui_real_6_results.png")
                        print("  ✓ Results tab clicked")
                        
                        # Check for results content
                        recent_runs = page.locator('text="Recent Test Runs"')
                        if recent_runs.count() > 0:
                            print("  ✓ Recent Test Runs section found")
                        
                        refresh_btn = page.locator('button:has-text("Refresh")')
                        if refresh_btn.count() > 0:
                            print("  ✓ Refresh button found")
                
                else:
                    print("  ✗ Templates tab NOT found")
                    print("  Available buttons:")
                    buttons = page.locator('button')
                    for i in range(min(5, buttons.count())):
                        text = buttons.nth(i).inner_text()
                        print(f"    - {text}")
                        
            else:
                print("  ✗ Brand input NOT found")
                print("  Checking what's on the page...")
                
                # List all inputs
                all_inputs = page.locator('input')
                print(f"  Found {all_inputs.count()} input fields")
                
                for i in range(min(3, all_inputs.count())):
                    inp = all_inputs.nth(i)
                    inp_type = inp.get_attribute("type")
                    inp_placeholder = inp.get_attribute("placeholder")
                    print(f"    Input {i+1}: type='{inp_type}', placeholder='{inp_placeholder}'")
        
        print("\n" + "=" * 50)
        print("UI TEST COMPLETE")
        print("Screenshots saved:")
        print("  - ui_real_1.png (initial)")
        print("  - ui_real_2_brand.png (after brand)")
        print("  - ui_real_3_templates.png (templates tab)")
        print("  - ui_real_4_countries.png (countries selected)")
        print("  - ui_real_5_modes.png (modes selected)")
        print("  - ui_real_6_results.png (results tab)")
        print("=" * 50)
        
        # Keep browser open for manual inspection
        print("\nKeeping browser open for manual inspection...")
        print("You can interact with the page manually.")
        print("Press Enter to close browser...")
        
        try:
            input()
        except:
            # If can't read input, just wait
            time.sleep(60)
        
        browser.close()
        print("Browser closed.")

if __name__ == "__main__":
    test_ui_real()