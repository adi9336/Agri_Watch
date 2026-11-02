@echo off
REM Agri_watch - Automated Daily Mandi Price Sync Runner for Windows Task Scheduler
cd /d "%~dp0\.."
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe scripts\daily_mandi_sync.py %*
) else (
    python scripts\daily_mandi_sync.py %*
)
