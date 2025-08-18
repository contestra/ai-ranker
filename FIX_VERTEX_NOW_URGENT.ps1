# FIX_VERTEX_NOW_URGENT.ps1
# RUN THIS IN POWERSHELL TO FIX VERTEX AI IMMEDIATELY

Write-Host "========================================" -ForegroundColor Red
Write-Host "URGENT: VERTEX AI IS OFFLINE" -ForegroundColor Red
Write-Host "FALLING BACK TO DIRECT API IS NOT ACCEPTABLE" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""

# Step 1: ADC is missing - this is the problem!
Write-Host "PROBLEM IDENTIFIED: ADC file is missing!" -ForegroundColor Yellow
Write-Host "Location checked: $env:APPDATA\gcloud\application_default_credentials.json" -ForegroundColor Gray
Write-Host ""

# Step 2: Create ADC (REQUIRES BROWSER)
Write-Host "FIXING: Creating Application Default Credentials..." -ForegroundColor Green
Write-Host "A browser window will open - COMPLETE THE AUTHENTICATION!" -ForegroundColor Cyan
Write-Host ""

# Remove old ADC if it exists elsewhere
Remove-Item "$env:APPDATA\gcloud\application_default_credentials.json" -ErrorAction SilentlyContinue

# Create new ADC - THIS IS THE FIX
gcloud auth application-default login

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ADC creation failed!" -ForegroundColor Red
    Write-Host "Cannot proceed without ADC!" -ForegroundColor Red
    exit 1
}

# Step 3: Set quota project
Write-Host ""
Write-Host "Setting quota project..." -ForegroundColor Yellow
gcloud auth application-default set-quota-project contestra-ai

# Step 4: Verify ADC exists
$adcPath = "$env:APPDATA\gcloud\application_default_credentials.json"
if (Test-Path $adcPath) {
    Write-Host ""
    Write-Host "SUCCESS: ADC file created at $adcPath" -ForegroundColor Green
} else {
    Write-Host "ERROR: ADC file still missing!" -ForegroundColor Red
    Write-Host "This means authentication happened in wrong context!" -ForegroundColor Red
    Write-Host "Make sure you're in PowerShell, not Git Bash!" -ForegroundColor Red
    exit 1
}

# Step 5: Set environment variables for this session
Write-Host ""
Write-Host "Setting environment variables for impersonation..." -ForegroundColor Yellow
$env:GOOGLE_IMPERSONATE_SERVICE_ACCOUNT = "vertex-runner@contestra-ai.iam.gserviceaccount.com"
$env:GOOGLE_CLOUD_PROJECT = "contestra-ai"
$env:GOOGLE_CLOUD_REGION = "europe-west4"
$env:PYTHONUTF8 = "1"

# Also set persistently
setx GOOGLE_IMPERSONATE_SERVICE_ACCOUNT "vertex-runner@contestra-ai.iam.gserviceaccount.com" >$null
setx GOOGLE_CLOUD_PROJECT "contestra-ai" >$null
setx GOOGLE_CLOUD_REGION "europe-west4" >$null
setx PYTHONUTF8 "1" >$null

Write-Host "✓ Environment variables set" -ForegroundColor Green

# Step 6: Test Vertex AI connection
Write-Host ""
Write-Host "Testing Vertex AI connection..." -ForegroundColor Yellow

$pythonTest = @'
import os, sys
try:
    import google.auth
    from google.auth.transport.requests import Request
    
    # Get credentials
    creds, proj = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    
    print(f"Credential type: {creds.__class__.__name__}")
    print(f"Service account: {getattr(creds, 'service_account_email', 'NOT IMPERSONATING')}")
    
    # Test Vertex
    from google import genai
    client = genai.Client(
        vertexai=True,
        project="contestra-ai",
        location="europe-west4"
    )
    response = client.models.generate_content(
        model="publishers/google/models/gemini-2.5-flash",
        contents="Say 'pong'"
    )
    if response.text or response.candidates:
        print("VERTEX AI: WORKING!")
        sys.exit(0)
    else:
        print("VERTEX AI: FAILED!")
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

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($testResult -eq 0) {
    Write-Host "✓ VERTEX AI IS NOW ONLINE!" -ForegroundColor Green
    Write-Host "✓ NO MORE FALLBACK TO DIRECT API!" -ForegroundColor Green
} else {
    Write-Host "✗ VERTEX AI TEST FAILED" -ForegroundColor Red
    Write-Host "Check error message above" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT STEP: Restart the backend from THIS PowerShell window:" -ForegroundColor Yellow
Write-Host "cd backend" -ForegroundColor White
Write-Host "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000" -ForegroundColor White
Write-Host ""
Write-Host "IMPORTANT: The backend MUST be started from THIS SAME PowerShell" -ForegroundColor Red
Write-Host "where the environment variables are set!" -ForegroundColor Red