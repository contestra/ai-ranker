#!/usr/bin/env python
"""
Test the prompt tracking API with grounding to see if it works after our fix
"""

import asyncio
import httpx
import json

async def test_prompt_tracking():
    """Test prompt tracking with grounding"""
    
    # First, get or create a template
    async with httpx.AsyncClient() as client:
        # Get existing templates
        response = await client.get("http://localhost:8000/api/prompt-tracking/templates?brand_name=avea")
        templates = response.json()["templates"]
        
        if templates:
            template_id = templates[0]["id"]
            print(f"Using existing template ID: {template_id}")
        else:
            # Create a new template
            template_data = {
                "brand_name": "avea",
                "template_name": "Test Grounding",
                "prompt_text": "List the top 10 longevity supplement brands",
                "prompt_type": "custom",
                "model_name": "gemini",
                "countries": ["US", "CH"],
                "grounding_modes": ["none", "web"]
            }
            response = await client.post(
                "http://localhost:8000/api/prompt-tracking/templates",
                json=template_data
            )
            if response.status_code == 409:
                # Duplicate, get the existing one
                templates = await client.get("http://localhost:8000/api/prompt-tracking/templates?brand_name=avea")
                template_id = templates.json()["templates"][0]["id"]
            else:
                template_id = response.json()["id"]
            print(f"Created new template ID: {template_id}")
        
        # Now run the template with grounding
        print("\n" + "=" * 60)
        print("Testing prompt tracking with Gemini grounding...")
        print("=" * 60)
        
        run_data = {
            "template_id": template_id,
            "brand_name": "avea",
            "model_name": "gemini",
            "countries": ["US", "CH"],
            "grounding_modes": ["web"]  # Test grounding mode only
        }
        
        print("\nRunning template with grounding mode...")
        print(f"Request: {json.dumps(run_data, indent=2)}")
        
        response = await client.post(
            "http://localhost:8000/api/prompt-tracking/run",
            json=run_data,
            timeout=120.0  # Long timeout for Gemini
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"\nSUCCESS - Response received")
            print(f"Template: {results.get('template_name')}")
            print(f"Brand: {results.get('brand_name')}")
            
            for result in results.get("results", []):
                print(f"\nCountry: {result.get('country')}")
                print(f"Grounding Mode: {result.get('grounding_mode')}")
                if "error" in result:
                    print(f"ERROR: {result['error']}")
                else:
                    print(f"Brand Mentioned: {result.get('brand_mentioned')}")
                    print(f"Mention Count: {result.get('mention_count')}")
                    print(f"Response Preview: {result.get('response_preview', '')[:100]}...")
        else:
            print(f"FAILED - Status code: {response.status_code}")
            print(f"Response: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_prompt_tracking())