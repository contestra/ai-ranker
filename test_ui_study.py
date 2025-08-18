"""
Study UI and identify improvements
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
import time

def study_ui():
    print("=" * 60)
    print("UI STUDY & IMPROVEMENT ANALYSIS")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        page = browser.new_page()
        
        try:
            # Navigate
            print("\n1. Opening app...")
            page.goto("http://localhost:3001", timeout=10000)
            time.sleep(2)
            
            # Enter brand
            print("2. Entering AVEA...")
            brand_input = page.locator('input[type="text"]').first
            brand_input.fill("AVEA")
            brand_input.press("Enter")
            time.sleep(2)
            
            # Templates tab
            print("\n3. Studying Templates tab...")
            templates_btn = page.locator('button:text("templates")')
            if templates_btn.count() > 0:
                templates_btn.first.click()
                time.sleep(2)
                
                print("\nTEMPLATES TAB OBSERVATIONS:")
                
                # Check gradient background
                gradient = page.locator('.bg-gradient-to-r')
                print(f"  • Gradient backgrounds: {gradient.count()}")
                
                # Check shadows
                shadows = page.locator('.shadow, .shadow-lg, .shadow-md')
                print(f"  • Shadow elements: {shadows.count()}")
                
                # Check icons
                icons = page.locator('[class*="w-"][class*="h-"]').filter(has_text="")
                print(f"  • Icon elements: {icons.count()}")
                
                # Check buttons
                buttons = page.locator('button')
                print(f"  • Total buttons: {buttons.count()}")
                
                # Check hover states
                hovers = page.locator('[class*="hover:"]')
                print(f"  • Elements with hover: {hovers.count()}")
                
                page.screenshot(path="ui_study_templates.png")
            
            # Results tab
            print("\n4. Studying Results tab...")
            results_btn = page.locator('button:text("results")')
            if results_btn.count() > 0:
                results_btn.first.click()
                time.sleep(2)
                
                print("\nRESULTS TAB OBSERVATIONS:")
                
                # Check cards
                cards = page.locator('.border.rounded-lg')
                print(f"  • Result cards: {cards.count()}")
                
                # Check badges
                badges = page.locator('[class*="bg-"][class*="100"]')
                print(f"  • Badge elements: {badges.count()}")
                
                # Check text colors
                colored_text = page.locator('[class*="text-green"], [class*="text-blue"], [class*="text-indigo"]')
                print(f"  • Colored text elements: {colored_text.count()}")
                
                page.screenshot(path="ui_study_results.png")
            
            print("\n" + "=" * 60)
            print("IMPROVEMENT OPPORTUNITIES")
            print("=" * 60)
            print("\n1. Add loading skeletons while data loads")
            print("2. Add tooltips to icon buttons")
            print("3. Add empty states with illustrations")
            print("4. Add success notifications after actions")
            print("5. Add keyboard shortcuts (Cmd+K for search)")
            print("6. Add dark mode toggle")
            print("7. Add bulk actions for templates")
            print("8. Add export functionality for results")
            
        except Exception as e:
            print(f"\nError: {e}")
            page.screenshot(path="ui_study_error.png")
        
        finally:
            print("\nPress Enter to close...")
            input()
            browser.close()

if __name__ == "__main__":
    study_ui()
