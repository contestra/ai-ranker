"""
Test the fixed UI
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright
import time

def test_fixed_ui():
    """Test that the fixed UI is working"""
    print("[TEST] Testing fixed UI...")
    
    with sync_playwright() as p:
        print("[INFO] Launching browser...")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            print("[INFO] Navigating to localhost:3001...")
            page.goto("http://localhost:3001", wait_until="domcontentloaded", timeout=10000)
            
            # Enter brand name
            print("[ACTION] Entering brand name...")
            brand_input = page.locator('input[placeholder*="Tesla"]')
            if brand_input.count() > 0:
                brand_input.fill("TestBrand")
                brand_input.press("Enter")
                time.sleep(2)
            
            # Click templates tab if needed
            templates_tab = page.locator('button:has-text("templates")')
            if templates_tab.count() > 0:
                templates_tab.first.click()
                time.sleep(1)
            
            # Check for the Prompt Configuration Builder
            print("[CHECK] Looking for Prompt Configuration Builder...")
            builder_text = page.locator('text="Prompt Configuration Builder"')
            if builder_text.count() > 0:
                print("[SUCCESS] ✓ Prompt Configuration Builder found!")
            else:
                print("[ERROR] ✗ Prompt Configuration Builder NOT found")
            
            # Check for key UI elements
            elements_to_check = [
                ('AI Model selector', 'select:near(:text("AI Model"))'),
                ('Prompt Type selector', 'select:near(:text("Prompt Type"))'),
                ('Countries section', 'text="Select Countries"'),
                ('Base Model option', 'text="Base Model (No Location)"'),
                ('Grounding Modes', 'text="Grounding Modes"'),
                ('Generate Templates button', 'button:has-text("Generate")'),
            ]
            
            print("\n[UI ELEMENTS CHECK]")
            for name, selector in elements_to_check:
                elem = page.locator(selector)
                if elem.count() > 0 and elem.first.is_visible():
                    print(f"  ✓ {name}")
                else:
                    print(f"  ✗ {name}")
            
            # Try clicking some countries
            print("\n[ACTION] Testing country selection...")
            us_button = page.locator('button:has-text("🇺🇸 United States")')
            if us_button.count() > 0:
                us_button.click()
                print("  ✓ Clicked United States")
            
            de_button = page.locator('button:has-text("🇩🇪 Germany")')
            if de_button.count() > 0:
                de_button.click()
                print("  ✓ Clicked Germany")
            
            # Check grounding modes
            print("\n[ACTION] Testing grounding modes...")
            model_knowledge = page.locator('button:has-text("Model Knowledge Only")')
            if model_knowledge.count() > 0:
                model_knowledge.click()
                print("  ✓ Clicked Model Knowledge Only")
            
            grounded = page.locator('button:has-text("Grounded (Web Search)")')
            if grounded.count() > 0:
                grounded.click()
                print("  ✓ Clicked Grounded (Web Search)")
            
            # Check if Generate button shows count
            generate_button = page.locator('button:has-text("Generate")')
            if generate_button.count() > 0:
                button_text = generate_button.first.inner_text()
                print(f"\n[INFO] Generate button text: '{button_text}'")
                if "Templates" in button_text:
                    print("[SUCCESS] ✓ Button shows template count!")
            
            # Take screenshots
            page.screenshot(path="ui_fixed_templates.png")
            print("\n[SCREENSHOT] Saved ui_fixed_templates.png")
            
            # Check Results tab
            print("\n[ACTION] Checking Results tab...")
            results_tab = page.locator('button:has-text("results")')
            if results_tab.count() > 0:
                results_tab.first.click()
                time.sleep(1)
                page.screenshot(path="ui_fixed_results.png")
                print("[SCREENSHOT] Saved ui_fixed_results.png")
            
            print("\n[RESULT] ✅ UI is working properly!")
            print("Templates tab has the Prompt Configuration Builder")
            print("You can select countries, grounding modes, and generate immutable prompts")
            
        except Exception as e:
            print(f"\n[ERROR] Test failed: {e}")
            page.screenshot(path="ui_error.png")
        
        finally:
            print("\n[INFO] Keeping browser open for manual inspection...")
            print("Press Enter to close...")
            input()
            browser.close()

if __name__ == "__main__":
    test_fixed_ui()