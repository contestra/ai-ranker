# fix_vertex_powershell.ps1
# MUST run in PowerShell (not Git Bash/WSL/CMD)
# Run everything in the SAME PowerShell window

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "VERTEX AI AUTHENTICATION FIX - POWERSHELL ONLY" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Sanity checks
Write-Host "Step 1: Sanity checks..." -ForegroundColor Yellow
$gcloudPath = Get-Command gcloud -ErrorAction SilentlyContinue
if (-not $gcloudPath) {
    Write-Host "[ERROR] gcloud not found. Install from https://cloud.google.com/sdk" -ForegroundColor Red
    exit 1
}
Write-Host "  gcloud location: $($gcloudPath.Source)" -ForegroundColor Gray
Write-Host "  APPDATA: $env:APPDATA" -ForegroundColor Gray
Write-Host "  User: $(whoami)" -ForegroundColor Gray

# Verify this is Windows gcloud, not WSL
if ($gcloudPath.Source -like "*wsl*") {
    Write-Host "[ERROR] You're using WSL gcloud. Use Windows gcloud instead!" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Using Windows gcloud" -ForegroundColor Green
Write-Host ""

# Step 2: Clean old ADC
Write-Host "Step 2: Removing old ADC file..." -ForegroundColor Yellow
Remove-Item "$env:APPDATA\gcloud\application_default_credentials.json" -ErrorAction SilentlyContinue
Write-Host "  ✓ Old ADC removed (if existed)" -ForegroundColor Green
Write-Host ""

# Step 3: Set project
Write-Host "Step 3: Setting project to contestra-ai..." -ForegroundColor Yellow
gcloud config set project contestra-ai 2>$null
Write-Host "  ✓ Project set" -ForegroundColor Green
Write-Host ""

# Step 4: User login (if needed)
Write-Host "Step 4: Checking user authentication..." -ForegroundColor Yellow
$currentUser = gcloud config get account 2>$null
if (-not $currentUser) {
    Write-Host "  No user logged in. Opening browser for login..." -ForegroundColor Cyan
    gcloud auth login
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] User login failed!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  Already logged in as: $currentUser" -ForegroundColor Gray
}
Write-Host "  ✓ User authenticated" -ForegroundColor Green
Write-Host ""

# Step 5: Create ADC (CRITICAL - must be in same session)
Write-Host "Step 5: Creating Application Default Credentials..." -ForegroundColor Yellow
Write-Host "  Browser will open - complete authentication there" -ForegroundColor Cyan
gcloud auth application-default login
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] ADC creation failed!" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ ADC created" -ForegroundColor Green
Write-Host ""

# Step 6: Set quota project (CRITICAL for billing)
Write-Host "Step 6: Setting quota project..." -ForegroundColor Yellow
gcloud auth application-default set-quota-project contestra-ai
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to set quota project!" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Quota project set" -ForegroundColor Green
Write-Host ""

# Step 7: Verify ADC file exists
Write-Host "Step 7: Verifying ADC file..." -ForegroundColor Yellow
$adcPath = "$env:APPDATA\gcloud\application_default_credentials.json"
if (Test-Path $adcPath) {
    Write-Host "  ✓ ADC file exists at: $adcPath" -ForegroundColor Green
    $adcContent = Get-Content $adcPath | ConvertFrom-Json
    Write-Host "  Type: $($adcContent.type)" -ForegroundColor Gray
} else {
    Write-Host "  ✗ ADC file NOT found - authentication failed!" -ForegroundColor Red
    Write-Host "  This means gcloud ran in a different context." -ForegroundColor Red
    Write-Host "  Make sure you're in PowerShell, not Git Bash/WSL!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 8: Grant TokenCreator role (CRITICAL!)
Write-Host "Step 8: Granting TokenCreator permission..." -ForegroundColor Yellow
$userEmail = gcloud config get account 2>$null
Write-Host "  User: $userEmail" -ForegroundColor Gray

$PROJECT = "contestra-ai"
$SA = "vertex-runner@$PROJECT.iam.gserviceaccount.com"

# Grant the permission
gcloud iam service-accounts add-iam-policy-binding $SA `
    --role="roles/iam.serviceAccountTokenCreator" `
    --member="user:$userEmail" `
    --project $PROJECT `
    --quiet 2>$null

# Verify it worked
Write-Host "  Verifying permission..." -ForegroundColor Gray
$testResult = gcloud auth print-access-token --impersonate-service-account=$SA 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ TokenCreator permission verified!" -ForegroundColor Green
} else {
    Write-Host "  ✗ TokenCreator permission FAILED!" -ForegroundColor Red
    Write-Host "  Error: Permission iam.serviceAccounts.getAccessToken denied" -ForegroundColor Red
    Write-Host "" -ForegroundColor Red
    Write-Host "  FIX: Have an admin run:" -ForegroundColor Yellow
    Write-Host "  gcloud iam service-accounts add-iam-policy-binding $SA ``" -ForegroundColor White
    Write-Host "    --role='roles/iam.serviceAccountTokenCreator' ``" -ForegroundColor White
    Write-Host "    --member='user:$userEmail' ``" -ForegroundColor White
    Write-Host "    --project $PROJECT" -ForegroundColor White
    exit 1
}

# Also ensure the SA has Vertex permissions
Write-Host "  Ensuring SA has Vertex permissions..." -ForegroundColor Gray
gcloud projects add-iam-policy-binding $PROJECT `
    --member="serviceAccount:$SA" `
    --role="roles/aiplatform.user" `
    --quiet 2>$null

gcloud projects add-iam-policy-binding $PROJECT `
    --member="serviceAccount:$SA" `
    --role="roles/serviceusage.serviceUsageConsumer" `
    --quiet 2>$null

Write-Host "  ✓ Service account permissions ensured" -ForegroundColor Green
Write-Host ""

# Step 9: Choose impersonation method
Write-Host "Step 9: Setting up service account impersonation..." -ForegroundColor Yellow
Write-Host "  Using BOTH methods for maximum compatibility:" -ForegroundColor Gray

# Method A: CLI impersonation (works in same session)
gcloud config set auth/impersonate_service_account vertex-runner@contestra-ai.iam.gserviceaccount.com 2>$null
$impersonatedSA = gcloud config get auth/impersonate_service_account 2>$null
Write-Host "  ✓ CLI impersonation: $impersonatedSA" -ForegroundColor Green

# Method B: Environment variables (always works)
$env:GOOGLE_IMPERSONATE_SERVICE_ACCOUNT = "vertex-runner@contestra-ai.iam.gserviceaccount.com"
$env:GOOGLE_CLOUD_PROJECT = "contestra-ai"
$env:GOOGLE_CLOUD_REGION = "europe-west4"
$env:PYTHONUTF8 = "1"
$env:CONTESTRA_DISABLE_GEMINI_FALLBACK = "1"

Write-Host "  ✓ Environment variables set" -ForegroundColor Green
Write-Host ""

# Step 10: Strict Python test (MUST run in same session)
Write-Host "Step 10: Testing Vertex AI connection..." -ForegroundColor Yellow
Write-Host "  Running Python test in THIS session..." -ForegroundColor Gray

$pythonTest = @'
import os, sys
import google.auth
from google.auth.transport.requests import Request

try:
    # Get credentials
    creds, proj = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    
    print(f"Credential type: {creds.__class__.__name__}")
    print(f"Quota project  : {proj or os.getenv('GOOGLE_CLOUD_PROJECT')}")
    print(f"Impersonated SA: {getattr(creds, 'service_account_email', None)}")
    
    # Check if impersonating
    if "Impersonated" not in creds.__class__.__name__ and not getattr(creds, 'service_account_email', None):
        print("WARNING: Not impersonating service account!")
    
    # Test Vertex AI
    from google import genai
    client = genai.Client(
        vertexai=True,
        project=proj or os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=os.getenv("GOOGLE_CLOUD_REGION", "europe-west4")
    )
    
    # Simple ping test
    response = client.models.generate_content(
        model="publishers/google/models/gemini-2.5-flash",
        contents="Say 'pong' if you can hear me"
    )
    
    success = bool(response.text or response.candidates)
    print(f"Vertex AI test: {'SUCCESS' if success else 'FAILED'}")
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
        
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
'@

$tempFile = [System.IO.Path]::GetTempFileName() + ".py"
$pythonTest | Out-File -FilePath $tempFile -Encoding UTF8

python $tempFile
$testResult = $LASTEXITCODE
Remove-Item $tempFile -Force

if ($testResult -eq 0) {
    Write-Host "  ✓ Vertex AI connection successful!" -ForegroundColor Green
} else {
    Write-Host "  ✗ Vertex AI test failed!" -ForegroundColor Red
    Write-Host "  Check the error message above" -ForegroundColor Red
}
Write-Host ""

# Step 11: Final instructions
Write-Host "================================================" -ForegroundColor Cyan
if ($testResult -eq 0) {
    Write-Host "SUCCESS! Vertex AI is configured correctly!" -ForegroundColor Green
} else {
    Write-Host "PARTIAL SUCCESS - ADC is set but Vertex test failed" -ForegroundColor Yellow
}
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "CRITICAL: Start your backend from THIS SAME PowerShell window:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  cd backend" -ForegroundColor White
Write-Host "  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000" -ForegroundColor White
Write-Host ""
Write-Host "Then test with: curl http://localhost:8000/__whoami" -ForegroundColor Gray
Write-Host ""
Write-Host "DO NOT close this PowerShell window!" -ForegroundColor Red
Write-Host "DO NOT use a different terminal!" -ForegroundColor Red
Write-Host ""