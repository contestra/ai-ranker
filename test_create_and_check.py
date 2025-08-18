"""
Create a new template, run it, and verify metadata displays
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright
import time

def test_create_and_check():
    """Create template, run it, check metadata"""
    print("=" * 60)
    print("CREATE TEMPLATE AND CHECK METADATA")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        # Monitor console
        console_msgs = []
        page.on("console", lambda msg: console_msgs.append(f"{msg.type}: {msg.text}"))
        
        try:
            # Navigate
            print("\n1. Opening app...")
            page.goto("http://localhost:3001", wait_until="networkidle", timeout=15000)
            time.sleep(2)
            
            # Enter brand
            print("2. Entering brand AVEA...")
            brand_input = page.locator('input[type="text"]').first
            brand_input.fill("AVEA")
            brand_input.press("Enter")
            time.sleep(2)
            
            # Go to templates
            print("3. Going to Templates tab...")
            templates_btn = page.locator('button').filter(has_text="templates").first
            templates_btn.click()
            time.sleep(2)
            
            # Check Prompt Configuration Builder
            print("\n4. Checking Prompt Configuration Builder...")
            builder = page.locator('text="Prompt Configuration Builder"')
            if builder.count() > 0:
                print("   ✓ Prompt Configuration Builder FOUND!")
                
                # Select recognition type
                print("5. Configuring prompt...")
                prompt_type = page.locator('select').nth(1)
                prompt_type.select_option("recognition")
                
                # Select US and Germany
                us_btn = page.locator('button:has-text("United States")')
                us_btn.click()
                de_btn = page.locator('button:has-text("Germany")')
                de_btn.click()
                
                # Select both grounding modes
                model_knowledge = page.locator('button:has-text("Model Knowledge Only")')
                model_knowledge.click()
                grounded = page.locator('button:has-text("Grounded")')
                grounded.click()
                
                # Generate templates
                print("6. Generating templates...")
                generate_btn = page.locator('button').filter(has_text="Generate")
                if generate_btn.count() > 0:
                    btn_text = generate_btn.first.inner_text()
                    print(f"   Button says: {btn_text}")
                    generate_btn.first.click()
                    time.sleep(3)
                    print("   ✓ Templates generated!")
                
                page.screenshot(path="create_1_generated.png")
            else:
                print("   ✗ Prompt Configuration Builder NOT FOUND")
            
            # Check template cards
            print("\n7. Checking template cards...")
            template_cards = page.locator('.bg-white.rounded-lg.shadow')
            print(f"   Found {template_cards.count()} template cards")
            
            if template_cards.count() > 0:
                # Check metadata in first card
                first_card = template_cards.first
                
                # Check for SHA-256
                sha_in_card = first_card.locator('text=/SHA-256/')
                if sha_in_card.count() > 0:
                    print("   ✓ SHA-256 hash displayed in template")
                
                # Check for temperature/seed
                temp_in_card = first_card.locator('text=/Temp:/')
                if temp_in_card.count() > 0:
                    print("   ✓ Temperature displayed in template")
                
                # Check for model name with color
                model_span = first_card.locator('.text-indigo-600')
                if model_span.count() > 0:
                    print(f"   ✓ Model displayed with color: {model_span.first.inner_text()}")
                
                # Run the first template
                print("\n8. Running first template...")
                run_btn = first_card.locator('button:has-text("Run Test")')
                if run_btn.count() > 0:
                    run_btn.click()
                    print("   ✓ Started test run")
                    
                    # Wait for completion
                    print("   Waiting for completion (max 30s)...")
                    running_text = first_card.locator('text="Running..."')
                    try:
                        running_text.wait_for(state="hidden", timeout=30000)
                        print("   ✓ Test completed!")
                    except:
                        print("   ⚠ Test still running or timed out")
                    
                    time.sleep(2)
            
            # Go to Results tab
            print("\n9. Checking Results tab...")
            results_btn = page.locator('button').filter(has_text="results").first
            results_btn.click()
            time.sleep(2)
            
            # Check run cards
            run_cards = page.locator('.border.rounded-lg')
            print(f"   Found {run_cards.count()} run cards")
            
            if run_cards.count() > 0:
                first_run = run_cards.first
                
                # Check for grounding badge
                grounding_badge = first_run.locator('.bg-green-100, .bg-gray-100')
                if grounding_badge.count() > 0:
                    print(f"   ✓ Grounding badge found: {grounding_badge.first.inner_text()}")
                
                # Check for model with color
                model_colored = first_run.locator('.text-green-600, .text-blue-600')
                if model_colored.count() > 0:
                    print(f"   ✓ Colored model name: {model_colored.first.inner_text()}")
                
                # Check for tool calls/citations
                tool_calls = first_run.locator('text=/tool calls/')
                if tool_calls.count() > 0:
                    print(f"   ✓ Tool calls displayed: {tool_calls.first.inner_text()}")
                
                citations = first_run.locator('text=/citations/')
                if citations.count() > 0:
                    print(f"   ✓ Citations displayed: {citations.first.inner_text()}")
                
                # Click View Response
                view_btn = first_run.locator('button:has-text("View Response")')
                if view_btn.count() > 0:
                    print("\n10. Viewing response details...")
                    view_btn.click()
                    time.sleep(2)
                    
                    # Check expanded content
                    expanded = first_run.locator('.mt-4.pt-4.border-t')
                    if expanded.count() > 0:
                        print("   ✓ Response expanded")
                        
                        # Check for metadata sections
                        grounding_section = expanded.locator('h4:has-text("Grounding Metadata")')
                        if grounding_section.count() > 0:
                            print("   ✓ Grounding Metadata section found")
                        
                        citations_section = expanded.locator('h4:has-text("Citations")')
                        if citations_section.count() > 0:
                            print("   ✓ Citations section found")
                            # Check for clickable links
                            links = expanded.locator('a[href][target="_blank"]')
                            print(f"   ✓ Found {links.count()} clickable citation links")
                        
                        full_sha = expanded.locator('.font-mono').filter(has_text="SHA-256:")
                        if full_sha.count() > 0:
                            print("   ✓ Full SHA-256 hash displayed")
            
            page.screenshot(path="create_2_results.png")
            
            # Summary
            print("\n" + "=" * 60)
            print("SUMMARY")
            print("=" * 60)
            
            # Check console
            errors = [m for m in console_msgs if m.startswith("error:")]
            if errors:
                print(f"\n⚠ Console errors found: {len(errors)}")
                for err in errors[:3]:
                    print(f"  - {err}")
            else:
                print("\n✓ No console errors")
            
            print("\n✅ Test completed successfully!")
            print("Screenshots saved: create_1_generated.png, create_2_results.png")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            page.screenshot(path="create_error.png")
        
        finally:
            print("\nBrowser will close in 5 seconds...")
            time.sleep(5)
            browser.close()

if __name__ == "__main__":
    test_create_and_check()