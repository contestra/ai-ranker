"""
Test Playwright with a public website
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')  # Handle UTF-8 on Windows

from playwright.sync_api import sync_playwright

def test_playwright_example():
    """Test Playwright with example.com"""
    print("[TEST] Testing Playwright with example.com...")
    
    try:
        with sync_playwright() as p:
            print("[INFO] Launching browser (headless)...")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print("[INFO] Navigating to example.com...")
            page.goto("https://example.com", wait_until="networkidle")
            
            # Get page title
            title = page.title()
            print(f"[SUCCESS] Page title: {title}")
            
            # Get heading text
            heading = page.locator("h1").text_content()
            print(f"[SUCCESS] Page heading: {heading}")
            
            # Take a screenshot
            page.screenshot(path="example_screenshot.png")
            print("[SUCCESS] Screenshot saved as example_screenshot.png")
            
            browser.close()
            print("\n[RESULT] Playwright is working correctly!")
            print("[INFO] Browser automation is available for testing")
            return True
            
    except Exception as e:
        print(f"[ERROR] Playwright test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_playwright_example()
    sys.exit(0 if success else 1)