#!/usr/bin/env python3
"""
Test script to verify all grounding modes are working correctly.
Tests the canonical grounding mode implementation.
"""
import sys
import os
import asyncio
import json
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure UTF-8 for Windows
if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')

from app.services.grounding_enforcement import (
    normalize_grounding_mode,
    should_use_grounding,
    is_grounding_enforced,
    validate_grounding_result,
    get_display_label
)

def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print('=' * 60)

def test_normalization():
    """Test grounding mode normalization."""
    print_section("Testing Grounding Mode Normalization")
    
    test_cases = [
        # Legacy values
        ("off", "not_grounded"),
        ("none", "not_grounded"),
        ("web", "preferred"),
        ("required", "enforced"),
        
        # Canonical values
        ("not_grounded", "not_grounded"),
        ("preferred", "preferred"),
        ("enforced", "enforced"),
        
        # Variations
        ("OFF", "not_grounded"),
        ("Web", "preferred"),
        ("REQUIRED", "enforced"),
        ("grounded", "preferred"),
        ("grounded (web search)", "preferred"),
        ("auto", "preferred"),
        
        # Edge cases
        (None, "not_grounded"),
        ("", "not_grounded"),
        ("unknown", "not_grounded"),
    ]
    
    passed = 0
    failed = 0
    
    for input_val, expected in test_cases:
        result = normalize_grounding_mode(input_val)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"  {status} normalize({repr(input_val)}) = {repr(result)} (expected {repr(expected)})")
    
    print(f"\nNormalization: {passed} passed, {failed} failed")
    return failed == 0

def test_grounding_logic():
    """Test grounding decision logic."""
    print_section("Testing Grounding Decision Logic")
    
    test_cases = [
        ("not_grounded", False, False),  # should_use, is_enforced
        ("preferred", True, False),
        ("enforced", True, True),
    ]
    
    passed = 0
    failed = 0
    
    for mode, expect_use, expect_enforced in test_cases:
        use_result = should_use_grounding(mode)
        enforce_result = is_grounding_enforced(mode)
        
        use_ok = use_result == expect_use
        enforce_ok = enforce_result == expect_enforced
        
        status = "✓" if use_ok and enforce_ok else "✗"
        if use_ok and enforce_ok:
            passed += 1
        else:
            failed += 1
            
        print(f"  {status} Mode: {mode}")
        print(f"      should_use_grounding: {use_result} (expected {expect_use})")
        print(f"      is_grounding_enforced: {enforce_result} (expected {expect_enforced})")
    
    print(f"\nGrounding Logic: {passed} passed, {failed} failed")
    return failed == 0

def test_validation():
    """Test grounding result validation."""
    print_section("Testing Grounding Result Validation")
    
    test_cases = [
        # (mode, grounded_effective, provider, expect_valid, expect_error_contains)
        ("not_grounded", False, "openai", True, None),
        ("not_grounded", True, "openai", False, "should not have"),
        
        ("preferred", False, "openai", True, None),
        ("preferred", True, "openai", True, None),
        ("preferred", False, "vertex", True, None),
        ("preferred", True, "vertex", True, None),
        
        ("enforced", False, "openai", False, "required but did not"),
        ("enforced", True, "openai", True, None),
        ("enforced", False, "vertex", False, "app-level enforcement failed"),
        ("enforced", True, "vertex", True, None),
    ]
    
    passed = 0
    failed = 0
    
    for mode, grounded, provider, expect_valid, error_contains in test_cases:
        is_valid, error_msg = validate_grounding_result(mode, grounded, provider)
        
        valid_ok = is_valid == expect_valid
        error_ok = True
        if error_contains:
            error_ok = error_msg and error_contains in error_msg
        elif not expect_valid:
            error_ok = error_msg is not None
        
        status = "✓" if valid_ok and error_ok else "✗"
        if valid_ok and error_ok:
            passed += 1
        else:
            failed += 1
            
        print(f"  {status} validate({mode}, grounded={grounded}, {provider})")
        print(f"      is_valid: {is_valid} (expected {expect_valid})")
        if error_msg:
            print(f"      error: {error_msg}")
    
    print(f"\nValidation: {passed} passed, {failed} failed")
    return failed == 0

def test_display_labels():
    """Test display label generation."""
    print_section("Testing Display Labels")
    
    test_cases = [
        ("not_grounded", "openai", "No Grounding"),
        ("not_grounded", "vertex", "No Grounding"),
        
        ("preferred", "openai", "Web Search (Auto)"),
        ("preferred", "vertex", "Web Search (Model Decides)"),
        
        ("enforced", "openai", "Web Search (Required)"),
        ("enforced", "vertex", "Web Search (App-Enforced)"),
    ]
    
    passed = 0
    failed = 0
    
    for mode, provider, expected in test_cases:
        result = get_display_label(mode, provider)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"  {status} label({mode}, {provider}) = {repr(result)}")
    
    print(f"\nDisplay Labels: {passed} passed, {failed} failed")
    return failed == 0

async def test_api_integration():
    """Test actual API integration with grounding modes."""
    print_section("Testing API Integration")
    
    import aiohttp
    
    # Test creating a template with canonical modes
    async with aiohttp.ClientSession() as session:
        # Create test template
        template_data = {
            "brand_name": "TestBrand",
            "template_name": f"Grounding Test Template",
            "prompt_text": "What are the latest developments in AI?",
            "prompt_type": "custom",
            "model_name": "gemini",
            "countries": ["US"],
            "grounding_modes": ["not_grounded", "preferred"]  # Using canonical values
        }
        
        try:
            async with session.post(
                "http://localhost:8000/api/prompt-tracking/templates",
                json=template_data
            ) as resp:
                if resp.status == 201:
                    result = await resp.json()
                    print(f"  ✓ Created template with ID: {result.get('template_id')}")
                    return True
                elif resp.status == 409:
                    print(f"  ⓘ Template already exists (duplicate)")
                    return True
                else:
                    print(f"  ✗ Failed to create template: {resp.status}")
                    text = await resp.text()
                    print(f"    Response: {text[:200]}")
                    return False
        except Exception as e:
            print(f"  ✗ API error: {e}")
            print("    Make sure the backend is running on port 8000")
            return False

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print(" GROUNDING MODES MIGRATION TEST SUITE")
    print("="*60)
    
    all_passed = True
    
    # Run unit tests
    all_passed &= test_normalization()
    all_passed &= test_grounding_logic()
    all_passed &= test_validation()
    all_passed &= test_display_labels()
    
    # Run integration test
    try:
        api_result = asyncio.run(test_api_integration())
        all_passed &= api_result
    except Exception as e:
        print(f"\n⚠️ Skipping API integration test: {e}")
    
    # Summary
    print_section("Test Summary")
    if all_passed:
        print("✅ ALL TESTS PASSED - Grounding modes migration successful!")
    else:
        print("❌ SOME TESTS FAILED - Please review the errors above")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())