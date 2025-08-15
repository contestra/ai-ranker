# PowerShell script to download and run Google Cloud SDK installer

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Google Cloud SDK Installer Download" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Set TLS to 1.2 for secure download
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$url = "https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe"
$installer = "$env:TEMP\GoogleCloudSDKInstaller.exe"

Write-Host "Downloading Google Cloud SDK installer..." -ForegroundColor Yellow
Write-Host "From: $url" -ForegroundColor Gray
Write-Host "To: $installer" -ForegroundColor Gray
Write-Host ""

try {
    # Use Invoke-WebRequest as alternative to WebClient
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
    
    Write-Host "SUCCESS! Download complete." -ForegroundColor Green
    Write-Host ""
    Write-Host "Launching installer..." -ForegroundColor Yellow
    Write-Host ""
    
    # Launch the installer
    Start-Process -FilePath $installer -Wait
    
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "Installation Complete!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "IMPORTANT: You need to restart PowerShell or your computer" -ForegroundColor Yellow
    Write-Host "for the PATH to update and gcloud to be available." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "After restart, run these commands:" -ForegroundColor Cyan
    Write-Host "  gcloud config set project contestra-ai" -ForegroundColor White
    Write-Host "  gcloud auth application-default login" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host "ERROR: Failed to download installer" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Alternative: Download manually from:" -ForegroundColor Yellow
    Write-Host "https://cloud.google.com/sdk/docs/install" -ForegroundColor Cyan
}

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")