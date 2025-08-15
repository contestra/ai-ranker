#!/usr/bin/env python
"""
Debug Gemini API issues
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
import google.generativeai as genai

# Configure with API key
genai.configure(api_key=settings.google_api_key)

def test_direct_api():
    """Test using the direct Google API instead of LangChain"""
    
    print("Testing direct Google Generative AI API...")
    print(f"API Key present: {bool(settings.google_api_key)}")
    print(f"API Key length: {len(settings.google_api_key) if settings.google_api_key else 0}")
    
    try:
        # Create model directly
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Generate content
        response = model.generate_content("What is 2+2?")
        
        # Check the response more carefully
        print(f"Response object: {response}")
        
        if hasattr(response, 'prompt_feedback'):
            print(f"Prompt feedback: {response.prompt_feedback}")
            
        if hasattr(response, 'candidates') and response.candidates:
            for i, candidate in enumerate(response.candidates):
                print(f"Candidate {i}:")
                print(f"  Finish reason: {candidate.finish_reason}")
                if hasattr(candidate, 'safety_ratings'):
                    print(f"  Safety ratings: {candidate.safety_ratings}")
                if hasattr(candidate, 'content'):
                    print(f"  Content: {candidate.content}")
        
        # Try to get text
        try:
            if response.text:
                print(f"SUCCESS: {response.text}")
        except Exception as e:
            print(f"Cannot get text: {e}")
                
    except Exception as e:
        print(f"ERROR: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    test_direct_api()