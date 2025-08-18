@echo off
cd backend
set PYTHONUTF8=1
set GOOGLE_CLOUD_PROJECT=contestra-ai
set GOOGLE_CLOUD_REGION=europe-west4
set CONTESTRA_DISABLE_GEMINI_FALLBACK=1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
