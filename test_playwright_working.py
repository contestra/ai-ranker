"""
Test Playwright browser automation capabilities
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')  # Handle UTF-8 on Windows

from playwright.sync_api import sync_playwright
import time

def test_playwright_basic():
    """Test basic Playwright functionality"""
    print("[TEST] Starting Playwright test...")
    
    try:
        with sync_playwright() as p:
            print("[INFO] Launching browser...")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print("[INFO] Navigating to localhost:3001...")
            page.goto("http://localhost:3001", wait_until="networkidle", timeout=10000)
            
            # Get page title
            title = page.title()
            print(f"[SUCCESS] Page title: {title}")
            
            # Check if the app is running
            if "AI Rank" in title or "React App" in title or title:
                print("[SUCCESS] Frontend app is accessible!")
            
            # Take a screenshot
            page.screenshot(path="playwright_test_screenshot.png")
            print("[SUCCESS] Screenshot saved as playwright_test_screenshot.png")
            
            browser.close()
            print("[SUCCESS] Playwright is working correctly!")
            return True
            
    except Exception as e:
        print(f"[ERROR] Playwright test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_playwright_basic()
    sys.exit(0 if success else 1)