# PowerShell script to add Google Cloud SDK to PATH

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Adding Google Cloud SDK to System PATH" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Common installation paths for Google Cloud SDK
$possiblePaths = @(
    "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin",
    "$env:ProgramFiles\Google\Cloud SDK\google-cloud-sdk\bin",
    "${env:ProgramFiles(x86)}\Google\Cloud SDK\google-cloud-sdk\bin",
    "$env:USERPROFILE\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin"
)

$gcloudPath = $null
foreach ($path in $possiblePaths) {
    if (Test-Path "$path\gcloud.cmd") {
        $gcloudPath = $path
        Write-Host "Found Google Cloud SDK at: $gcloudPath" -ForegroundColor Green
        break
    }
}

if (-not $gcloudPath) {
    Write-Host "Could not find Google Cloud SDK installation!" -ForegroundColor Red
    Write-Host "Please install it first using:" -ForegroundColor Yellow
    Write-Host "  winget install Google.CloudSDK" -ForegroundColor Cyan
    exit 1
}

# Add to current session PATH
$env:PATH = "$gcloudPath;$env:PATH"
Write-Host "Added to current session PATH" -ForegroundColor Green

# Add to permanent user PATH
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*$gcloudPath*") {
    [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$gcloudPath", "User")
    Write-Host "Added to permanent user PATH" -ForegroundColor Green
    Write-Host ""
    Write-Host "IMPORTANT: Close and reopen PowerShell for permanent PATH changes" -ForegroundColor Yellow
} else {
    Write-Host "Already in permanent PATH" -ForegroundColor Green
}

Write-Host ""
Write-Host "Testing gcloud in current session..." -ForegroundColor Yellow
Write-Host ""

# Test gcloud
try {
    $version = & gcloud --version 2>&1 | Select-Object -First 1
    Write-Host "SUCCESS! gcloud is working: $version" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "Current configuration:" -ForegroundColor Yellow
    & gcloud config list
    
} catch {
    Write-Host "Error running gcloud: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Run these commands to set up ADC:" -ForegroundColor Yellow
Write-Host "   gcloud config set project contestra-ai" -ForegroundColor White
Write-Host "   gcloud auth application-default login" -ForegroundColor White
Write-Host ""
Write-Host "2. Test Vertex AI access:" -ForegroundColor Yellow
Write-Host "   python test_vertex_direct.py" -ForegroundColor White
Write-Host ""