"""
Direct UI test - actually navigate to localhost:3001
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright
import time

def test_ui_direct():
    """Test the UI directly"""
    print("TESTING UI AT http://localhost:3001")
    print("=" * 50)
    
    with sync_playwright() as p:
        print("\n[1] Launching browser...")
        # Launch with visible browser
        browser = p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        print("[2] Navigating to http://localhost:3001...")
        
        # Try multiple times with different wait strategies
        url = "http://localhost:3001"
        
        try:
            # First attempt - just go to the URL
            response = page.goto(url, wait_until="domcontentloaded", timeout=15000)
            if response and response.ok:
                print(f"  ✓ Successfully loaded {url}")
                print(f"  Status: {response.status}")
            else:
                print(f"  ⚠ Page loaded but response not OK")
                
        except Exception as e:
            print(f"  ✗ Failed to load: {e}")
            print("\n[3] Trying alternative approach...")
            
            # Try just navigating without waiting
            try:
                page.goto(url, wait_until="commit", timeout=5000)
                print("  ✓ Navigation committed")
            except:
                print("  ✗ Still failing")
                
        # Wait a bit for page to settle
        time.sleep(3)
        
        # Check current URL
        current_url = page.url
        print(f"\n[4] Current URL: {current_url}")
        
        if "localhost:3001" not in current_url:
            print("  ✗ NOT on localhost:3001!")
            print("\n[5] Trying manual navigation...")
            
            # Try typing the URL in the address bar
            page.keyboard.press("Control+L")
            time.sleep(0.5)
            page.keyboard.type("http://localhost:3001")
            page.keyboard.press("Enter")
            time.sleep(5)
            
            current_url = page.url
            print(f"  Current URL after manual nav: {current_url}")
        
        # Now test the actual UI
        print("\n[6] Testing UI elements...")
        
        # Take screenshot of whatever is showing
        page.screenshot(path="ui_current_state.png")
        print("  Screenshot saved: ui_current_state.png")
        
        # Check for any content
        page_content = page.content()
        if len(page_content) > 500:
            print(f"  ✓ Page has content ({len(page_content)} chars)")
            
            # Look for key elements
            elements_to_find = [
                ("Brand input", 'input[type="text"]'),
                ("Templates text", 'text="templates"'),
                ("Results text", 'text="results"'),
                ("Prompt Tracking title", 'text="Prompt Tracking"'),
                ("AI Ranker", 'text="AI RANKER"'),
                ("Any button", 'button'),
                ("Any input", 'input')
            ]
            
            print("\n[7] Looking for UI elements...")
            for name, selector in elements_to_find:
                try:
                    count = page.locator(selector).count()
                    if count > 0:
                        print(f"  ✓ {name}: Found {count}")
                    else:
                        print(f"  ✗ {name}: Not found")
                except:
                    print(f"  ✗ {name}: Error checking")
                    
            # Try to interact
            print("\n[8] Attempting interactions...")
            
            # Try to find and fill brand input
            brand_inputs = page.locator('input[type="text"]')
            if brand_inputs.count() > 0:
                print(f"  Found {brand_inputs.count()} input fields")
                first_input = brand_inputs.first
                
                try:
                    # Check placeholder
                    placeholder = first_input.get_attribute("placeholder")
                    print(f"  First input placeholder: '{placeholder}'")
                    
                    # Try to fill it
                    first_input.fill("AVEA")
                    print("  ✓ Filled brand name: AVEA")
                    
                    # Press Enter
                    first_input.press("Enter")
                    print("  ✓ Pressed Enter")
                    
                    time.sleep(2)
                    page.screenshot(path="ui_after_brand.png")
                    print("  Screenshot saved: ui_after_brand.png")
                    
                except Exception as e:
                    print(f"  ✗ Could not interact with input: {e}")
                    
            # Check for tabs
            print("\n[9] Looking for tabs...")
            tabs = page.locator('button, a').filter(has_text="templates")
            if tabs.count() > 0:
                print(f"  ✓ Found Templates tab")
                tabs.first.click()
                time.sleep(1)
                page.screenshot(path="ui_templates_tab.png")
                print("  ✓ Clicked Templates tab")
                
                # Now look for the Prompt Configuration Builder
                print("\n[10] Checking Templates tab content...")
                builder = page.locator('text="Prompt Configuration Builder"')
                if builder.count() > 0:
                    print("  ✓✓✓ PROMPT CONFIGURATION BUILDER FOUND!")
                else:
                    print("  ✗✗✗ Prompt Configuration Builder NOT FOUND")
                    
                    # Check what IS there
                    print("\n  Looking for any template-related content...")
                    template_elements = [
                        "Create New Template",
                        "Create Template", 
                        "Template Name",
                        "Countries",
                        "Grounding",
                        "Model"
                    ]
                    
                    for elem in template_elements:
                        if page.locator(f'text="{elem}"').count() > 0:
                            print(f"    ✓ Found: {elem}")
                        else:
                            print(f"    ✗ Missing: {elem}")
                            
        else:
            print(f"  ✗ Page appears empty ({len(page_content)} chars)")
            
        print("\n" + "=" * 50)
        print("TEST COMPLETE - Check screenshots")
        print("=" * 50)
        
        # Keep browser open
        print("\nBrowser will stay open. Press Enter to close...")
        try:
            input()
        except:
            time.sleep(30)  # Keep open for 30 seconds if can't read input
            
        browser.close()

if __name__ == "__main__":
    test_ui_direct()