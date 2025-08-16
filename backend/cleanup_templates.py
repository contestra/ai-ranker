#!/usr/bin/env python
"""
Script to clean up duplicate grounding modes in templates.
Converts legacy modes (none, web) to new modes (off, preferred, required).
"""

import requests
import json

API_BASE = "http://localhost:8000/api/prompt-tracking"

def get_templates():
    """Get all templates from the API"""
    response = requests.get(f"{API_BASE}/templates")
    response.raise_for_status()
    return response.json()["templates"]

def clean_grounding_modes(modes):
    """Convert legacy modes to new format and remove duplicates"""
    new_modes = set()
    
    for mode in modes:
        if mode == "none":
            new_modes.add("off")
        elif mode == "web":
            new_modes.add("preferred")
            new_modes.add("required")
        elif mode in ["off", "preferred", "required"]:
            new_modes.add(mode)
    
    # Return sorted list for consistency
    return sorted(list(new_modes))

def update_template(template_id, template_data):
    """Update a template via the API"""
    # Clean the grounding modes
    original_modes = template_data["grounding_modes"]
    cleaned_modes = clean_grounding_modes(original_modes)
    
    # Only update if modes changed
    if set(original_modes) == set(cleaned_modes):
        return False, "No changes needed"
    
    # Prepare update payload
    update_data = {
        "brand_name": template_data["brand_name"],
        "template_name": template_data["template_name"],
        "prompt_text": template_data["prompt_text"],
        "prompt_type": template_data["prompt_type"],
        "model_name": template_data["model_name"],
        "countries": template_data["countries"],
        "grounding_modes": cleaned_modes
    }
    
    # Send update request
    response = requests.put(
        f"{API_BASE}/templates/{template_id}",
        json=update_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        return True, f"Updated from {original_modes} to {cleaned_modes}"
    else:
        return False, f"Error: {response.status_code} - {response.text}"

def main():
    print("Fetching templates...")
    templates = get_templates()
    print(f"Found {len(templates)} templates\n")
    
    updated_count = 0
    error_count = 0
    
    for template in templates:
        template_id = template["id"]
        template_name = template["template_name"]
        
        print(f"Processing template {template_id}: {template_name}")
        
        success, message = update_template(template_id, template)
        
        if success:
            print(f"  ✓ {message}")
            updated_count += 1
        elif message == "No changes needed":
            print(f"  - {message}")
        else:
            print(f"  ✗ {message}")
            error_count += 1
        
        print()
    
    print("\n" + "="*50)
    print(f"Summary: {updated_count} templates updated, {error_count} errors")

if __name__ == "__main__":
    main()