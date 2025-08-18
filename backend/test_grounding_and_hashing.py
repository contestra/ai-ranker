#!/usr/bin/env python3
"""
Test script to show what parameters are hashed for both OpenAI and Gemini models
and verify that grounding modes work correctly.
"""

import json
from app.services.prompt_hasher import calculate_bundle_hash, _normalize_modes, _normalize_countries

def test_hash_calculation():
    """Show what gets hashed for different model configurations."""
    
    test_cases = [
        {
            "name": "Gemini with Grounding On",
            "model": "gemini-2.5-pro",
            "prompt": "What are the top 10 longevity supplement brands?",
            "countries": ["US", "CH"],
            "modes": ["off", "preferred"],  # Frontend sends these values
        },
        {
            "name": "OpenAI with Required Grounding",
            "model": "gpt-5",
            "prompt": "What are the top 10 longevity supplement brands?",
            "countries": ["US", "CH"],
            "modes": ["off", "required"],  # Frontend sends these values
        },
        {
            "name": "Gemini Base Model (NONE country)",
            "model": "gemini-2.5-pro",
            "prompt": "What are the top 10 longevity supplement brands?",
            "countries": ["NONE"],
            "modes": ["off"],
        },
    ]
    
    print("=" * 80)
    print("HASH CALCULATION TEST - What Parameters Are Included")
    print("=" * 80)
    
    for test in test_cases:
        print(f"\n{test['name']}")
        print("-" * 40)
        
        # Show raw input
        print("RAW INPUT:")
        print(f"  Model: {test['model']}")
        print(f"  Countries: {test['countries']}")
        print(f"  Modes: {test['modes']}")
        print(f"  Prompt: {test['prompt'][:50]}...")
        
        # Show normalized values that will be hashed
        normalized_countries = _normalize_countries(test['countries'])
        normalized_modes = _normalize_modes(test['modes'])
        
        print("\nNORMALIZED FOR HASHING:")
        print(f"  Model: {test['model']}")
        print(f"  Countries: {normalized_countries}")
        print(f"  Modes: {normalized_modes}")
        print(f"  Prompt: (whitespace collapsed)")
        
        # Calculate hash
        hash_value = calculate_bundle_hash(
            test['prompt'],
            model_name=test['model'],
            countries=test['countries'],
            grounding_modes=test['modes']
        )
        
        print(f"\nHASH: {hash_value[:16]}...")
        
        # Show what's actually in the hash
        canonical = {
            "prompt_text": test['prompt'].strip(),
            "countries": normalized_countries,
            "grounding_modes": normalized_modes,
            "model_name": test['model'],
        }
        print(f"\nHASHED JSON STRUCTURE:")
        print(json.dumps(canonical, indent=2))

def test_grounding_mode_processing():
    """Test how grounding modes are processed for routing."""
    
    print("\n" + "=" * 80)
    print("GROUNDING MODE PROCESSING TEST")
    print("=" * 80)
    
    modes = ["off", "preferred", "required"]
    
    for mode in modes:
        # Simulate what prompt_tracking.py does
        mode_lower = mode.lower()
        needs_grounding = mode_lower in ("web", "preferred", "required")
        grounding_forced = mode_lower == "required"
        
        print(f"\nMode: '{mode}'")
        print(f"  needs_grounding: {needs_grounding}")
        print(f"  grounding_forced: {grounding_forced}")
        print(f"  -> Will pass use_grounding={needs_grounding} to adapter")
        
        # Show normalization for hashing
        normalized = _normalize_modes([mode])
        print(f"  -> Normalized for hash: {normalized}")

if __name__ == "__main__":
    test_hash_calculation()
    test_grounding_mode_processing()
    
    print("\n" + "=" * 80)
    print("KEY INSIGHTS:")
    print("=" * 80)
    print("""
1. HASHING includes these parameters:
   - prompt_text (whitespace normalized)
   - model_name (exact string)
   - countries (uppercase, sorted, NONE for base model)
   - grounding_modes (normalized to 'none' or 'web')
   
2. GROUNDING MODE MAPPING:
   - 'off' -> needs_grounding=False (hash: 'none')
   - 'preferred' -> needs_grounding=True (hash: 'web')
   - 'required' -> needs_grounding=True, forced=True (hash: 'web')
   
3. MODEL DIFFERENCES:
   - Gemini: Only uses needs_grounding flag (on/off)
   - OpenAI: Can use grounding_forced for enforcement
   
4. IMPORTANT: 'preferred' and 'required' both hash to 'web'
   This means they're considered the same template configuration
   for deduplication purposes.
""")