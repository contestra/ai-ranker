@echo off
echo ==================================================
echo FIXING ADC TO USE CONTESTRA-AI PROJECT
echo ==================================================
echo.
echo Setting project to contestra-ai...
gcloud config set project contestra-ai
echo.
echo Re-authenticating ADC (browser will open)...
echo IMPORTANT: Select your Google account and click Allow
echo.
gcloud auth application-default login
echo.
echo ==================================================
echo COMPLETE! ADC should now use contestra-ai
echo ==================================================
echo.
echo Now run: python test_vertex_final.py
echo.
pause