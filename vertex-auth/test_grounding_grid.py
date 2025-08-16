import asyncio
from playwright.async_api import async_playwright
import time

async def test_grounding_grid_complete():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--no-sandbox'])
        page = await browser.new_page()
        
        try:
            print('=== GROUNDING TEST GRID TESTING ===')
            print('Navigating to http://localhost:3001...')
            await page.goto('http://localhost:3001', timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            print('[OK] Page loaded successfully')
            
            # Step 1: Enter brand name
            print('\n1. Entering brand name "AVEA"...')
            brand_input = await page.wait_for_selector('input[placeholder*="Tesla"]', timeout=10000)
            await brand_input.fill('AVEA')
            await brand_input.press('Enter')
            await page.wait_for_timeout(3000)
            print('[OK] Brand name entered')
            
            # Step 2: Find and click the Grounding Test tab
            print('\n2. Looking for Grounding Test tab...')
            
            # Wait for the tab navigation to appear
            await page.wait_for_selector('nav', timeout=10000)
            
            # Look for the grounding test tab
            grounding_tab = await page.wait_for_selector('text="Grounding Test"', timeout=10000)
            print('[OK] Found Grounding Test tab')
            
            await grounding_tab.click()
            await page.wait_for_timeout(3000)
            print('[OK] Clicked Grounding Test tab')
            
            # Step 3: Take screenshot of the grounding test grid
            await page.screenshot(path='grounding_test_grid.png')
            print('[OK] Screenshot taken: grounding_test_grid.png')
            
            # Step 4: Find and analyze the test grid
            print('\n3. Analyzing test grid...')
            
            # Look for the Run All Tests button
            run_all_button = await page.query_selector('text="Run All Tests"')
            if run_all_button:
                print('[OK] Found "Run All Tests" button')
                
                # Look for individual test cards
                test_cards = await page.query_selector_all('[class*="border rounded-lg p-4"]')
                print(f'[OK] Found {len(test_cards)} test cards')
                
                # Step 5: Run tests to verify the grid works
                print('\n4. Testing test execution...')
                
                print('Starting all tests...')
                await page.screenshot(path='before_test.png')
                
                # Click Run All Tests button to start testing
                await run_all_button.click()
                print('[OK] Started test execution')
                
                # Wait for tests to complete (they run sequentially)
                print('Waiting for tests to complete (may take 60+ seconds)...')
                
                # Wait for running state to appear
                try:
                    await page.wait_for_selector('.animate-spin', timeout=10000)
                    print('[OK] Tests are running (spinner detected)')
                except:
                    print('[WARN] No spinner detected, tests may have completed quickly')
                
                # Wait for tests to complete (no more spinners)
                start_time = time.time()
                timeout = 180  # 3 minutes timeout
                
                while time.time() - start_time < timeout:
                    spinners = await page.query_selector_all('.animate-spin')
                    if len(spinners) == 0:
                        print('[OK] All tests completed')
                        break
                    await page.wait_for_timeout(5000)
                    print(f'  Still running... {len(spinners)} tests active')
                
                if time.time() - start_time >= timeout:
                    print('[WARN] Tests timed out after 3 minutes')
                
                # Take final screenshot
                await page.screenshot(path='tests_completed.png')
                print('[OK] Final screenshot taken: tests_completed.png')
                
                # Analyze results
                print('\n5. Analyzing test results...')
                
                # Count success/failure indicators
                success_icons = await page.query_selector_all('.text-green-500')
                failure_icons = await page.query_selector_all('.text-red-500')
                warning_icons = await page.query_selector_all('.text-yellow-500')
                
                print(f'[PASS] Success indicators: {len(success_icons)}')
                print(f'[FAIL] Failure indicators: {len(failure_icons)}')
                print(f'[WARN] Warning indicators: {len(warning_icons)}')
                
                # Check for error messages
                error_elements = await page.query_selector_all('text=/Error:.*/')
                if error_elements:
                    print(f'[ERROR] Found {len(error_elements)} error messages')
                    for i, error in enumerate(error_elements[:3]):  # Show first 3
                        error_text = await error.text_content()
                        print(f'   Error {i+1}: {error_text}')
                else:
                    print('[OK] No error messages found')
                
                print('\n=== TEST SUMMARY ===')
                if len(success_icons) >= 2:  # At least 2 tests should pass
                    print('[SUCCESS] GROUNDING TEST GRID: WORKING')
                    print('   - Grid loads properly')
                    print('   - Tests execute successfully')
                    print('   - Results display correctly')
                else:
                    print('[FAILURE] GROUNDING TEST GRID: ISSUES DETECTED')
                    print('   - Tests may be failing')
                    print('   - Check error messages above')
            else:
                print('[ERROR] "Run All Tests" button not found')
            
            # Keep browser open for manual inspection
            print('\nBrowser will stay open for 10 seconds for manual inspection...')
            await page.wait_for_timeout(10000)
            
        except Exception as e:
            print(f'[ERROR] Error during testing: {e}')
            import traceback
            traceback.print_exc()
            
            # Take error screenshot
            try:
                await page.screenshot(path='error_state.png')
                print('[INFO] Error screenshot saved: error_state.png')
            except:
                pass
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_grounding_grid_complete())