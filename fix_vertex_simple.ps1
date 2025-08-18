# Simple Vertex AI Authentication Fix
Write-Host "VERTEX AI AUTHENTICATION FIX" -ForegroundColor Cyan
Write-Host ""

# Clean up old ADC
Remove-Item "$env:APPDATA\gcloud\application_default_credentials.json" -ErrorAction SilentlyContinue
Write-Host "Cleaned old ADC file" -ForegroundColor Green

# Set project
gcloud config set project contestra-ai
Write-Host "Set project to contestra-ai" -ForegroundColor Green

# User login
Write-Host "Please authenticate in browser for user login..." -ForegroundColor Yellow
gcloud auth login

# ADC login
Write-Host "Please authenticate in browser for ADC..." -ForegroundColor Yellow
gcloud auth application-default login

# Set quota project
gcloud auth application-default set-quota-project contestra-ai
Write-Host "Set quota project" -ForegroundColor Green

# Set impersonation
gcloud config set auth/impersonate_service_account vertex-runner@contestra-ai.iam.gserviceaccount.com
Write-Host "Set impersonation" -ForegroundColor Green

# Set environment variables
$env:GOOGLE_CLOUD_PROJECT = "contestra-ai"
$env:GOOGLE_CLOUD_REGION = "europe-west4"
$env:CONTESTRA_DISABLE_GEMINI_FALLBACK = "1"
$env:PYTHONUTF8 = "1"

Write-Host ""
Write-Host "SETUP COMPLETE!" -ForegroundColor Green
Write-Host "Now run: powershell -File test_and_start.ps1" -ForegroundColor Yellow