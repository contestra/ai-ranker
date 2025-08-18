@echo off
setlocal ENABLEDELAYEDEXPANSION

REM ===== Config =====
set "DEFAULT_PROJECT=contestra-ai"
set "SA_EMAIL=vertex-runner@contestra-ai.iam.gserviceaccount.com"
set "REGION=europe-west4"

REM ===== Accept optional project arg =====
if "%~1"=="" (
  set "PROJECT=%DEFAULT_PROJECT%"
) else (
  set "PROJECT=%~1"
)

echo.
echo === Contestra Vertex Auth Fix ===
echo Project: %PROJECT%
echo Region : %REGION%
echo SA     : %SA_EMAIL%
echo.

REM ===== Check gcloud exists =====
where gcloud >nul 2>&1
if errorlevel 1 (
  echo [ERROR] gcloud CLI not found. Install from https://cloud.google.com/sdk
  pause
  exit /b 1
)

REM ===== CRITICAL: Remove brittle CLI impersonation first =====
echo [INFO] Removing CLI-level impersonation (causes reauthentication issues)...
gcloud config unset auth/impersonate_service_account 1>nul 2>nul

REM ===== Clean old ADC if requested =====
echo [INFO] Cleaning old ADC file...
del "%APPDATA%\gcloud\application_default_credentials.json" /f /q 2>nul

REM ===== Point gcloud at the project WITHOUT impersonation =====
echo [INFO] Setting gcloud core/project to %PROJECT% ...
gcloud config set project "%PROJECT%" 1>nul

REM ===== Ensure ADC exists; if missing, open browser =====
echo [INFO] Creating Application Default Credentials (browser will open)...
echo       NOTE: You only need to authenticate ONCE, not twice!
gcloud auth application-default login
if errorlevel 1 (
  echo [ERROR] ADC login failed or was cancelled. Please rerun the script.
  pause
  exit /b 1
)

REM ===== Ensure quota project (prevents 403s on some APIs) =====
echo [INFO] Setting quota project to "%PROJECT%" ...
gcloud auth application-default set-quota-project "%PROJECT%" 1>nul

REM ===== Set persistent env vars for SA impersonation and project/region =====
echo [INFO] Setting persistent environment variables ...
setx GOOGLE_IMPERSONATE_SERVICE_ACCOUNT "%SA_EMAIL%" >nul
setx GOOGLE_CLOUD_PROJECT "%PROJECT%" >nul
setx GOOGLE_CLOUD_REGION "%REGION%" >nul
setx PYTHONUTF8 "1" >nul

echo [INFO] Also setting them for this session ...
set "GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=%SA_EMAIL%"
set "GOOGLE_CLOUD_PROJECT=%PROJECT%"
set "GOOGLE_CLOUD_REGION=%REGION%"
set "PYTHONUTF8=1"

REM ===== Verify token (non-interactive) =====
echo [INFO] Verifying access token via ADC ...
gcloud auth application-default print-access-token >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Token verification failed. ADC may be stale.
  echo        Please run: gcloud auth application-default login
  pause
  exit /b 1
)

echo.
echo =====================================
echo    VERTEX AUTH FIXED SUCCESSFULLY!   
echo =====================================
echo    Project: %PROJECT%
echo    Region : %REGION%
echo    SA Impersonation: %SA_EMAIL%
echo    (via environment variable, not CLI)
echo =====================================
echo.
echo IMPORTANT: 
echo 1. Open a NEW terminal/PowerShell for env vars to take effect
echo 2. Do NOT use 'gcloud config set auth/impersonate_service_account'
echo 3. The backend will use env var impersonation automatically
echo.
echo To start the backend in a NEW terminal:
echo   cd backend
echo   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
echo.
pause

endlocal
exit /b 0