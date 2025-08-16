#!/usr/bin/env python
"""
Script to delete all templates and results from the database.
This will clean up all dummy test data.
"""

import requests
import json

API_BASE = "http://localhost:8000/api/prompt-tracking"

def get_templates():
    """Get all templates from the API"""
    response = requests.get(f"{API_BASE}/templates")
    response.raise_for_status()
    return response.json()["templates"]

def delete_template(template_id):
    """Delete a template via the API"""
    response = requests.delete(f"{API_BASE}/templates/{template_id}")
    return response.status_code == 200

def main():
    print("Fetching all templates...")
    templates = get_templates()
    print(f"Found {len(templates)} templates to delete\n")
    
    deleted_count = 0
    error_count = 0
    
    # Delete templates in reverse order (newer first) to avoid dependency issues
    for template in reversed(templates):
        template_id = template["id"]
        template_name = template["template_name"]
        
        print(f"Deleting template {template_id}: {template_name}")
        
        if delete_template(template_id):
            print(f"  [OK] Deleted successfully")
            deleted_count += 1
        else:
            print(f"  [ERROR] Failed to delete")
            error_count += 1
    
    print("\n" + "="*50)
    print(f"Summary: {deleted_count} templates deleted, {error_count} errors")
    print("\nNote: All associated results were automatically deleted with the templates.")

if __name__ == "__main__":
    main()