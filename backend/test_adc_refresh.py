#!/usr/bin/env python
"""
Check ADC status and try refreshing credentials
"""

import os
import google.auth
from google.auth.transport.requests import Request

print("Checking ADC credentials...")
print("=" * 50)

try:
    # Get current credentials
    credentials, project = google.auth.default()
    print(f"Project: {project}")
    print(f"Credentials type: {type(credentials).__name__}")
    
    # Check if credentials are valid
    if hasattr(credentials, 'valid'):
        print(f"Valid: {credentials.valid}")
    
    if hasattr(credentials, 'expired'):
        print(f"Expired: {credentials.expired}")
    
    # Try to refresh credentials
    print("\nRefreshing credentials...")
    if hasattr(credentials, 'refresh'):
        try:
            request = Request()
            credentials.refresh(request)
            print("Credentials refreshed successfully!")
        except Exception as e:
            print(f"Refresh failed: {e}")
    
    # Now test Vertex
    print("\n" + "=" * 50)
    print("Testing Vertex AI with refreshed credentials...")
    
    from google import genai
    client = genai.Client(vertexai=True, project="contestra-ai", location="europe-west4")
    response = client.models.generate_content(model="gemini-1.5-flash-002", contents="Say OK")
    print(f"SUCCESS: {response.text.strip()}")
    
except Exception as e:
    print(f"Error: {e}")
    print("\n" + "=" * 50)
    print("TROUBLESHOOTING:")
    print("1. IAM may still be propagating (can take up to 5 minutes)")
    print("2. You may need to re-authenticate:")
    print("   gcloud auth application-default login")
    print("3. Make sure you added 'Vertex AI User' role, not just 'Vertex AI Viewer'")
    print("4. Check the role was added to YOUR email, not a service account")