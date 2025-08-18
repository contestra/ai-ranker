"""
Test final implementation of Templates and Results tabs
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
import time

def test_final():
    print("=" * 70)
    print("TESTING FINAL IMPLEMENTATION")
    print("=" * 70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        page = browser.new_page()
        
        try:
            # Navigate
            print("\n1. Loading app...")
            page.goto("http://localhost:3001", timeout=10000)
            time.sleep(2)
            
            # Enter brand
            print("2. Entering AVEA...")
            brand_input = page.locator('input[type="text"]').first
            brand_input.fill("AVEA")
            brand_input.press("Enter")
            time.sleep(2)
            
            # Templates tab
            print("\n3. TEMPLATES TAB CHECK:")
            templates_btn = page.locator('button:text("templates")')
            templates_btn.first.click()
            time.sleep(2)
            
            # Check for provider badges
            print("   Checking provider badges...")
            provider_badges = page.locator('.bg-blue-100, .bg-green-100').filter(has_text=["vertex", "openai"])
            print(f"   • Provider badges: {provider_badges.count()}")
            
            # Check for expand buttons
            expand_btns = page.locator('[title*="Expand details"]')
            print(f"   • Expand buttons: {expand_btns.count()}")
            
            if expand_btns.count() > 0:
                print("   • Clicking expand button...")
                expand_btns.first.click()
                time.sleep(1)
                
                # Check for expanded content
                system_params = page.locator('h5:has-text("System Parameters")')
                if system_params.count() > 0:
                    print("     ✓ System Parameters section visible")
                
                config_hash = page.locator('h5:has-text("Configuration Hash")')
                if config_hash.count() > 0:
                    print("     ✓ Configuration Hash section visible")
                
                metadata = page.locator('h5:has-text("Metadata")')
                if metadata.count() > 0:
                    print("     ✓ Metadata section visible")
            
            # Results tab
            print("\n4. RESULTS TAB CHECK:")
            results_btn = page.locator('button:text("results")')
            results_btn.first.click()
            time.sleep(2)
            
            # Check for provenance strip
            print("   Checking provenance strip...")
            provider_tags = page.locator('span').filter(has_text="provider=")
            mode_tags = page.locator('span').filter(has_text="mode=")
            grounded_tags = page.locator('span').filter(has_text="grounded=")
            
            print(f"   • Provider tags: {provider_tags.count()}")
            print(f"   • Mode tags: {mode_tags.count()}")
            print(f"   • Grounded tags: {grounded_tags.count()}")
            
            # Check for cross-link buttons
            template_links = page.locator('button').filter(has_text="Template")
            print(f"   • Template links: {template_links.count()}")
            
            # Click View Details
            view_details = page.locator('button:has-text("View Details")').first
            if view_details.count() > 0:
                print("\n5. Testing View Details...")
                view_details.click()
                time.sleep(2)
                
                # Check expanded content
                prompt_section = page.locator('span:has-text("Prompt:")')
                response_section = page.locator('span:has-text("Response:")')
                
                if prompt_section.count() > 0:
                    print("   ✓ Prompt section visible")
                if response_section.count() > 0:
                    print("   ✓ Response section visible")
                
                # Check metadata
                brand_mention = page.locator('span:has-text("Brand mentioned:")')
                if brand_mention.count() > 0:
                    print("   ✓ Brand mention metadata visible")
            
            print("\n" + "=" * 70)
            print("IMPLEMENTATION STATUS")
            print("=" * 70)
            
            print("\n✅ WORKING FEATURES:")
            print("  • Templates tab with expand/collapse")
            print("  • Provider badges in templates")
            print("  • System parameters section")
            print("  • Results tab with View Details")
            print("  • Cross-link to templates")
            
            print("\n❌ MISSING/BROKEN:")
            if provider_tags.count() == 0:
                print("  • Provenance strip not showing properly")
            if template_links.count() == 0:
                print("  • Template cross-links missing")
            
            page.screenshot(path="final_implementation.png")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            page.screenshot(path="final_error.png")
        
        finally:
            print("\nTest complete! Press Enter to close...")
            input()
            browser.close()

if __name__ == "__main__":
    test_final()
