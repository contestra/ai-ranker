"""
Comprehensive test of all Prompt Tracking functionality
Tests all models, grounding modes, and UI features
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
import time
import json

def test_comprehensive():
    print("=" * 80)
    print("COMPREHENSIVE PROMPT TRACKING TEST")
    print("Testing all models, grounding modes, and UI functionality")
    print("=" * 80)
    
    tests_passed = []
    tests_failed = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        page = browser.new_page()
        
        # Monitor network for API calls
        api_calls = []
        def log_api(route):
            if '/api/' in route.request.url:
                api_calls.append({
                    'method': route.request.method,
                    'url': route.request.url,
                    'status': None
                })
            route.continue_()
        
        page.route('**/*', log_api)
        
        # Monitor console
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
        
        try:
            # ========== SETUP ==========
            print("\n1. SETUP")
            print("-" * 40)
            page.goto("http://localhost:3001", timeout=15000)
            time.sleep(2)
            
            # Enter brand
            brand_input = page.locator('input[type="text"]').first
            brand_input.fill("AVEA")
            brand_input.press("Enter")
            time.sleep(2)
            print("✓ Entered brand: AVEA")
            
            # Go to Templates tab
            templates_btn = page.locator('button').filter(has_text="Templates").first
            templates_btn.click()
            time.sleep(2)
            print("✓ Navigated to Templates tab")
            
            # ========== TEST GPT-5 MODES ==========
            print("\n2. TESTING GPT-5 MODES")
            print("-" * 40)
            
            # Test OFF mode
            print("\n   Testing GPT-5 with OFF mode...")
            model_select = page.locator('select').first
            model_select.select_option("gpt-5")
            
            # Select US
            us_btn = page.locator('button span:has-text("United States")').locator('..')
            us_btn.first.click()
            
            # Select OFF
            off_btn = page.locator('button:has-text("OFF")')
            off_btn.first.click()
            
            # Generate
            generate_btn = page.locator('button:has-text("Generate Templates")')
            generate_btn.first.click()
            time.sleep(2)
            
            # Check if template created
            template_cards = page.locator('.bg-white.rounded-lg.shadow')
            initial_count = template_cards.count()
            if initial_count > 0:
                print("   ✓ GPT-5 OFF template created")
                tests_passed.append("GPT-5 OFF template creation")
            else:
                print("   ✗ Failed to create GPT-5 OFF template")
                tests_failed.append("GPT-5 OFF template creation")
            
            # Test PREFERRED mode
            print("\n   Testing GPT-5 with PREFERRED mode...")
            preferred_btn = page.locator('button:has-text("PREFERRED")')
            preferred_btn.first.click()
            generate_btn.first.click()
            time.sleep(2)
            
            new_count = page.locator('.bg-white.rounded-lg.shadow').count()
            if new_count > initial_count:
                print("   ✓ GPT-5 PREFERRED template created")
                tests_passed.append("GPT-5 PREFERRED template creation")
            else:
                print("   ✗ Failed to create GPT-5 PREFERRED template")
                tests_failed.append("GPT-5 PREFERRED template creation")
            
            # Test REQUIRED mode
            print("\n   Testing GPT-5 with REQUIRED mode...")
            required_btn = page.locator('button:has-text("REQUIRED")')
            required_btn.first.click()
            generate_btn.first.click()
            time.sleep(2)
            
            new_count2 = page.locator('.bg-white.rounded-lg.shadow').count()
            if new_count2 > new_count:
                print("   ✓ GPT-5 REQUIRED template created")
                tests_passed.append("GPT-5 REQUIRED template creation")
            else:
                print("   ✗ Failed to create GPT-5 REQUIRED template")
                tests_failed.append("GPT-5 REQUIRED template creation")
            
            # ========== TEST GEMINI MODES ==========
            print("\n3. TESTING GEMINI MODES")
            print("-" * 40)
            
            # Switch to Gemini
            print("\n   Testing Gemini 2.5 Pro...")
            model_select.select_option("gemini-2.5-pro")
            time.sleep(1)
            
            # Test Model Knowledge Only
            print("   Testing Model Knowledge Only mode...")
            knowledge_btn = page.locator('button:has-text("Model Knowledge Only")')
            knowledge_btn.first.click()
            generate_btn.first.click()
            time.sleep(2)
            
            gemini_count = page.locator('.bg-white.rounded-lg.shadow').count()
            if gemini_count > new_count2:
                print("   ✓ Gemini Model Knowledge template created")
                tests_passed.append("Gemini Model Knowledge template creation")
            else:
                print("   ✗ Failed to create Gemini Model Knowledge template")
                tests_failed.append("Gemini Model Knowledge template creation")
            
            # Test Grounded mode
            print("\n   Testing Grounded (Web Search) mode...")
            grounded_btn = page.locator('button:has-text("Grounded (Web Search)")')
            grounded_btn.first.click()
            generate_btn.first.click()
            time.sleep(2)
            
            final_template_count = page.locator('.bg-white.rounded-lg.shadow').count()
            if final_template_count > gemini_count:
                print("   ✓ Gemini Grounded template created")
                tests_passed.append("Gemini Grounded template creation")
            else:
                print("   ✗ Failed to create Gemini Grounded template")
                tests_failed.append("Gemini Grounded template creation")
            
            # ========== TEST TEMPLATE FEATURES ==========
            print("\n4. TESTING TEMPLATE FEATURES")
            print("-" * 40)
            
            # Test expand functionality
            print("\n   Testing template expansion...")
            expand_btn = page.locator('[title*="Expand"]').first
            if expand_btn.count() > 0:
                expand_btn.click()
                time.sleep(1)
                
                # Check for System Parameters
                sys_params = page.locator('h5:has-text("System Parameters")')
                if sys_params.count() > 0:
                    print("   ✓ System Parameters visible on expand")
                    tests_passed.append("Template expand functionality")
                    
                    # Check for SHA-256
                    sha = page.locator('text=/SHA-256:/')
                    if sha.count() > 0:
                        print("   ✓ SHA-256 hash displayed")
                        tests_passed.append("SHA-256 display")
                    
                    # Check for temperature/seed
                    temp = page.locator('text=/Temperature:/')
                    seed = page.locator('text=/Seed:/')
                    if temp.count() > 0 and seed.count() > 0:
                        print("   ✓ Temperature and Seed displayed")
                        tests_passed.append("System parameters display")
                else:
                    print("   ✗ System Parameters not visible")
                    tests_failed.append("Template expand functionality")
                
                # Collapse
                expand_btn.click()
            
            # Test running a template
            print("\n   Testing template execution...")
            run_btn = page.locator('button:has-text("Run Test")').first
            if run_btn.count() > 0:
                run_btn.click()
                print("   • Running template...")
                time.sleep(5)  # Wait for API call
                tests_passed.append("Template run trigger")
            
            # ========== TEST RESULTS TAB ==========
            print("\n5. TESTING RESULTS TAB")
            print("-" * 40)
            
            # Navigate to Results
            results_btn = page.locator('button').filter(has_text="Results").first
            results_btn.click()
            time.sleep(3)
            print("✓ Navigated to Results tab")
            
            # Check for run cards
            run_cards = page.locator('.border.rounded-lg').filter(has=page.locator('span:has-text("Status:")'))
            run_count = run_cards.count()
            print(f"   Found {run_count} run cards")
            
            if run_count > 0:
                tests_passed.append("Results display")
                
                # Check status distribution
                completed = page.locator('.text-green-500:has-text("completed")')
                running = page.locator('.text-yellow-500:has-text("running")')
                failed = page.locator('.text-red-500:has-text("failed")')
                
                print(f"   Status: {completed.count()} completed, {running.count()} running, {failed.count()} failed")
                
                # Test View Response
                view_btn = page.locator('button:has-text("View Response")').first
                if view_btn.count() > 0:
                    print("\n   Testing View Response...")
                    view_btn.click()
                    time.sleep(2)
                    
                    # Check for metadata
                    metadata_checks = [
                        ('text=/Brand mentioned:/', "Brand mention metadata"),
                        ('text=/Confidence:/', "Confidence score"),
                        ('text=/SHA-256:/', "SHA-256 in results"),
                        ('text=/Model:/', "Model info"),
                        ('text=/Grounding Mode:/', "Grounding mode info")
                    ]
                    
                    for selector, name in metadata_checks:
                        element = page.locator(selector)
                        if element.count() > 0:
                            print(f"   ✓ {name} displayed")
                            tests_passed.append(name)
                        else:
                            print(f"   ✗ {name} missing")
                            tests_failed.append(name)
                    
                    # Hide response
                    hide_btn = page.locator('button:has-text("Hide Response")')
                    if hide_btn.count() > 0:
                        hide_btn.click()
                        time.sleep(1)
            else:
                print("   ✗ No results found")
                tests_failed.append("Results display")
            
            # ========== CHECK API CALLS ==========
            print("\n6. API CALL VERIFICATION")
            print("-" * 40)
            
            # Filter for important API calls
            important_apis = [call for call in api_calls if any(x in call['url'] for x in [
                '/templates', '/run', '/results', '/analytics'
            ])]
            
            print(f"   Total API calls made: {len(api_calls)}")
            print(f"   Important API calls: {len(important_apis)}")
            
            # ========== CHECK CONSOLE ERRORS ==========
            print("\n7. CONSOLE ERROR CHECK")
            print("-" * 40)
            
            errors = [log for log in console_logs if 'error' in log.lower()]
            if errors:
                print(f"   ⚠ Found {len(errors)} console errors:")
                for err in errors[:5]:
                    print(f"      - {err[:100]}")
            else:
                print("   ✓ No console errors")
                tests_passed.append("No console errors")
            
            # Take final screenshot
            page.screenshot(path="comprehensive_test_final.png")
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            page.screenshot(path="comprehensive_test_error.png")
        
        finally:
            # ========== FINAL SUMMARY ==========
            print("\n" + "=" * 80)
            print("TEST SUMMARY")
            print("=" * 80)
            
            print(f"\n✅ Tests Passed: {len(tests_passed)}")
            for test in tests_passed:
                print(f"   • {test}")
            
            if tests_failed:
                print(f"\n❌ Tests Failed: {len(tests_failed)}")
                for test in tests_failed:
                    print(f"   • {test}")
            
            print(f"\n📊 Success Rate: {len(tests_passed)}/{len(tests_passed) + len(tests_failed)}")
            print("📸 Screenshot: comprehensive_test_final.png")
            
            print("\n\nClosing browser in 10 seconds...")
            time.sleep(10)
            browser.close()

if __name__ == "__main__":
    test_comprehensive()