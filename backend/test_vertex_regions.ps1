# Test Vertex AI regions and models
Write-Host "Testing Vertex AI Regions and Models" -ForegroundColor Cyan
Write-Host "=" * 50

# Get token
$TOKEN = & 'C:\Users\leedr\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' auth application-default print-access-token
$PROJ = "contestra-ai"

# Test EU region
Write-Host "`nTesting europe-west4..." -ForegroundColor Yellow
$LOC = "europe-west4"
$URL = "https://${LOC}-aiplatform.googleapis.com/v1/projects/${PROJ}/locations/${LOC}/publishers/google/models"

try {
    $response = Invoke-RestMethod -Headers @{Authorization="Bearer $TOKEN"} -Uri $URL -ErrorAction Stop
    Write-Host "SUCCESS! Found models in $LOC`:" -ForegroundColor Green
    $response.models | Select name, displayName | Format-Table -Auto
} catch {
    Write-Host "ERROR in $LOC`: $_" -ForegroundColor Red
}

# Test US region
Write-Host "`nTesting us-central1..." -ForegroundColor Yellow
$LOC = "us-central1"
$URL = "https://${LOC}-aiplatform.googleapis.com/v1/projects/${PROJ}/locations/${LOC}/publishers/google/models"

try {
    $response = Invoke-RestMethod -Headers @{Authorization="Bearer $TOKEN"} -Uri $URL -ErrorAction Stop
    Write-Host "SUCCESS! Found models in $LOC`:" -ForegroundColor Green
    $response.models | Select name, displayName | Format-Table -Auto
} catch {
    Write-Host "ERROR in $LOC`: $_" -ForegroundColor Red
}