@echo off
chcp 65001 >nul
echo =====================================================================
echo  Agri_watch - Sovereign Indic Agricultural Voice Intelligence Agent
echo =====================================================================

REM 1. Check Python virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [!] Virtual environment not found in .venv. Creating one...
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements.txt
)

REM 2. Check if frontend build exists
if not exist "frontend\dist\index.html" (
    echo [*] Building React Frontend SPA...
    cd frontend
    call npm install
    call npm run build
    cd ..
)

echo [*] Starting FastAPI Backend on http://localhost:8000 ...
start "Agri_watch FastAPI Web" cmd /k "chcp 65001 >nul && .venv\Scripts\python.exe -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload"

echo [*] Starting LiveKit Voice Agent Worker...
start "Agri_watch Voice Worker" cmd /k "chcp 65001 >nul && .venv\Scripts\python.exe voice_engine\livekit_worker.py dev"

echo [✓] Both services launched!
echo [✓] Open your browser at: http://localhost:8000

