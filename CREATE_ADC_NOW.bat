@echo off
echo ========================================
echo CREATING APPLICATION DEFAULT CREDENTIALS
echo ========================================
echo.
echo This will open a browser for authentication.
echo Please sign in with your Google account.
echo.

REM Create ADC - this WILL open browser
gcloud auth application-default login

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to create ADC!
    pause
    exit /b 1
)

echo.
echo Setting quota project...
gcloud auth application-default set-quota-project contestra-ai

echo.
echo ========================================
echo ADC CREATED SUCCESSFULLY!
echo ========================================
echo.
echo Verifying ADC exists...
if exist "%APPDATA%\gcloud\application_default_credentials.json" (
    echo SUCCESS: ADC file exists at %APPDATA%\gcloud\application_default_credentials.json
) else (
    echo WARNING: ADC file not found at expected location
)

echo.
echo Testing token...
gcloud auth application-default print-access-token >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo SUCCESS: ADC token is valid!
) else (
    echo WARNING: Could not get token
)

echo.
pause