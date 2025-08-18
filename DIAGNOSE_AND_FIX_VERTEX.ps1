# DIAGNOSE_AND_FIX_VERTEX.ps1
# This script will diagnose and try to fix the Vertex AI authentication issue

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "VERTEX AI AUTHENTICATION DIAGNOSTIC" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Step 1: Check where we're running
Write-Host "STEP 1: Environment Check" -ForegroundColor Yellow
Write-Host "-------------------------" -ForegroundColor Gray
Write-Host "Current Shell: $($PSVersionTable.PSVersion)" -ForegroundColor Gray
Write-Host "Current User: $(whoami)" -ForegroundColor Gray
Write-Host "Current Directory: $(Get-Location)" -ForegroundColor Gray

# Check if running in correct shell
if ($env:SHELL -like "*bash*" -or $env:TERM_PROGRAM -eq "mintty") {
    Write-Host "`n[ERROR] You're running this from Git Bash or WSL!" -ForegroundColor Red
    Write-Host "This MUST be run from native PowerShell!" -ForegroundColor Red
    Write-Host "Open PowerShell from Start Menu and try again." -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Running in PowerShell" -ForegroundColor Green

# Step 2: Check gcloud installation
Write-Host "`nSTEP 2: gcloud Installation Check" -ForegroundColor Yellow
Write-Host "----------------------------------" -ForegroundColor Gray
$gcloudPath = where.exe gcloud 2>$null
if (-not $gcloudPath) {
    Write-Host "[ERROR] gcloud not found!" -ForegroundColor Red
    Write-Host "Install from: https://cloud.google.com/sdk" -ForegroundColor Yellow
    exit 1
}
Write-Host "gcloud location: $gcloudPath" -ForegroundColor Gray
if ($gcloudPath -like "*wsl*") {
    Write-Host "[ERROR] Using WSL gcloud! Use Windows gcloud instead." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Using Windows gcloud" -ForegroundColor Green

# Step 3: Check current authentication
Write-Host "`nSTEP 3: Current Authentication Status" -ForegroundColor Yellow
Write-Host "-------------------------------------" -ForegroundColor Gray
$currentAccount = gcloud config get account 2>$null
$currentProject = gcloud config get project 2>$null
Write-Host "Active Account: $currentAccount" -ForegroundColor Gray
Write-Host "Active Project: $currentProject" -ForegroundColor Gray

if ($currentAccount -ne "l@contestra.com") {
    Write-Host "[WARNING] Not using correct account" -ForegroundColor Yellow
    Write-Host "Setting account to l@contestra.com..." -ForegroundColor Cyan
    gcloud config set account l@contestra.com
}

if ($currentProject -ne "contestra-ai") {
    Write-Host "[WARNING] Not using correct project" -ForegroundColor Yellow
    Write-Host "Setting project to contestra-ai..." -ForegroundColor Cyan
    gcloud config set project contestra-ai
}

# Step 4: Check ADC file
Write-Host "`nSTEP 4: ADC File Status" -ForegroundColor Yellow
Write-Host "-----------------------" -ForegroundColor Gray
$adcPath = "C:\Users\leedr\AppData\Roaming\gcloud\application_default_credentials.json"
$adcExists = Test-Path $adcPath

if ($adcExists) {
    Write-Host "[OK] ADC file exists at: $adcPath" -ForegroundColor Green
    $adcInfo = Get-Item $adcPath
    Write-Host "Last Modified: $($adcInfo.LastWriteTime)" -ForegroundColor Gray
    
    # Check if it's too old (>1 hour)
    $age = (Get-Date) - $adcInfo.LastWriteTime
    if ($age.TotalHours -gt 1) {
        Write-Host "[WARNING] ADC file is $([int]$age.TotalHours) hours old" -ForegroundColor Yellow
        $refreshADC = $true
    } else {
        Write-Host "[OK] ADC file is recent" -ForegroundColor Green
        $refreshADC = $false
    }
} else {
    Write-Host "[ERROR] ADC file does NOT exist!" -ForegroundColor Red
    $refreshADC = $true
}

# Step 5: Check TokenCreator permission
Write-Host "`nSTEP 5: TokenCreator Permission Check" -ForegroundColor Yellow
Write-Host "-------------------------------------" -ForegroundColor Gray
$SA = "vertex-runner@contestra-ai.iam.gserviceaccount.com"
Write-Host "Testing impersonation of: $SA" -ForegroundColor Gray

$testToken = gcloud auth print-access-token --impersonate-service-account=$SA 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] TokenCreator permission is working" -ForegroundColor Green
} else {
    Write-Host "[ERROR] TokenCreator permission missing or not working!" -ForegroundColor Red
    Write-Host "Error: $testToken" -ForegroundColor Gray
    
    Write-Host "`nAttempting to grant permission..." -ForegroundColor Cyan
    gcloud iam service-accounts add-iam-policy-binding $SA `
        --role="roles/iam.serviceAccountTokenCreator" `
        --member="user:$currentAccount" `
        --project contestra-ai
}

# Step 6: Fix ADC if needed
if ($refreshADC) {
    Write-Host "`nSTEP 6: Creating/Refreshing ADC" -ForegroundColor Yellow
    Write-Host "--------------------------------" -ForegroundColor Gray
    Write-Host "[ACTION REQUIRED] Browser will open for authentication" -ForegroundColor Cyan
    Write-Host "Please complete the authentication in the browser." -ForegroundColor Cyan
    Write-Host "`nPress Enter to continue..." -ForegroundColor Yellow
    Read-Host
    
    # Remove old ADC
    if (Test-Path $adcPath) {
        Remove-Item $adcPath -Force
        Write-Host "Removed old ADC file" -ForegroundColor Gray
    }
    
    # Create new ADC
    gcloud auth application-default login
    
    # Verify it was created
    if (Test-Path $adcPath) {
        Write-Host "[OK] ADC file created successfully!" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] ADC file was NOT created!" -ForegroundColor Red
        Write-Host "This usually means:" -ForegroundColor Yellow
        Write-Host "1. You cancelled the browser authentication" -ForegroundColor Yellow
        Write-Host "2. You're running from Git Bash/WSL instead of PowerShell" -ForegroundColor Yellow
        Write-Host "3. Browser was blocked by security software" -ForegroundColor Yellow
        exit 1
    }
    
    # Set quota project
    Write-Host "Setting quota project..." -ForegroundColor Cyan
    gcloud auth application-default set-quota-project contestra-ai
    Write-Host "[OK] Quota project set" -ForegroundColor Green
}

# Step 7: Set environment variables
Write-Host "`nSTEP 7: Setting Environment Variables" -ForegroundColor Yellow
Write-Host "-------------------------------------" -ForegroundColor Gray
$env:GOOGLE_IMPERSONATE_SERVICE_ACCOUNT = $SA
$env:GOOGLE_CLOUD_PROJECT = "contestra-ai"
$env:GOOGLE_CLOUD_REGION = "europe-west4"
$env:PYTHONUTF8 = "1"

Write-Host "GOOGLE_IMPERSONATE_SERVICE_ACCOUNT = $SA" -ForegroundColor Gray
Write-Host "GOOGLE_CLOUD_PROJECT = contestra-ai" -ForegroundColor Gray
Write-Host "GOOGLE_CLOUD_REGION = europe-west4" -ForegroundColor Gray
Write-Host "[OK] Environment variables set for this session" -ForegroundColor Green

# Step 8: Test Vertex AI
Write-Host "`nSTEP 8: Testing Vertex AI Connection" -ForegroundColor Yellow
Write-Host "------------------------------------" -ForegroundColor Gray

$pythonTest = @'
import os, sys
try:
    import google.auth
    from google.auth.transport.requests import Request
    
    creds, proj = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    
    print(f"Credential type: {creds.__class__.__name__}")
    
    if hasattr(creds, 'service_account_email'):
        print(f"Service account: {creds.service_account_email}")
        if creds.service_account_email == "vertex-runner@contestra-ai.iam.gserviceaccount.com":
            print("[OK] Impersonation working correctly")
        else:
            print(f"[ERROR] Wrong service account: {creds.service_account_email}")
            sys.exit(1)
    elif "Impersonated" in creds.__class__.__name__:
        print("[OK] Using impersonated credentials")
    else:
        print("[WARNING] Not using impersonation - may fall back to direct API")
    
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
        print("[OK] Vertex AI is working!")
        sys.exit(0)
    else:
        print("[ERROR] Vertex AI test failed!")
        sys.exit(1)
        
except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)
'@

$tempFile = [System.IO.Path]::GetTempFileName() + ".py"
$pythonTest | Out-File -FilePath $tempFile -Encoding UTF8
python $tempFile 2>&1
$testResult = $LASTEXITCODE
Remove-Item $tempFile -Force

# Final summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "DIAGNOSTIC COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($testResult -eq 0) {
    Write-Host "`n✅ VERTEX AI IS WORKING!" -ForegroundColor Green
    Write-Host "✅ NO FALLBACK TO DIRECT API!" -ForegroundColor Green
    Write-Host "`nNEXT STEPS:" -ForegroundColor Yellow
    Write-Host "1. Stop the current backend (Ctrl+C)" -ForegroundColor White
    Write-Host "2. Start it from THIS PowerShell window:" -ForegroundColor White
    Write-Host "   cd backend" -ForegroundColor Gray
    Write-Host "   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000" -ForegroundColor Gray
} else {
    Write-Host "`n❌ VERTEX AI IS NOT WORKING!" -ForegroundColor Red
    Write-Host "The system is falling back to direct API (NOT ACCEPTABLE)" -ForegroundColor Red
    Write-Host "`nPOSSIBLE ISSUES:" -ForegroundColor Yellow
    Write-Host "1. ADC file not created (check Step 4 above)" -ForegroundColor White
    Write-Host "2. TokenCreator permission missing (check Step 5 above)" -ForegroundColor White
    Write-Host "3. Running from wrong shell (must be PowerShell)" -ForegroundColor White
    Write-Host "4. Environment variables not set" -ForegroundColor White
}

Write-Host "`nIMPORTANT:" -ForegroundColor Yellow
Write-Host "- You MUST run the backend from THIS SAME PowerShell window" -ForegroundColor Red
Write-Host "- Do NOT use a different terminal or the env vars won't be set" -ForegroundColor Red
Write-Host ""