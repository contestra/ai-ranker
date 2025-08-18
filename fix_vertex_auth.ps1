# fix_vertex_auth.ps1 - Run this in PowerShell directly on Windows
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "VERTEX AI AUTHENTICATION FIX" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Clean up old ADC
Write-Host "Step 1: Cleaning up old ADC file..." -ForegroundColor Yellow
Remove-Item "$env:APPDATA\gcloud\application_default_credentials.json" -ErrorAction SilentlyContinue
Write-Host "  ✓ Old ADC file removed (if existed)" -ForegroundColor Green
Write-Host ""

# Step 2: Set project
Write-Host "Step 2: Setting project to contestra-ai..." -ForegroundColor Yellow
gcloud config set project contestra-ai
Write-Host "  ✓ Project set" -ForegroundColor Green
Write-Host ""

# Step 3: User login
Write-Host "Step 3: User login (browser will open)..." -ForegroundColor Yellow
Write-Host "  Please complete authentication in your browser" -ForegroundColor Cyan
gcloud auth login
Write-Host "  ✓ User login complete" -ForegroundColor Green
Write-Host ""

# Step 4: ADC login
Write-Host "Step 4: Creating Application Default Credentials (browser will open)..." -ForegroundColor Yellow
Write-Host "  Please complete authentication in your browser" -ForegroundColor Cyan
gcloud auth application-default login
Write-Host "  ✓ ADC created" -ForegroundColor Green
Write-Host ""

# Step 5: Set quota project
Write-Host "Step 5: Setting quota project..." -ForegroundColor Yellow
gcloud auth application-default set-quota-project contestra-ai
Write-Host "  ✓ Quota project set" -ForegroundColor Green
Write-Host ""

# Step 6: Verify ADC file exists
Write-Host "Step 6: Verifying ADC file..." -ForegroundColor Yellow
$adcPath = "$env:APPDATA\gcloud\application_default_credentials.json"
if (Test-Path $adcPath) {
    Write-Host "  ✓ ADC file exists at: $adcPath" -ForegroundColor Green
}
else {
    Write-Host "  ✗ ADC file NOT found - something went wrong!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 7: Set impersonation
Write-Host "Step 7: Configuring service account impersonation..." -ForegroundColor Yellow
gcloud config set auth/impersonate_service_account vertex-runner@contestra-ai.iam.gserviceaccount.com
$impersonatedSA = gcloud config get auth/impersonate_service_account
Write-Host "  ✓ Impersonating: $impersonatedSA" -ForegroundColor Green
Write-Host ""

# Step 8: Set environment variables
Write-Host "Step 8: Setting environment variables..." -ForegroundColor Yellow
$env:GOOGLE_CLOUD_PROJECT = "contestra-ai"
$env:GOOGLE_CLOUD_REGION = "europe-west4"
$env:CONTESTRA_DISABLE_GEMINI_FALLBACK = "1"
Write-Host "  ✓ GOOGLE_CLOUD_PROJECT = contestra-ai" -ForegroundColor Green
Write-Host "  ✓ GOOGLE_CLOUD_REGION = europe-west4" -ForegroundColor Green
Write-Host "  ✓ CONTESTRA_DISABLE_GEMINI_FALLBACK = 1 (no fallback)" -ForegroundColor Green
Write-Host ""

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "SETUP COMPLETE!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Run: python test_vertex_strict.py" -ForegroundColor White
Write-Host "2. Start backend: cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000" -ForegroundColor White
Write-Host ""
Write-Host "Both commands should be run in THIS SAME PowerShell window!" -ForegroundColor Cyan