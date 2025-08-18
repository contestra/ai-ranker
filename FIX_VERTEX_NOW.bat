@echo off
echo ========================================
echo FIXING VERTEX AI AUTHENTICATION
echo ========================================
echo.

REM Delete old ADC
del "%APPDATA%\gcloud\application_default_credentials.json" /f /q 2>nul
echo Cleaned old ADC

REM Set project
gcloud config set project contestra-ai
echo Set project: contestra-ai

REM Set impersonation
gcloud config set auth/impersonate_service_account vertex-runner@contestra-ai.iam.gserviceaccount.com
echo Set impersonation: vertex-runner@contestra-ai.iam.gserviceaccount.com

echo.
echo Now running ADC login - PLEASE AUTHENTICATE IN BROWSER
echo.
gcloud auth application-default login

echo.
echo Setting quota project...
gcloud auth application-default set-quota-project contestra-ai

echo.
echo ========================================
echo SETUP COMPLETE!
echo ========================================
echo.
echo Now run: START_BACKEND_VERTEX.bat
echo.
pause