#!/usr/bin/env python3
"""
Test to fix Google Cloud authentication with service account impersonation
"""
import os
import sys

# Set UTF-8 encoding for Windows
if sys.platform.startswith('win'):
    os.environ['PYTHONUTF8'] = '1'

def test_impersonation():
    """Test different approaches to service account impersonation"""
    
    print("[AUTH] Testing Google Cloud Authentication with Service Account Impersonation")
    print("=" * 70)
    
    # Set environment variables
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'contestra-ai'
    os.environ['GOOGLE_CLOUD_REGION'] = 'europe-west4'
    os.environ['GOOGLE_IMPERSONATE_SERVICE_ACCOUNT'] = 'vertex-runner@contestra-ai.iam.gserviceaccount.com'
    
    print(f"Environment Variables:")
    print(f"- GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
    print(f"- GOOGLE_CLOUD_REGION: {os.getenv('GOOGLE_CLOUD_REGION')}")
    print(f"- GOOGLE_IMPERSONATE_SERVICE_ACCOUNT: {os.getenv('GOOGLE_IMPERSONATE_SERVICE_ACCOUNT')}")
    print()
    
    # Test 1: google.auth.default() - Current failing approach
    print("TEST 1: google.auth.default() - Current failing approach")
    print("-" * 50)
    try:
        import google.auth
        from google.auth.transport.requests import Request
        
        creds, project = google.auth.default()
        print(f"[OK] Initial auth successful")
        print(f"  - Credential type: {creds.__class__.__name__}")
        print(f"  - Project: {project}")
        print(f"  - Service account: {getattr(creds, 'service_account_email', 'N/A')}")
        
        # Try to refresh
        creds.refresh(Request())
        print(f"[OK] Refresh successful")
        
        # Get access token
        print(f"[OK] Access token: {creds.token[:50]}...")
        
    except Exception as e:
        print(f"[ERROR] FAILED: {e}")
    
    print()
    
    # Test 2: Manual impersonation setup
    print("TEST 2: Manual impersonation using Google Auth library")
    print("-" * 50)
    try:
        from google.auth import impersonated_credentials
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        import google.auth
        
        # Get source credentials (user credentials)
        source_credentials, _ = google.auth.default()
        
        # Create impersonated credentials
        target_credentials = impersonated_credentials.Credentials(
            source_credentials=source_credentials,
            target_principal='vertex-runner@contestra-ai.iam.gserviceaccount.com',
            target_scopes=['https://www.googleapis.com/auth/cloud-platform'],
        )
        
        # Refresh to get token
        target_credentials.refresh(Request())
        
        print(f"[OK] Manual impersonation successful")
        print(f"  - Credential type: {target_credentials.__class__.__name__}")
        print(f"  - Service account: {target_credentials.service_account_email}")
        print(f"  - Token: {target_credentials.token[:50]}...")
        
        return target_credentials
        
    except Exception as e:
        print(f"[ERROR] FAILED: {e}")
    
    print()
    
    # Test 3: Check if we can use gcloud CLI token directly
    print("TEST 3: Using gcloud CLI token directly")
    print("-" * 50)
    try:
        import subprocess
        
        # Get token from gcloud CLI
        result = subprocess.run([
            'gcloud', 'auth', 'print-access-token', 
            '--impersonate-service-account=vertex-runner@contestra-ai.iam.gserviceaccount.com'
        ], capture_output=True, text=True, check=True)
        
        token = result.stdout.strip()
        print(f"[OK] CLI token obtained: {token[:50]}...")
        
        # Test the token by making an API call
        import requests
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Test with a simple GCP API call
        response = requests.get(
            'https://cloudresourcemanager.googleapis.com/v1/projects/contestra-ai',
            headers=headers
        )
        
        if response.status_code == 200:
            print(f"[OK] Token works! Can access project info")
            project_info = response.json()
            print(f"  - Project ID: {project_info.get('projectId')}")
            print(f"  - Project Name: {project_info.get('name')}")
        else:
            print(f"[ERROR] Token test failed: {response.status_code} {response.text}")
            
        return token
            
    except Exception as e:
        print(f"[ERROR] FAILED: {e}")
    
    print()
    
    # Test 4: Try to fix ADC by regenerating it
    print("TEST 4: Regenerating ADC credentials")
    print("-" * 50)
    try:
        import json
        from pathlib import Path
        
        # Get the current user credentials
        source_credentials, _ = google.auth.default()
        
        # Check if we can access the refresh token
        adc_path = Path.home() / 'AppData' / 'Roaming' / 'gcloud' / 'application_default_credentials.json'
        if adc_path.exists():
            with open(adc_path, 'r') as f:
                adc_data = json.load(f)
            
            print(f"[OK] ADC file exists at: {adc_path}")
            print(f"  - Type: {adc_data.get('type')}")
            print(f"  - Client ID: {adc_data.get('client_id')}")
            print(f"  - Has refresh token: {'refresh_token' in adc_data}")
            
            # Try to use the refresh token directly
            if adc_data.get('refresh_token'):
                from google.oauth2.credentials import Credentials
                from google.auth.transport.requests import Request
                
                # Create credentials from the ADC data
                creds = Credentials.from_authorized_user_info(adc_data)
                creds.refresh(Request())
                
                print(f"[OK] Successfully refreshed ADC credentials")
                print(f"  - New token: {creds.token[:50]}...")
                
                return creds
        else:
            print(f"[ERROR] ADC file not found at: {adc_path}")
            
    except Exception as e:
        print(f"[ERROR] FAILED: {e}")
    
    print()
    return None

def test_vertex_with_fixed_auth(credentials=None):
    """Test Vertex AI with the fixed credentials"""
    print("TEST 5: Testing Vertex AI with fixed credentials")
    print("-" * 50)
    
    if credentials is None:
        print("[ERROR] No credentials available for testing")
        return
    
    try:
        # Try to use the credentials with Vertex AI
        if isinstance(credentials, str):  # It's a token
            # Use the token directly with requests
            import requests
            
            headers = {
                'Authorization': f'Bearer {credentials}',
                'Content-Type': 'application/json'
            }
            
            # Make a simple API call to Vertex AI
            url = 'https://europe-west4-aiplatform.googleapis.com/v1/projects/contestra-ai/locations/europe-west4/publishers/google/models/gemini-2.0-flash:generateContent'
            
            payload = {
                "contents": [{"parts": [{"text": "Hello"}]}],
                "generation_config": {"maxOutputTokens": 10}
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                print(f"[OK] Vertex AI API call successful")
                print(f"  - Response: {result}")
            else:
                print(f"[ERROR] Vertex AI API call failed: {response.status_code}")
                print(f"  - Error: {response.text}")
        else:
            # Use credentials object with google-genai library
            print(f"[OK] Using credentials object: {type(credentials)}")
            # This would require modifying the Vertex adapter to accept custom credentials
            
    except Exception as e:
        print(f"[ERROR] FAILED: {e}")

if __name__ == "__main__":
    # Run the authentication tests
    fixed_creds = test_impersonation()
    
    # Test Vertex AI if we got working credentials
    if fixed_creds:
        test_vertex_with_fixed_auth(fixed_creds)
    
    print()
    print("[COMPLETE] Authentication testing complete")