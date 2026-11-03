"""
Agri_watch - Mandi Price Fetcher
Supports:
1. Real-time Live API (data.gov.in) for Today's live prices
2. Historical / Old Date queries (via local Agmarknet database)
3. Date filtering (--date DD/MM/YYYY or YYYY-MM-DD)
"""

import os
import sys
import json
import csv
import io
import urllib.request
import urllib.parse
from datetime import datetime
from typing import List, Dict, Optional, Tuple

sys.stdout.reconfigure(encoding='utf-8')

DATA_GOV_IN_RESOURCE_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
SNAPSHOT_DATA_URL = "https://raw.githubusercontent.com/herrrickshaw/agri-commodity-tracker/main/data/mandi_prices_snapshot.csv"
LOCAL_CACHE_PATH = os.path.join(os.path.dirname(__file__), "data", "mandi_prices_snapshot.csv")
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")


def load_env() -> Dict[str, str]:
    """Parse local .env file if present."""
    env_vars = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip('"').strip("'")
    return env_vars


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """Normalize input date string to DD/MM/YYYY format used by Agmarknet."""
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            pass
    return date_str


def find_nearest_date(target_str: Optional[str], available_dates: List[str]) -> Optional[str]:
    """Finds the chronologically nearest date from a list of available dates."""
    if not target_str or not available_dates:
        return None
    norm_t = normalize_date(target_str)
    if not norm_t:
        return None
    try:
        target_dt = datetime.strptime(norm_t, "%d/%m/%Y")
    except ValueError:
        return None

    parsed = []
    for d in available_dates:
        try:
            dt = datetime.strptime(d.strip(), "%d/%m/%Y")
            parsed.append((dt, d))
        except ValueError:
            continue

    if not parsed:
        return None

    # Prioritize dates on or before target_dt, sorted by smallest time difference
    parsed.sort(key=lambda x: (x[0] > target_dt, abs((x[0] - target_dt).total_seconds())))
    return parsed[0][1]


class MandiPriceService:
    def __init__(self, api_key: Optional[str] = None):
        env_vars = load_env()
        self.api_key = api_key or os.getenv("DATA_GOV_IN_KEY") or env_vars.get("API_KEY") or env_vars.get("DATA_GOV_IN_KEY")

    def ensure_local_cache(self) -> str:
        """Ensures the full Agmarknet snapshot dataset is cached locally."""
        if os.path.exists(LOCAL_CACHE_PATH) and os.path.getsize(LOCAL_CACHE_PATH) > 10 * 1024 * 1024:
            return LOCAL_CACHE_PATH

        os.makedirs(os.path.dirname(LOCAL_CACHE_PATH), exist_ok=True)
        print("[*] Downloading Agmarknet dataset snapshot (50MB)...")
        urllib.request.urlretrieve(SNAPSHOT_DATA_URL, LOCAL_CACHE_PATH)
        return LOCAL_CACHE_PATH

    def _query_api(self, params: Dict[str, str], timeout: int = 20) -> List[Dict]:
        """Helper to query data.gov.in API."""
        query_params = {
            "api-key": self.api_key,
            "format": "json",
            **params
        }
        url = f"{DATA_GOV_IN_RESOURCE_URL}?{urllib.parse.urlencode(query_params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "AgriWatch/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("records", [])

    def fetch_live_prices(
        self,
        state: Optional[str] = None,
        district: Optional[str] = None,
        crop: Optional[str] = None,
        market: Optional[str] = None
    ) -> Tuple[List[Dict], List[Dict], Optional[str]]:
        """Fetches today's live prices from data.gov.in."""
        if not self.api_key:
            raise ValueError("No API key found in .env or environment variables.")

        direct_matches = []
        state_matches = []
        reporting_date = None
        crop_lower = crop.lower() if crop else ""

        if district:
            params = {"limit": "100"}
            if state:
                params["filters[state.keyword]"] = state
            params["filters[district]"] = district
            try:
                dist_records = self._query_api(params, timeout=12)
                if dist_records:
                    reporting_date = dist_records[0].get("arrival_date")
                    for r in dist_records:
                        comm = r.get("commodity", "")
                        if not crop or crop_lower in comm.lower():
                            direct_matches.append(r)
            except Exception as e:
                print(f"[!] District query notice: {e}")

        # If specific market was requested, prioritize exact market matches
        if market and direct_matches:
            m_lower = market.lower()
            m_matched = [r for r in direct_matches if m_lower in (r.get("market") or "").lower()]
            if m_matched:
                direct_matches = m_matched

        state_params = {"limit": "100"}
        if state:
            state_params["filters[state.keyword]"] = state
        
        try:
            state_records = self._query_api(state_params, timeout=18)
            if state_records and not reporting_date:
                reporting_date = state_records[0].get("arrival_date")

            for r in state_records:
                r_dist = r.get("district", "")
                r_comm = r.get("commodity", "")
                matches_crop = not crop or (crop_lower in r_comm.lower())
                matches_dist = not district or (district.lower() in r_dist.lower())

                if matches_crop and matches_dist and not direct_matches:
                    direct_matches.append(r)
                elif matches_crop and not matches_dist:
                    state_matches.append(r)
        except Exception as e:
            if not direct_matches:
                raise e

        return direct_matches, state_matches, reporting_date

    def fetch_historical(
        self,
        state: Optional[str] = None,
        district: Optional[str] = None,
        crop: Optional[str] = None,
        target_date: Optional[str] = None,
        market: Optional[str] = None,
        max_results: int = 25
    ) -> Tuple[List[Dict], List[str]]:
        """
        Searches historical records from local Agmarknet database.
        Allows filtering by specific date (target_date in DD/MM/YYYY) and optional specific market.
        """
        cache_file = self.ensure_local_cache()
        results = []
        market_filtered_results = []
        all_dates_found = set()
        target_market_clean = market.strip().lower() if market else ""

        with open(cache_file, mode="r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                r_state = row.get("state", "").strip()
                r_district = row.get("district", "").strip()
                r_market = row.get("market", "").strip()
                r_comm = row.get("commodity", "").strip()
                r_date = row.get("arrival_date", "").strip()

                r_dist_clean = r_district.strip().lower()
                target_dist_clean = district.strip().lower() if district else ""
                state_match = not state or (state.lower() in r_state.lower())
                district_match = not district or (r_dist_clean == target_dist_clean) or (target_dist_clean in r_dist_clean.split())
                crop_match = not crop or (crop.lower() in r_comm.lower())

                if state_match and district_match and crop_match:
                    if r_date:
                        all_dates_found.add(r_date)

                    matches_date = not target_date or (r_date == target_date)
                    if matches_date:
                        results.append(row)
                        if target_market_clean and (target_market_clean in r_market.lower()):
                            market_filtered_results.append(row)

        # If specific market matches were found, prioritize them
        if market_filtered_results:
            results = market_filtered_results

        # Sort dates chronologically if any
        sorted_dates = sorted(list(all_dates_found))

        # If specific date was requested but had no records, fallback to the nearest available date
        if target_date and not results and sorted_dates:
            nearest = find_nearest_date(target_date, sorted_dates)
            if nearest:
                with open(cache_file, mode="r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        r_state = row.get("state", "").strip()
                        r_district = row.get("district", "").strip()
                        r_market = row.get("market", "").strip()
                        r_comm = row.get("commodity", "").strip()
                        r_date = row.get("arrival_date", "").strip()

                        r_dist_clean = r_district.strip().lower()
                        target_dist_clean = district.strip().lower() if district else ""
                        state_match = not state or (state.lower() in r_state.lower())
                        district_match = not district or (r_dist_clean == target_dist_clean) or (target_dist_clean in r_dist_clean.split())
                        crop_match = not crop or (crop.lower() in r_comm.lower())

                        if state_match and district_match and crop_match and r_date == nearest:
                            results.append(row)
                            if target_market_clean and (target_market_clean in r_market.lower()):
                                market_filtered_results.append(row)

                if market_filtered_results:
                    results = market_filtered_results

        return results[:max_results], sorted_dates


def display_records_table(records: List[Dict], title: str):
    print(f"\n==================== [{title}] ====================")
    if not records:
        print("[!] No records found for the given criteria.")
        return

    print(f"[+] Found {len(records)} record(s):\n")
    for r in records:
        market = r.get("market")
        district = r.get("district")
        state = r.get("state")
        commodity = r.get("commodity")
        variety = r.get("variety", "Standard")
        modal = r.get("modal_price")
        min_p = r.get("min_price")
        max_p = r.get("max_price")
        date = r.get("arrival_date")

        print(f"Date: {date} | Mandi: {market} ({district}, {state})")
        print(f"  Crop: {commodity} ({variety})")
        print(f"  Modal Price: Rs. {modal}/Quintal (Min: Rs. {min_p}, Max: Rs. {max_p})")
        print("-" * 65)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch crop prices from your nearest mandi")
    parser.add_argument("--state", type=str, default="Uttar Pradesh", help="State name")
    parser.add_argument("--district", type=str, default="Jhansi", help="District name")
    parser.add_argument("--crop", type=str, default="Wheat", help="Crop name (e.g. Wheat, Paddy, Mustard)")
    parser.add_argument("--date", type=str, default=None, help="Query by specific date (e.g. 24/09/2026, 2026-09-24, or 'today')")
    parser.add_argument("--api-key", type=str, default=None, help="Optional data.gov.in API key")

    args = parser.parse_args()

    service = MandiPriceService(api_key=args.api_key)
    norm_date = normalize_date(args.date) if args.date and args.date.lower() != "today" else None

    # Check if user explicitly asked for an old date
    is_today_query = not args.date or args.date.lower() == "today"

    print(f"[*] Querying Mandi data: State='{args.state}', District='{args.district}', Crop='{args.crop}'")
    if norm_date:
        print(f"[*] Target Date: {norm_date}")

    if is_today_query and service.api_key:
        print("[*] Checking TODAY'S Live API (data.gov.in)...")
        try:
            direct, state_matches, rep_date = service.fetch_live_prices(
                state=args.state,
                district=args.district,
                crop=args.crop
            )
            if direct:
                display_records_table(direct, f"LIVE DATA ({rep_date})")
            else:
                print(f"[!] Notice: No arrivals for '{args.crop}' in {args.district} on {rep_date or 'today'}.")
                if state_matches:
                    print(f"\n[*] Active '{args.crop}' prices reported in other mandis across {args.state} on {rep_date}:")
                    display_records_table(state_matches[:10], f"STATE-WIDE LIVE ({rep_date})")
                
                # Also show recent historical dates as reference
                print("\n[*] Searching historical records for recent dates...")
                hist_records, available_dates = service.fetch_historical(args.state, args.district, args.crop, max_results=5)
                if available_dates:
                    print(f"[*] Available past dates for {args.crop} in {args.district}: {', '.join(available_dates[-6:])}")
                display_records_table(hist_records, "MOST RECENT HISTORICAL SESSIONS")
        except Exception as e:
            print(f"[!] Live query notice: {e}. Falling back to historical database...")
            records, dates = service.fetch_historical(args.state, args.district, args.crop, target_date=norm_date)
            display_records_table(records, f"HISTORICAL RECORDS ({norm_date or 'ALL'})")
    else:
        # User specified an old date or has no API key
        records, available_dates = service.fetch_historical(
            state=args.state,
            district=args.district,
            crop=args.crop,
            target_date=norm_date
        )
        if norm_date:
            display_records_table(records, f"HISTORICAL DATE: {norm_date}")
            if not records and available_dates:
                print(f"\n[*] No arrivals on {norm_date}. Dates with arrivals in {args.district}:")
                print("   " + ", ".join(available_dates[-10:]))
        else:
            display_records_table(records, f"HISTORICAL SESSIONS ({args.district})")
            if available_dates:
                print(f"\n[*] All available dates for {args.crop} in {args.district}:")
                print("   " + ", ".join(available_dates))
