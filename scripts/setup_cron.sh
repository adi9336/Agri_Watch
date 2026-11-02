#!/usr/bin/env bash
# Agri_watch - Linux Cron Setup for Mandi Ingestion
# Runs daily at 20:00 (8:00 PM IST)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_EXEC="$DIR/.venv/bin/python"
if [ ! -f "$PYTHON_EXEC" ]; then
    PYTHON_EXEC="python3"
fi

CRON_CMD="0 20 * * * cd $DIR && $PYTHON_EXEC scripts/daily_mandi_sync.py >> logs/daily_sync.log 2>&1"
(crontab -l 2>/dev/null | grep -F -v "daily_mandi_sync.py"; echo "$CRON_CMD") | crontab -
echo "[+] Mandi Daily Sync Cron successfully configured:"
echo "    $CRON_CMD"
