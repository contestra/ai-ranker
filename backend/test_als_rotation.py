#!/usr/bin/env python
"""
Test script to verify ALS civic phrase rotation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.als import als_service

def test_rotation():
    """Test that civic phrases rotate when called multiple times"""
    country = "DE"
    phrases_seen = set()
    
    print(f"Testing ALS rotation for {country}...")
    print("=" * 60)
    
    # Call 20 times to see if we get different phrases
    for i in range(20):
        block = als_service.build_als_block(country)
        
        # Extract the civic phrase (it's on the 3rd line after the quotes)
        lines = block.split('\n')
        if len(lines) >= 3:
            # Line format: - Bundesportal — "phrase here"
            civic_line = lines[2]
            # Extract phrase between quotes
            if '"' in civic_line:
                start = civic_line.index('"') + 1
                end = civic_line.rindex('"')
                phrase = civic_line[start:end]
                phrases_seen.add(phrase)
                print(f"Run {i+1:2d}: {phrase}")
    
    print("=" * 60)
    print(f"Unique phrases seen: {len(phrases_seen)}")
    print("Phrases:")
    for phrase in sorted(phrases_seen):
        print(f"  - {phrase}")
    
    # Test without randomization (should always get the same phrase)
    print("\n" + "=" * 60)
    print("Testing without randomization (randomize=False)...")
    non_random_phrases = set()
    for i in range(5):
        block = als_service.build_als_block(country, randomize=False)
        lines = block.split('\n')
        if len(lines) >= 3:
            civic_line = lines[2]
            if '"' in civic_line:
                start = civic_line.index('"') + 1
                end = civic_line.rindex('"')
                phrase = civic_line[start:end]
                non_random_phrases.add(phrase)
                print(f"Run {i+1}: {phrase}")
    
    print(f"Unique phrases without randomization: {len(non_random_phrases)}")
    
    if len(non_random_phrases) == 1:
        print("✓ Without randomization: Always returns the same phrase (correct)")
    else:
        print("✗ Without randomization: Returns different phrases (incorrect)")
    
    if len(phrases_seen) > 1:
        print(f"✓ With randomization: Returns {len(phrases_seen)} different phrases (rotation working)")
    else:
        print("✗ With randomization: Always returns the same phrase (rotation NOT working)")

if __name__ == "__main__":
    test_rotation()