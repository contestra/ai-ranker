# test_and_start.ps1 - Run AFTER fix_vertex_auth.ps1 in the SAME PowerShell window
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "TESTING VERTEX AI AUTHENTICATION" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# First run the Python test inline
Write-Host "Running Vertex AI strict test..." -ForegroundColor Yellow
Write-Host ""

$pythonTest = @'
import os, sys, google.auth
from google.auth.transport.requests import Request
from google import genai

print("Checking authentication...")
creds, proj = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
creds.refresh(Request())
print(f"  Credential type: {creds.__class__.__name__}")
print(f"  Quota project   : {proj or os.getenv('GOOGLE_CLOUD_PROJECT')}")
print(f"  Impersonated SA : {getattr(creds, 'service_account_email', None)}")

# Fail if not impersonating
if "Impersonated" not in creds.__class__.__name__:
    print("\n✗ ERROR: Not impersonating service account!")
    sys.exit(1)

print("\n✓ Impersonation working correctly!")
print("\nTesting Vertex AI connection...")

try:
    client = genai.Client(
        vertexai=True, 
        project=proj or os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=os.getenv("GOOGLE_CLOUD_REGION","europe-west4")
    )
    r = client.models.generate_content(
        model="publishers/google/models/gemini-2.5-flash", 
        contents="Say 'Vertex working'"
    )
    if r.text or r.candidates:
        print(f"✓ Vertex AI response: {r.text[:50] if hasattr(r, 'text') else 'Got response'}")
        print("\n✓ VERTEX AI IS WORKING CORRECTLY!")
    else:
        print("✗ No response from Vertex AI")
        sys.exit(1)
except Exception as e:
    print(f"✗ Vertex AI failed: {e}")
    sys.exit(1)
'@

# Save to temp file and run
$tempFile = [System.IO.Path]::GetTempFileName() + ".py"
$pythonTest | Out-File -FilePath $tempFile -Encoding UTF8

python $tempFile
$testResult = $LASTEXITCODE

# Clean up temp file
Remove-Item $tempFile -ErrorAction SilentlyContinue

if ($testResult -ne 0) {
    Write-Host ""
    Write-Host "✗ Vertex AI test failed!" -ForegroundColor Red
    Write-Host "Please run fix_vertex_auth.ps1 first" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "SUCCESS! Starting backend..." -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Kill any existing backend process on port 8000
Write-Host "Checking for existing backend on port 8000..." -ForegroundColor Yellow
$existingProcess = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($existingProcess) {
    $pid = $existingProcess.OwningProcess
    Write-Host "  Found process $pid on port 8000, stopping it..." -ForegroundColor Yellow
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}
Write-Host "  ✓ Port 8000 is clear" -ForegroundColor Green
Write-Host ""

# Set environment variables (in case running in new session)
$env:GOOGLE_CLOUD_PROJECT = "contestra-ai"
$env:GOOGLE_CLOUD_REGION = "europe-west4"
$env:CONTESTRA_DISABLE_GEMINI_FALLBACK = "1"
$env:PYTHONUTF8 = "1"

# Start backend
Write-Host "Starting backend with Vertex AI (no fallback)..." -ForegroundColor Green
Write-Host "URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Health check: http://localhost:8000/api/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the backend" -ForegroundColor Yellow
Write-Host ""

cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000