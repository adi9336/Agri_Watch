#!/usr/bin/env bash
# Deploys the website + API to Vercel. The voice worker keeps running locally (run_local.sh).
set -e
cd "$(dirname "$0")/.."
# Ship the latest price snapshot compressed (5 MB instead of 53 MB)
gzip -kf data/mandi_prices_snapshot.csv
vercel deploy --prod --yes
