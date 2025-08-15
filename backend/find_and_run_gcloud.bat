@echo off
echo Searching for gcloud installation...
echo.

REM Check common installation paths
set GCLOUD_PATH=

if exist "%ProgramFiles%\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" (
    set GCLOUD_PATH=%ProgramFiles%\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd
    goto found
)

if exist "%ProgramFiles(x86)%\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" (
    set GCLOUD_PATH=%ProgramFiles(x86)%\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd
    goto found
)

if exist "%LocalAppData%\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" (
    set GCLOUD_PATH=%LocalAppData%\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd
    goto found
)

REM Try to find it using where command
for /f "delims=" %%i in ('where gcloud 2^>nul') do (
    set GCLOUD_PATH=%%i
    goto found
)

echo ERROR: Could not find gcloud installation!
echo.
echo Please restart your computer to update PATH, or reinstall Google Cloud SDK
echo.
pause
exit /b 1

:found
echo Found gcloud at: %GCLOUD_PATH%
echo.
echo Setting project to contestra-ai...
"%GCLOUD_PATH%" config set project contestra-ai
echo.
echo Authenticating ADC (browser will open)...
echo IMPORTANT: Select your Google account and click Allow
echo.
"%GCLOUD_PATH%" auth application-default login
echo.
echo ==========================================
echo COMPLETE! ADC should now use contestra-ai
echo ==========================================
echo.
pause