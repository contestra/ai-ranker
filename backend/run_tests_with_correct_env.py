#!/usr/bin/env python
"""
Run production tests with correct environment setup
Removes GOOGLE_APPLICATION_CREDENTIALS to use ADC
"""
import os
import sys
import subprocess

# Remove the problematic environment variable
if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
    print(f"Removing GOOGLE_APPLICATION_CREDENTIALS: {os.environ['GOOGLE_APPLICATION_CREDENTIALS']}")
    del os.environ['GOOGLE_APPLICATION_CREDENTIALS']

# Set the correct project explicitly
os.environ['GOOGLE_CLOUD_PROJECT'] = 'contestra-ai'
os.environ['GCLOUD_PROJECT'] = 'contestra-ai'

# Verify ADC
import google.auth
creds, project = google.auth.default()
print(f"ADC project detected: {project}")

# If still wrong, use the creds with quota_project_id
if project != 'contestra-ai':
    print("Warning: ADC still using wrong project, will pass project explicitly to APIs")

# Run the test
print("\nRunning production architecture tests...")
result = subprocess.run([sys.executable, 'test_production_architecture.py'], cwd=os.path.dirname(__file__))
sys.exit(result.returncode)