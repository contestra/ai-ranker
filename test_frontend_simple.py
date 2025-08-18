"""
Simple frontend test to check UI elements and navigation
"""
import asyncio
from playwright.async_api import async_playwright
import sys

# Set encoding for Windows
sys.stdout.reconfigure(encoding='utf-8')

async def test_frontend():
    """Test frontend UI navigation and elements"""
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("=" * 60)
        print("FRONTEND UI TEST")
        print("=" * 60)
        
        # Navigate to the app
        print("\n1. Opening http://localhost:3001...")
        await page.goto("http://localhost:3001", wait_until="networkidle")
        
        # Take screenshot of main page
        await page.screenshot(path="main_page.png")
        print("   Screenshot saved: main_page.png")
        
        # Wait and look for navigation elements
        print("\n2. Looking for UI elements...")
        await asyncio.sleep(2)
        
        # Try to find tabs or navigation
        tabs = await page.locator('[role="tab"], button').all()
        print(f"   Found {len(tabs)} clickable elements")
        
        for i, tab in enumerate(tabs[:10]):  # Check first 10 elements
            text = await tab.text_content()
            if text:
                print(f"   - Element {i}: {text.strip()}")
        
        # Look specifically for Prompt Tracking
        print("\n3. Looking for Prompt Tracking section...")
        
        # Try different selectors
        selectors = [
            'text="Prompt Tracking"',
            'text=/prompt.*tracking/i',
            'button:has-text("Prompt")',
            '[href*="prompt"]',
            'nav >> text="Prompt"'
        ]
        
        found = False
        for selector in selectors:
            element = page.locator(selector).first
            if await element.is_visible():
                print(f"   Found element with selector: {selector}")
                await element.click()
                found = True
                break
        
        if not found:
            print("   Could not find Prompt Tracking - checking page structure...")
            # Get all text on page to understand structure
            all_text = await page.text_content('body')
            if 'prompt' in all_text.lower():
                print("   'prompt' text found on page")
            if 'template' in all_text.lower():
                print("   'template' text found on page")
            if 'results' in all_text.lower():
                print("   'results' text found on page")
        
        # Take final screenshot
        await asyncio.sleep(1)
        await page.screenshot(path="final_state.png")
        print("\n4. Final screenshot saved: final_state.png")
        
        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("Check screenshots to see UI state")
        print("=" * 60)
        
        # Keep browser open for manual inspection
        print("\nBrowser will stay open for 10 seconds for inspection...")
        await asyncio.sleep(10)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_frontend())