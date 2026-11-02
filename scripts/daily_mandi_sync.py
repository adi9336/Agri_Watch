"""
Agri_watch - Automated Daily Mandi Price Ingestion & Sync Engine
Pulls finalized daily APMC wholesale rates from api.data.gov.in,
deduplicates against the local historical snapshot, and appends new records.

Usage:
    python scripts/daily_mandi_sync.py                  # Syncs today's records
    python scripts/daily_mandi_sync.py --date 02/11/2026 # Syncs specific date
    python scripts/daily_mandi_sync.py --days 3         # Backfill past 3 days
    python scripts/daily_mandi_sync.py --dry-run        # Preview without writing
"""

import os
import sys
import csv
import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, List, Set, Tuple, Optional

sys.stdout.reconfigure(encoding='utf-8')

# Ensure parent directory is in Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from mandi_tracker import MandiPriceService, normalize_date

logger = logging.getLogger("agriwatch.sync")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

CSV_PATH = os.path.join(PARENT_DIR, "data", "mandi_prices_snapshot.csv")
FIELDNAMES = [
    "state", "district", "market", "commodity", "variety",
    "grade", "arrival_date", "min_price", "max_price", "modal_price", "pulled_on"
]


def load_existing_keys_for_dates(target_dates: Set[str]) -> Set[Tuple]:
    """
    Scans the local historical CSV and returns unique compound keys
    matching target dates for fast O(1) deduplication.
    """
    existing_keys = set()
    if not os.path.exists(CSV_PATH):
        return existing_keys

    with open(CSV_PATH, mode="r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            arr_date = (row.get("arrival_date") or "").strip()
            if arr_date in target_dates:
                key = (
                    arr_date,
                    (row.get("state") or "").strip().lower(),
                    (row.get("district") or "").strip().lower(),
                    (row.get("market") or "").strip().lower(),
                    (row.get("commodity") or "").strip().lower(),
                    (row.get("variety") or "").strip().lower()
                )
                existing_keys.add(key)

    return existing_keys


def fetch_records_for_date(service: MandiPriceService, target_date: str, page_size: int = 1000, max_records: int = 25000) -> List[Dict]:
    """
    Fetches all APMC records for a given date across India from data.gov.in using pagination.
    Applies polite rate limiting (150ms sleep) to prevent API throttling.
    """
    import time
    all_records = []
    offset = 0

    while offset < max_records:
        params = {
            "limit": str(page_size),
            "offset": str(offset),
            "filters[arrival_date]": target_date
        }
        try:
            records = service._query_api(params, timeout=25)
            if not records:
                break
            all_records.extend(records)
            logger.info(f"[*] Fetched page: offset={offset}, count={len(records)} for {target_date} (Total: {len(all_records)})")
            if len(records) < page_size:
                break
            offset += page_size
            time.sleep(0.15)  # Polite pause for data.gov.in rate limits
        except Exception as e:
            logger.error(f"[!] API query error at offset={offset} for {target_date}: {e}")
            break

    return all_records


def sync_mandi_data(
    target_date: Optional[str] = None,
    days: int = 1,
    dry_run: bool = False,
    max_records_per_date: int = 25000
) -> Dict[str, Any]:
    """
    Main programmatic sync method.
    Pulls data, deduplicates, and appends to the historical database.
    """
    service = MandiPriceService()
    if not service.api_key:
        msg = "No DATA_GOV_IN_KEY found in environment or .env file."
        logger.error(f"[!] {msg}")
        return {"status": "error", "message": msg}

    # Determine dates to sync
    dates_to_sync = []
    if target_date:
        norm_d = normalize_date(target_date)
        if norm_d:
            dates_to_sync.append(norm_d)
    else:
        # Default: today and past N days
        now = datetime.now()
        for i in range(days):
            d_str = (now - timedelta(days=i)).strftime("%d/%m/%Y")
            dates_to_sync.append(d_str)

    target_date_set = set(dates_to_sync)
    logger.info(f"[*] Starting Mandi Price Sync for dates: {dates_to_sync}")

    # Load existing compound keys for deduplication
    existing_keys = load_existing_keys_for_dates(target_date_set)
    logger.info(f"[*] Loaded {len(existing_keys)} existing unique keys for target date(s).")

    total_fetched = 0
    new_records_to_append = []
    pulled_on_date = datetime.now().strftime("%Y-%m-%d")

    for d in dates_to_sync:
        recs = fetch_records_for_date(service, d, max_records=max_records_per_date)
        total_fetched += len(recs)

        for r in recs:
            arr_date = (r.get("arrival_date") or "").strip()
            state = (r.get("state") or "").strip()
            district = (r.get("district") or "").strip()
            market = (r.get("market") or "").strip()
            commodity = (r.get("commodity") or "").strip()
            variety = (r.get("variety") or "").strip()

            key = (arr_date, state.lower(), district.lower(), market.lower(), commodity.lower(), variety.lower())

            if key not in existing_keys:
                existing_keys.add(key)
                new_row = {
                    "state": state,
                    "district": district,
                    "market": market,
                    "commodity": commodity,
                    "variety": variety,
                    "grade": (r.get("grade") or "FAQ").strip(),
                    "arrival_date": arr_date,
                    "min_price": str(r.get("min_price", 0)),
                    "max_price": str(r.get("max_price", 0)),
                    "modal_price": str(r.get("modal_price", 0)),
                    "pulled_on": pulled_on_date
                }
                new_records_to_append.append(new_row)

    logger.info(f"[+] Total records fetched: {total_fetched} | New unique records to append: {len(new_records_to_append)}")

    if dry_run:
        logger.info("[*] DRY RUN: Skipping write to disk.")
        return {
            "status": "dry_run",
            "dates": dates_to_sync,
            "total_fetched": total_fetched,
            "new_records": len(new_records_to_append)
        }

    # Append new records to CSV
    if new_records_to_append:
        file_exists = os.path.exists(CSV_PATH)
        mode = "a" if file_exists else "w"
        with open(CSV_PATH, mode=mode, encoding="utf-8", newline="", errors="ignore") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            if not file_exists:
                writer.writeheader()
            writer.writerows(new_records_to_append)

        logger.info(f"[+] Successfully wrote {len(new_records_to_append)} new records to {CSV_PATH}")

    return {
        "status": "success",
        "dates": dates_to_sync,
        "total_fetched": total_fetched,
        "new_records_added": len(new_records_to_append)
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daily APMC Mandi Price Sync Engine")
    parser.add_argument("--date", type=str, help="Specific arrival date to sync (DD/MM/YYYY)")
    parser.add_argument("--days", type=int, default=1, help="Number of past days to sync (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Preview sync results without modifying CSV")
    args = parser.parse_args()

    result = sync_mandi_data(target_date=args.date, days=args.days, dry_run=args.dry_run)
    print("\n[+] Sync Result Summary:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
