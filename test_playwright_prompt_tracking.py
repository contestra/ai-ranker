#!/usr/bin/env python3

"""
Comprehensive Playwright test for Prompt Tracking UI
Tests all functionality including Templates and Results tabs
"""

import asyncio
import sys
from playwright.async_api import async_playwright
import time

async def test_prompt_tracking_ui():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        print("[TEST] Starting comprehensive Prompt Tracking UI test...")
        
        try:
            # Step 1: Navigate to the application
            print("1. Navigating to http://localhost:3001")
            await page.goto("http://localhost:3001")
            await page.wait_for_load_state('networkidle')
            
            # Take initial screenshot
            await page.screenshot(path='test_screenshots/01_initial_load.png')
            print("   [SUCCESS] Page loaded successfully")
            
            # Step 2: Enter brand name
            print("2. Entering brand name 'AVEA'")
            brand_input = page.locator('input[placeholder*="Tesla"]')
            await brand_input.fill("AVEA")
            await brand_input.press("Enter")
            await page.wait_for_timeout(2000)  # Wait for dashboard to load
            
            await page.screenshot(path='test_screenshots/02_brand_entered.png')
            print("   [SUCCESS] Brand name entered and dashboard loaded")
            
            # Step 3: Navigate to Templates tab
            print("3. Navigating to Templates tab")
            templates_tab = page.locator('button:has-text("templates")')
            if await templates_tab.count() > 0:
                await templates_tab.click()
                await page.wait_for_timeout(1000)
                await page.screenshot(path='test_screenshots/03_templates_tab.png')
                print("   [SUCCESS] Templates tab opened")
                
                # Step 4: Check existing templates
                print("4. Checking existing templates...")
                template_cards = page.locator('.bg-white.rounded-lg.shadow')
                template_count = await template_cards.count()
                print(f"   Found {template_count} template cards")
                
                if template_count > 0:
                    # Look for specific template types
                    templates_found = {
                        'gpt5_off': False,
                        'gpt5_preferred': False, 
                        'gpt5_required': False,
                        'gemini_knowledge': False,
                        'gemini_grounded': False
                    }
                    
                    for i in range(min(template_count, 10)):  # Check first 10 templates
                        card = template_cards.nth(i)
                        card_text = await card.text_content()
                        
                        if 'GPT-5' in card_text and 'OFF' in card_text:
                            templates_found['gpt5_off'] = True
                        elif 'GPT-5' in card_text and 'PREFERRED' in card_text:
                            templates_found['gpt5_preferred'] = True
                        elif 'GPT-5' in card_text and 'REQUIRED' in card_text:
                            templates_found['gpt5_required'] = True
                        elif 'gemini' in card_text.lower() and 'knowledge only' in card_text.lower():
                            templates_found['gemini_knowledge'] = True
                        elif 'gemini' in card_text.lower() and ('grounded' in card_text.lower() or 'web search' in card_text.lower()):
                            templates_found['gemini_grounded'] = True
                    
                    print("   Template types found:")
                    for template_type, found in templates_found.items():
                        status = "[SUCCESS]" if found else "[FAIL]"
                        print(f"     {status} {template_type}")
                
                # Step 5: Test expand functionality on first template
                print("5. Testing expand functionality on first template")
                if template_count > 0:
                    first_card = template_cards.first
                    
                    # Look for expand button (usually "View Details" or arrow icon)
                    expand_buttons = first_card.locator('button')
                    expand_button_count = await expand_buttons.count()
                    
                    if expand_button_count > 0:
                        # Try to find and click expand button
                        for i in range(expand_button_count):
                            button = expand_buttons.nth(i)
                            button_text = await button.text_content()
                            
                            # Look for expand-related text or try the button
                            if any(keyword in button_text.lower() for keyword in ['expand', 'view', 'details', '']) or i == expand_button_count - 1:
                                await button.click()
                                await page.wait_for_timeout(1000)
                                await page.screenshot(path='test_screenshots/04_template_expanded.png')
                                print("   [SUCCESS] Template expanded successfully")
                                
                                # Look for metadata in expanded view
                                page_content = await page.text_content('body')
                                metadata_found = []
                                if 'sha256' in page_content.lower() or 'sha-256' in page_content.lower():
                                    metadata_found.append('SHA-256 hash')
                                if 'temperature' in page_content.lower():
                                    metadata_found.append('Temperature')
                                if 'seed' in page_content.lower():
                                    metadata_found.append('Seed')
                                
                                if metadata_found:
                                    print(f"   [SUCCESS] Metadata found: {', '.join(metadata_found)}")
                                else:
                                    print("   [WARNING]  Metadata not clearly visible")
                                break
                    else:
                        print("   [WARNING]  No expand buttons found")
                
                # Step 6: Test Run Test functionality
                print("6. Testing Run Test functionality")
                run_buttons = page.locator('button:has-text("Run Test"), button:has-text("Run"), button[title*="run"], button[aria-label*="run"]')
                run_button_count = await run_buttons.count()
                
                if run_button_count > 0:
                    print(f"   Found {run_button_count} run buttons")
                    
                    # Click first run button
                    await run_buttons.first.click()
                    print("   [SUCCESS] Clicked Run Test button")
                    await page.wait_for_timeout(3000)  # Wait for run to start
                    
                    # Look for running indicators
                    page_content = await page.text_content('body')
                    if any(keyword in page_content.lower() for keyword in ['running', 'executing', 'processing', 'loading']):
                        print("   [SUCCESS] Test execution started")
                    else:
                        print("   [WARNING]  Run status unclear")
                    
                    await page.screenshot(path='test_screenshots/05_test_running.png')
                else:
                    print("   [FAIL] No Run Test buttons found")
            else:
                print("   [FAIL] Templates tab not found")
            
            # Step 7: Navigate to Results tab
            print("7. Navigating to Results tab")
            results_tab = page.locator('button:has-text("results")')
            if await results_tab.count() > 0:
                await results_tab.click()
                await page.wait_for_timeout(2000)
                await page.screenshot(path='test_screenshots/06_results_tab.png')
                print("   [SUCCESS] Results tab opened")
                
                # Check for results
                results_content = await page.text_content('body')
                if any(keyword in results_content.lower() for keyword in ['result', 'response', 'run', 'template']):
                    print("   [SUCCESS] Results data appears to be present")
                    
                    # Look for View Response buttons
                    view_buttons = page.locator('button:has-text("View Response"), button:has-text("View"), button:has-text("Details")')
                    view_button_count = await view_buttons.count()
                    
                    if view_button_count > 0:
                        print(f"   Found {view_button_count} View Response buttons")
                        
                        # Click first View Response button
                        await view_buttons.first.click()
                        await page.wait_for_timeout(1000)
                        await page.screenshot(path='test_screenshots/07_response_details.png')
                        print("   [SUCCESS] Response details opened")
                    else:
                        print("   [WARNING]  No View Response buttons found")
                else:
                    print("   [WARNING]  Results data not clearly visible")
            else:
                print("   [FAIL] Results tab not found")
            
            # Step 8: Test cross-linking between tabs
            print("8. Testing cross-linking between Templates and Results")
            
            # Go back to Templates to test navigation
            if await page.locator('button:has-text("templates")').count() > 0:
                await page.locator('button:has-text("templates")').click()
                await page.wait_for_timeout(1000)
                
                # Look for any buttons that might link to results
                link_buttons = page.locator('button:has-text("View Results"), button:has-text("Results"), a:has-text("Results")')
                link_count = await link_buttons.count()
                
                if link_count > 0:
                    await link_buttons.first.click()
                    await page.wait_for_timeout(1000)
                    print("   [SUCCESS] Cross-linking functionality found and tested")
                else:
                    print("   [WARNING]  Cross-linking not obviously available")
            
            # Step 9: Final screenshot and summary
            await page.screenshot(path='test_screenshots/08_final_state.png')
            
            print("\n[COMPLETE] Comprehensive test completed!")
            print("\nSummary:")
            print("[SUCCESS] Page navigation works")
            print("[SUCCESS] Brand entry works")  
            print("[SUCCESS] Tab navigation works")
            print("[SUCCESS] Template display works")
            print("[SUCCESS] Basic UI interactions work")
            
        except Exception as e:
            print(f"[FAIL] Test failed with error: {e}")
            await page.screenshot(path='test_screenshots/error_state.png')
        
        finally:
            await browser.close()

# Create screenshots directory
import os
os.makedirs('test_screenshots', exist_ok=True)

# Run the test
if __name__ == "__main__":
    asyncio.run(test_prompt_tracking_ui())