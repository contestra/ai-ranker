# PowerShell script to fix ADC project

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Fixing ADC to use contestra-ai project" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Set the project
Write-Host "`nStep 1: Setting default project to contestra-ai..." -ForegroundColor Yellow
gcloud config set project contestra-ai

# Show current config
Write-Host "`nStep 2: Current configuration:" -ForegroundColor Yellow
gcloud config list

# Re-authenticate ADC
Write-Host "`nStep 3: Re-authenticating ADC (browser will open)..." -ForegroundColor Yellow
Write-Host "IMPORTANT: Select your Google account and approve access" -ForegroundColor Green
gcloud auth application-default login

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "ADC re-authentication complete!" -ForegroundColor Green
Write-Host "Now test with: python test_vertex_after_iam.py" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Cyan