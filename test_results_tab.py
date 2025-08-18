"""
Test Results tab View Response functionality
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
import time

def test_results_tab():
    print("=" * 60)
    print("RESULTS TAB TEST - VIEW RESPONSE FUNCTIONALITY")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        page = browser.new_page()
        
        # Monitor console
        console_errors = []
        page.on("console", lambda msg: console_errors.append(f"{msg.type}: {msg.text}") if msg.type == "error" else None)
        
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
            
            # Go to Results tab
            print("3. Going to Results tab...")
            results_btn = page.locator('button:text("results")')
            results_btn.first.click()
            time.sleep(2)
            
            # Check run cards
            run_cards = page.locator('.border.rounded-lg')
            print(f"   Found {run_cards.count()} run cards")
            
            if run_cards.count() > 0:
                # Find a completed run
                print("\n4. Looking for completed runs...")
                completed_runs = page.locator('.text-green-500').filter(has_text="completed")
                
                if completed_runs.count() == 0:
                    # Find any run with View Response button
                    view_btns = page.locator('button:has-text("View Response")')
                    print(f"   Found {view_btns.count()} View Response buttons")
                else:
                    print(f"   Found {completed_runs.count()} completed runs")
                
                # Click first View Response
                print("\n5. Clicking View Response...")
                view_btn = page.locator('button:has-text("View Response")').first
                if view_btn.count() > 0:
                    view_btn.click()
                    time.sleep(2)
                    
                    # Check what appears
                    print("\n6. Checking expanded content...")
                    
                    # Check for error
                    error_msg = page.locator('.bg-red-50').filter(has_text="Error")
                    if error_msg.count() > 0:
                        print("   ✗ ERROR displayed:", error_msg.first.inner_text())
                    
                    # Check for prompt
                    prompt_section = page.locator('span:has-text("Prompt:")')
                    if prompt_section.count() > 0:
                        print("   ✓ Prompt section found")
                        prompt_text = page.locator('.bg-gray-50').first
                        if prompt_text.count() > 0:
                            text = prompt_text.inner_text()[:100]
                            print(f"   Prompt: {text}...")
                    
                    # Check for response
                    response_section = page.locator('span:has-text("Response:")')
                    if response_section.count() > 0:
                        print("   ✓ Response section found")
                        response_text = page.locator('pre.bg-gray-50')
                        if response_text.count() > 0:
                            text = response_text.first.inner_text()[:200]
                            print(f"   Response: {text}...")
                    
                    # Check for metadata
                    brand_mention = page.locator('span:has-text("Brand mentioned:")')
                    if brand_mention.count() > 0:
                        print("   ✓ Brand mention metadata found")
                    
                    mentions = page.locator('span:has-text("Mentions:")')
                    if mentions.count() > 0:
                        print("   ✓ Mention count found")
                    
                    confidence = page.locator('span:has-text("Confidence:")')
                    if confidence.count() > 0:
                        print("   ✓ Confidence score found")
                    
                    # Check for SHA-256
                    sha = page.locator('.font-mono:has-text("SHA-256:")')
                    if sha.count() > 0:
                        print("   ✓ SHA-256 hash displayed")
                    
                    page.screenshot(path="results_expanded.png")
                    
                    # Click again to collapse
                    print("\n7. Testing collapse...")
                    hide_btn = page.locator('button:has-text("Hide Response")').first
                    if hide_btn.count() > 0:
                        hide_btn.click()
                        time.sleep(1)
                        print("   ✓ Response collapsed")
                    
                else:
                    print("   ✗ No View Response buttons found")
            
            # Check console errors
            print("\n8. Checking console errors...")
            if console_errors:
                print(f"   ✗ Found {len(console_errors)} errors:")
                for err in console_errors[:3]:
                    print(f"     - {err}")
            else:
                print("   ✓ No console errors")
            
            print("\n" + "=" * 60)
            print("RESULTS TAB SUMMARY")
            print("=" * 60)
            print("\nFunctionality tested:")
            print("  • View Response button click")
            print("  • Expanded content display")
            print("  • Metadata visibility")
            print("  • Collapse functionality")
            print("\nScreenshot saved: results_expanded.png")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            page.screenshot(path="results_error.png")
        
        finally:
            print("\nTest complete! Browser will close in 5 seconds...")
            time.sleep(5)
            browser.close()

if __name__ == "__main__":
    test_results_tab()
