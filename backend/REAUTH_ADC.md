# Re-authenticate ADC with Correct Project

## Issue Found
Your ADC is pointing to `llm-entity-probe` project instead of `contestra-ai`!

## Fix: Re-authenticate ADC

Run this in **PowerShell**:

```powershell
# Set the default project to contestra-ai
gcloud config set project contestra-ai

# Re-authenticate ADC (this will open a browser)
gcloud auth application-default login

# When browser opens:
# 1. Choose your account
# 2. Allow access
# 3. You'll see "You are now authenticated"
```

## Alternative: Set project explicitly in environment

If you can't run gcloud commands, add this to your PowerShell before running Python:

```powershell
$env:GOOGLE_CLOUD_PROJECT = "contestra-ai"
$env:GCLOUD_PROJECT = "contestra-ai"
```

Then test:
```powershell
cd backend
python test_vertex_after_iam.py
```

## Why This Happened
You previously authenticated ADC for a different project (`llm-entity-probe`). The IAM role you just added is on `contestra-ai`, but your ADC is still pointing to the old project.

## Quick Test After Re-auth
```python
import google.auth
credentials, project = google.auth.default()
print(f"Project: {project}")  # Should show: contestra-ai
```