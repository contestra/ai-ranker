# Google Cloud Authentication Setup for Vertex AI

## Quick Fix for Authentication Issues

If you're encountering Vertex AI permission errors or authentication loops, follow this clean setup:

### 1. Clean Setup (Windows PowerShell) - UPDATED

Open PowerShell (regular, not admin) and run these commands exactly:

```powershell
# Pin gcloud path (adjust if your install path differs)
$GCLOUD = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

# Clear the stale SA override (current session + User scope)
$env:GOOGLE_APPLICATION_CREDENTIALS = $null
[Environment]::SetEnvironmentVariable('GOOGLE_APPLICATION_CREDENTIALS', $null, 'User')
# Note: Machine scope needs admin; skip it for local dev

# Remove old ADC file safely
$adc = Join-Path $env:APPDATA 'gcloud\application_default_credentials.json'
if (Test-Path $adc) { Remove-Item -Force $adc }

# Point gcloud to the right project
& $GCLOUD config set project contestra-ai

# Device-flow login (NO browser callback to localhost)
& $GCLOUD auth application-default login --no-browser --project contestra-ai
# Follow on-screen instructions: copy URL to any browser, paste code, approve
```

**Important**: The device-flow step MUST be completed once by a human. You'll see a URL and a code - open the URL in any browser, paste the code when prompted, and approve.

### 2. Verify Authentication

After completing the device-flow authentication:

```powershell
# Sanity checks
& $GCLOUD auth application-default print-access-token | Out-Null
& $GCLOUD auth list
& $GCLOUD config get-value core/project

# Enable Vertex AI API (only after auth succeeds)
& $GCLOUD services enable aiplatform.googleapis.com --project=contestra-ai

# Quick Python smoke test
python -c "from google import genai; from google.genai.types import GenerateContentConfig; c = genai.Client(vertexai=True, project='contestra-ai', location='global'); r = c.models.generate_content(model='gemini-2.5-pro', contents='Say OK', config=GenerateContentConfig(temperature=0)); print(getattr(r, 'text', '') or 'OK')"
```

If the smoke test prints "OK", your ADC and project are configured correctly.

### 3. Why This Works

- **ADC (Application Default Credentials)** is what Vertex AI client libraries read by default
- Clearing `GOOGLE_APPLICATION_CREDENTIALS` prevents old service-account keys from hijacking calls
- `--no-browser` uses device flow, avoiding the `http://localhost:8085/` redirect issue
- Using `$null` instead of empty string properly clears environment variables in PowerShell

### 4. Common Issues and Solutions

#### Permission Denied Error
```
Permission 'aiplatform.endpoints.predict' denied on resource
```

**Solutions:**
1. Enable the Vertex AI API:
   ```bash
   gcloud services enable aiplatform.googleapis.com --project=contestra-ai
   ```

2. Grant IAM permissions (via Console or CLI):
   ```bash
   gcloud projects add-iam-policy-binding contestra-ai \
     --member="user:YOUR_EMAIL@domain.com" \
     --role="roles/aiplatform.user"
   ```

#### Authentication Token Expired
If you see "Reauthentication failed", use the device flow method above.

#### PowerShell Syntax Errors

Common PowerShell pitfalls and fixes:
- **"Missing expression after ','"** - Use `$null` not bare comma: `[Environment]::SetEnvironmentVariable('VAR', $null, 'User')`
- **"Requested registry access not allowed"** - Machine scope needs admin. Use User scope for local dev
- **"The term ':VAR' is not recognized"** - Escape issue. Use proper quotes: `$env:VAR = $null`

#### Old Credentials Keep Reappearing
Ensure you:
1. Clear the environment variable (`$env:GOOGLE_APPLICATION_CREDENTIALS = $null`)
2. Remove the ADC file (`Remove-Item -Force $adc`)
3. Restart any running processes (IDE, terminal, backend) to reload environment

### 5. Code Guardrails

Add these checks to your code to prevent authentication issues:

```python
# Verify project on startup
import google.auth
creds, proj = google.auth.default()
assert proj == "contestra-ai", f"ADC project is {proj}, expected contestra-ai"

# Always pass project explicitly
from google import genai
client = genai.Client(
    vertexai=True, 
    project="contestra-ai",  # Always explicit
    location="europe-west4"
)
```

### 6. Quick Smoke Test (Updated)

After setup, test Vertex AI access with the correct model path:

```python
from google import genai
from google.genai.types import GenerateContentConfig

# Note: Use 'global' location for better grounding support
client = genai.Client(vertexai=True, project="contestra-ai", location="global")
resp = client.models.generate_content(
    model="gemini-2.5-pro",  # or "publishers/google/models/gemini-2.5-pro"
    contents="Say OK",
    config=GenerateContentConfig(temperature=0)
)
print(getattr(resp, "text", "") or "Connection working")
```

### 7. For Production/CI

Use a dedicated service account instead of ADC:

1. Create service account: `vertex-runner@contestra-ai.iam.gserviceaccount.com`
2. Grant role: `roles/aiplatform.user`
3. Download key and set: `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`

## What NOT to Do

- **Don't flip `GOOGLE_APPLICATION_CREDENTIALS` to random JSON files** - Especially avoid reusing old service account keys from different projects
- **Don't try to enable services with expired auth** - Fix authentication first, then enable APIs
- **Don't rely on implicit project detection** - Always specify project explicitly in your code
- **Don't use the localhost:8085 browser flow** - Use `--no-browser` device flow instead
- **Don't reuse old keys like `llm-entity-probe-438c83aadfdd.json`** - Wrong project, wrong permissions

## Required APIs

Ensure these are enabled:
- `aiplatform.googleapis.com` - Vertex AI API
- `bigquery.googleapis.com` - BigQuery API (if using analytics)

## Troubleshooting Commands

```bash
# Check current authentication
gcloud auth list

# Check application default credentials
gcloud auth application-default print-access-token

# Check project
gcloud config get-value project

# List enabled APIs
gcloud services list --enabled --filter="name:aiplatform"

# Check if old env var is still set
echo $env:GOOGLE_APPLICATION_CREDENTIALS

# Restart backend to pick up new credentials (after auth fix)
# Kill the backend process and restart it
```

## Complete Authentication Process Summary

1. **Clear old credentials** (environment variables and ADC file)
2. **Set correct project** (`contestra-ai`)
3. **Device-flow authentication** (avoids localhost:8085 issue)
4. **Verify with smoke test** (should print "OK")
5. **Restart backend** to pick up new credentials
6. **Test in application** (Vertex AI calls should now work)