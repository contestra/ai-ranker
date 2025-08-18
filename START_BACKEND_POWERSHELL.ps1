# START_BACKEND_POWERSHELL.ps1
# This script ensures the backend starts with proper Vertex AI authentication
# MUST be run from PowerShell, NOT Git Bash!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BACKEND STARTER FOR VERTEX AI" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify we're in PowerShell
if ($env:SHELL -like "*bash*" -or $env:TERM_PROGRAM -eq "mintty") {
    Write-Host "[ERROR] You're running this from Git Bash or WSL!" -ForegroundColor Red
    Write-Host "This MUST be run from native PowerShell!" -ForegroundColor Red
    Write-Host "Open PowerShell from Start Menu and try again." -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Running in PowerShell" -ForegroundColor Green

# Step 2: Check if ADC exists
$adcPath = "$env:APPDATA\gcloud\application_default_credentials.json"
if (-not (Test-Path $adcPath)) {
    Write-Host "[ERROR] ADC file not found!" -ForegroundColor Red
    Write-Host "Run DIAGNOSE_AND_FIX_VERTEX.ps1 first!" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] ADC file exists" -ForegroundColor Green

# Step 3: Set environment variables
Write-Host ""
Write-Host "Setting environment variables..." -ForegroundColor Yellow
$env:GOOGLE_IMPERSONATE_SERVICE_ACCOUNT = "vertex-runner@contestra-ai.iam.gserviceaccount.com"
$env:GOOGLE_CLOUD_PROJECT = "contestra-ai"
$env:GOOGLE_CLOUD_REGION = "europe-west4"
$env:PYTHONUTF8 = "1"

Write-Host "GOOGLE_IMPERSONATE_SERVICE_ACCOUNT = vertex-runner@contestra-ai.iam.gserviceaccount.com" -ForegroundColor Gray
Write-Host "GOOGLE_CLOUD_PROJECT = contestra-ai" -ForegroundColor Gray
Write-Host "GOOGLE_CLOUD_REGION = europe-west4" -ForegroundColor Gray
Write-Host "PYTHONUTF8 = 1" -ForegroundColor Gray

# Step 4: Quick test
Write-Host ""
Write-Host "Testing Vertex AI authentication..." -ForegroundColor Yellow

$pythonTest = @'
import os, sys
try:
    import google.auth
    from google.auth.transport.requests import Request
    creds, proj = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    if hasattr(creds, 'service_account_email'):
        if creds.service_account_email == "vertex-runner@contestra-ai.iam.gserviceaccount.com":
            print("[OK] Vertex AI authentication working!")
            sys.exit(0)
    print("[WARNING] Not using impersonation")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)
'@

$tempFile = [System.IO.Path]::GetTempFileName() + ".py"
$pythonTest | Out-File -FilePath $tempFile -Encoding UTF8
python $tempFile 2>&1 | Out-Host
$testResult = $LASTEXITCODE
Remove-Item $tempFile -Force

if ($testResult -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Vertex AI authentication not working!" -ForegroundColor Red
    Write-Host "Run DIAGNOSE_AND_FIX_VERTEX.ps1 to fix!" -ForegroundColor Yellow
    exit 1
}

# Step 5: Start backend
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "STARTING BACKEND WITH VERTEX AI" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Starting backend on port 8000..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Change to backend directory and start
Set-Location -Path "D:\OneDrive\CONTESTRA\Microapps\ai-ranker\backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000