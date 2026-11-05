#!/usr/bin/env bash
set -e

echo "====================================================================="
echo " Agri_watch - Sovereign Indic Agricultural Voice Intelligence Agent"
echo "====================================================================="

# 1. Build React Frontend if not already built
if [ ! -f "frontend/dist/index.html" ]; then
    echo "[*] Building React Frontend SPA..."
    (cd frontend && npm install && npm run build)
fi

# 2. Check virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "[*] Starting FastAPI Server on http://0.0.0.0:8000 ..."
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

echo "[*] Starting LiveKit Voice Worker..."
python voice_engine/livekit_worker.py dev &
WORKER_PID=$!

trap "kill $FASTAPI_PID $WORKER_PID" EXIT INT TERM

echo "[✓] Both services running. Visit http://localhost:8000"
wait
