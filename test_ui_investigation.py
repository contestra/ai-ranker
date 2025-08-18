"""
Investigate UI issues with Playwright
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright
import time
import json

def investigate_ui():
    """Use Playwright to investigate the UI issues"""
    print("[INVESTIGATION] Starting UI investigation...")
    
    with sync_playwright() as p:
        print("[INFO] Launching browser...")
        browser = p.chromium.launch(headless=False)  # Show browser for debugging
        page = browser.new_page()
        
        # Wait for servers to be ready
        print("[INFO] Waiting for servers to start...")
        time.sleep(5)
        
        try:
            print("[INFO] Navigating to localhost:3001...")
            page.goto("http://localhost:3001", wait_until="domcontentloaded", timeout=30000)
            
            # Take screenshot of current state
            page.screenshot(path="ui_initial_state.png")
            print("[SUCCESS] Initial screenshot saved")
            
            # Enter brand name to access the main UI
            print("[ACTION] Entering brand name...")
            brand_input = page.locator('input[placeholder*="Tesla"]')
            if brand_input.count() > 0:
                brand_input.fill("TestBrand")
                brand_input.press("Enter")
                time.sleep(2)
                page.screenshot(path="ui_after_brand.png")
                print("[SUCCESS] Brand entered")
            
            # Check if Templates tab is visible
            print("[CHECK] Looking for Templates tab...")
            templates_tab = page.locator('button:has-text("templates")')
            if templates_tab.count() > 0:
                print(f"[FOUND] Templates tab found: {templates_tab.count()} instances")
                templates_tab.first.click()
                time.sleep(1)
                page.screenshot(path="ui_templates_tab.png")
            
            # Look for New Template or Create Template button
            print("[CHECK] Looking for template creation elements...")
            
            # Check various possible selectors
            selectors_to_check = [
                'button:has-text("New Template")',
                'button:has-text("Create Template")',
                'button:has-text("Add Template")',
                'text="Template Name"',
                'text="Countries"',
                'text="Grounding Modes"',
                'text="Base Model")',
                '.bg-white.rounded-lg.shadow'  # Template creation card
            ]
            
            for selector in selectors_to_check:
                elements = page.locator(selector)
                if elements.count() > 0:
                    print(f"[FOUND] {selector}: {elements.count()} instances")
                    # Get first element's bounding box if visible
                    try:
                        box = elements.first.bounding_box()
                        if box:
                            print(f"  Position: x={box['x']}, y={box['y']}, width={box['width']}, height={box['height']}")
                    except:
                        print(f"  Element not visible or accessible")
            
            # Check if the template creation form is already visible
            print("\n[CHECK] Template creation form visibility...")
            template_name_input = page.locator('input[id="template-name"]')
            if template_name_input.count() > 0:
                is_visible = template_name_input.is_visible()
                print(f"[INFO] Template name input found and visible: {is_visible}")
                if is_visible:
                    print("[SUCCESS] Template creation form IS visible!")
                    
                    # Check all form elements
                    form_elements = {
                        'Template Name': 'input[id="template-name"]',
                        'Model Select': 'select[id="model-name"]',
                        'Prompt Type': 'select[id="prompt-type"]',
                        'Prompt Text': 'textarea[id="prompt-text"]',
                        'Countries Section': 'text="Countries"',
                        'Grounding Section': 'text="Grounding Modes"',
                        'Create Button': 'button:has-text("Create Template")'
                    }
                    
                    print("\n[FORM ELEMENTS STATUS]")
                    for name, selector in form_elements.items():
                        elem = page.locator(selector)
                        if elem.count() > 0:
                            visible = elem.first.is_visible()
                            print(f"  {name}: {'✓ Visible' if visible else '✗ Hidden'}")
                        else:
                            print(f"  {name}: ✗ Not found")
            else:
                print("[WARNING] Template creation form not found or hidden")
                
                # Try to find what might be hiding it
                print("\n[DEBUG] Checking page structure...")
                
                # Get all text content to see what's on the page
                all_text = page.locator('body').inner_text()
                if 'New Template' in all_text:
                    print("[INFO] 'New Template' text found on page")
                if 'Create Template' in all_text:
                    print("[INFO] 'Create Template' text found on page")
                    
            # Take final screenshot
            page.screenshot(path="ui_final_investigation.png")
            print("\n[COMPLETE] Investigation finished. Check screenshots:")
            print("  - ui_initial_state.png")
            print("  - ui_after_brand.png")
            print("  - ui_templates_tab.png")
            print("  - ui_final_investigation.png")
            
        except Exception as e:
            print(f"[ERROR] Investigation failed: {e}")
            page.screenshot(path="ui_error_state.png")
        
        finally:
            print("\n[INFO] Press Enter to close browser...")
            input()
            browser.close()

if __name__ == "__main__":
    investigate_ui()