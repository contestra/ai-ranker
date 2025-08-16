# Vertex AI Authentication Solution (Working Method)

## Option A: Service Account (Fastest - Recommended)

This avoids all browser authentication issues and works immediately.

### Step 1: Create Service Account
1. Go to Google Cloud Console for project **contestra-ai**
2. Create or reuse service account: `vertex-runner@contestra-ai.iam.gserviceaccount.com`
3. Grant these roles:
   - `roles/aiplatform.user`
   - (Optional) `roles/bigquery.dataEditor` and `roles/bigquery.jobUser` if using analytics

### Step 2: Download and Set Key
1. Download the service account key JSON
2. Save it to a secure location, e.g., `C:\keys\vertex-runner.json`

### Step 3: Configure Environment (PowerShell)
```powershell
# Set environment variable permanently for your user
[Environment]::SetEnvironmentVariable('GOOGLE_APPLICATION_CREDENTIALS','C:\keys\vertex-runner.json','User')

# Also set for current session
$env:GOOGLE_APPLICATION_CREDENTIALS = 'C:\keys\vertex-runner.json'

# Configure gcloud
$GCLOUD = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$env:Path = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin;$env:Path"
& $GCLOUD config set project contestra-ai

# Optional: Activate SA for CLI
& $GCLOUD auth activate-service-account --key-file="$env:GOOGLE_APPLICATION_CREDENTIALS"
```

### Step 4: Quick Test
```powershell
python - << 'PY'
from google import genai
from google.genai.types import GenerateContentConfig
c = genai.Client(vertexai=True, project="contestra-ai", location="global")
r = c.models.generate_content(
    model="publishers/google/models/gemini-2.5-pro",
    contents="Say OK",
    config=GenerateContentConfig(temperature=0)
)
print(getattr(r, "text", "") or "OK")
PY
```

If you see "OK", you're done! Restart your backend to pick up the new credentials.

---

## Option B: User ADC with Device Flow (Alternative)

If you prefer user authentication instead of service account:

### Step 1: Clear Old Credentials
```powershell
$GCLOUD = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$env:GOOGLE_APPLICATION_CREDENTIALS = $null
[Environment]::SetEnvironmentVariable('GOOGLE_APPLICATION_CREDENTIALS', $null, 'User')

# Remove old ADC
$adc = Join-Path $env:APPDATA 'gcloud\application_default_credentials.json'
if (Test-Path $adc) { Remove-Item -Force $adc }
```

### Step 2: Configure Project
```powershell
# Verify gcloud works with full path
& $GCLOUD --version
& $GCLOUD config set project contestra-ai
```

### Step 3: Device Flow Authentication
```powershell
& $GCLOUD auth application-default login --no-browser --project contestra-ai
```

**If it shows a verification URL + code:**
- Open the URL in any browser
- Enter the code
- Approve
- Return to terminal and press Enter

**If it shows a remote-bootstrap command:**
- Copy the ENTIRE command including the URL
- Run it with the full path:
```powershell
& $GCLOUD auth application-default login --remote-bootstrap="https://accounts.google.com/..."
```
- Copy the output blob back to the first prompt

### Step 4: Verify and Enable API
```powershell
# Verify authentication
& $GCLOUD auth application-default print-access-token | Out-Null
& $GCLOUD config get-value core/project

# Enable Vertex AI
& $GCLOUD services enable aiplatform.googleapis.com --project=contestra-ai
```

### Step 5: Test (same as Option A)
Run the Python smoke test above.

---

## Why Previous Attempts Failed

1. **Path Issue**: PowerShell couldn't find `gcloud` - must use full path `& $GCLOUD`
2. **EOFError**: Device flow prompt is fragile in wrapped commands
3. **localhost:8085**: Browser callback doesn't work properly - use `--no-browser`
4. **Stale Service Account**: Old `GOOGLE_APPLICATION_CREDENTIALS` was pointing to wrong project

## Recommendation

**Use Option A (Service Account)** - it's simpler, more reliable, and works immediately without any browser authentication complexity.

## After Authentication Succeeds

1. **Restart your backend** to pick up new credentials:
   ```powershell
   # Kill the Python process and restart
   cd backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **Test in your application** - Vertex AI calls should now work properly

## Troubleshooting

If you get permission errors after authentication:
- Ensure the service account has `roles/aiplatform.user` role
- Verify project is set to `contestra-ai`
- Check that Vertex AI API is enabled
- Restart all Python processes to reload credentials