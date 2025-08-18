"""
Generate OAuth consent URL for Vertex AI access
This creates a browser URL for user authentication without gcloud CLI
"""

import webbrowser
from urllib.parse import urlencode

# OAuth 2.0 parameters for Google Cloud
oauth_params = {
    'client_id': '764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com',
    'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',  # For manual copy-paste flow
    'response_type': 'code',
    'scope': ' '.join([
        'https://www.googleapis.com/auth/cloud-platform',
        'https://www.googleapis.com/auth/userinfo.email',
        'openid'
    ]),
    'access_type': 'offline',
    'prompt': 'consent'
}

# Generate the OAuth consent URL
base_url = 'https://accounts.google.com/o/oauth2/v2/auth'
auth_url = f"{base_url}?{urlencode(oauth_params)}"

print("=" * 70)
print("VERTEX AI AUTHENTICATION")
print("=" * 70)
print("\nOpen this URL in your browser to authenticate:")
print("\n" + auth_url)
print("\n" + "=" * 70)
print("\nAfter approving, you'll get an authorization code.")
print("Copy the code and we'll exchange it for credentials.")
print("=" * 70)

# Try to open in browser
try:
    webbrowser.open(auth_url)
    print("\n✓ Opening browser...")
except:
    print("\n⚠ Could not open browser automatically. Please copy the URL above.")