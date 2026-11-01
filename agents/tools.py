"""
Agri_watch - Clean Specialist Tools for Market Intelligence & Data Ingestion
Calls MandiPriceService directly without regex or legacy router dependencies.
Exposes clean, structured JSON payloads for LLM Tool Calling and LiveKit.
"""

import os
import sys
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

sys.stdout.reconfigure(encoding='utf-8')

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from mandi_tracker import MandiPriceService, normalize_date
from agents.observability import traceable

MSP_FILE = os.path.join(PARENT_DIR, "data", "msp_benchmarks.json")
_price_service = MandiPriceService()

# Common Indic crop synonyms for tool input normalization
CROP_NORM_MAP = {
    "gehu": "Wheat", "gehun": "Wheat", "गेहूँ": "Wheat", "गेहू": "Wheat", "wheat": "Wheat",
    "dhan": "Paddy", "धान": "Paddy", "chawal": "Paddy", "paddy": "Paddy",
    "sarson": "Mustard", "सरसों": "Mustard", "mustard": "Mustard", "rai": "Mustard",
    "chana": "Gram", "chane": "Gram", "चने": "Gram", "चना": "Gram", "gram": "Gram", "chickpea": "Gram",
    "matar": "Peas(Dry)", "मटर": "Peas(Dry)",
    "pyaz": "Onion", "प्याज": "Onion", "onion": "Onion",
    "alu": "Potato", "आलू": "Potato", "potato": "Potato"
}

# Common Indic district mapping to English APMC database keys
DISTRICT_NORM_MAP = {
    "झाँसी": "Jhansi", "झांसी": "Jhansi", "jhansi": "Jhansi",
    "प्रयागराज": "Prayagraj", "इलाहाबाद": "Prayagraj", "prayagraj": "Prayagraj", "allahabad": "Prayagraj",
    "एटा": "Etah", "etah": "Etah",
    "सम्भल": "Sambhal", "sambhal": "Sambhal",
    "बदायूँ": "Badaun", "बदायूं": "Badaun", "badaun": "Badaun",
    "इटावा": "Etawah", "etawah": "Etawah",
    "ललितपुर": "Lalitpur", "lalitpur": "Lalitpur",
    "आगरा": "Agra", "agra": "Agra",
    "मथुरा": "Mathura", "mathura": "Mathura",
    "अलीगढ़": "Aligarh", "aligarh": "Aligarh",
    "राजकोट": "Rajkot", "rajkot": "Rajkot",
    "करनाल": "Karnal", "karnal": "Karnal",
    "लुधियाना": "Ludhiana", "ludhiana": "Ludhiana"
}


def normalize_district(dist: str) -> str:
    """Normalizes district from Devanagari/slang to English APMC database key."""
    if not dist:
        return "Jhansi"
    dist_clean = dist.strip().lower()
    for k, v in DISTRICT_NORM_MAP.items():
        if k.lower() in dist_clean or dist_clean in k.lower():
            return v
    return dist.strip().title()


def clean_market_name(market: str) -> str:
    """Removes APMC codes and bracketed noise for clean voice output."""
    if not market:
        return "मंडी"
    clean = re.sub(r"\bAPMC\b", "", market, flags=re.IGNORECASE)
    clean = re.sub(r"\(.*?\)", "", clean).strip()
    return clean


def parse_spoken_date(date_str: Optional[str]) -> Optional[str]:
    """Parses spoken/relative dates into DD/MM/YYYY format."""
    if not date_str:
        return None
    d_clean = date_str.strip().lower()
    if d_clean in ("today", "aaj", "आज"):
        return datetime.now().strftime("%d/%m/%Y")
    if d_clean in ("yesterday", "kal", "कल", "beeta kal", "बीता कल"):
        return (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
    return normalize_date(date_str)


# -------------------------------------------------------------------------
# Tool 1: Get Crop Price (Clean, factual, single-purpose, date-aware)
# -------------------------------------------------------------------------
@traceable(name="Agmarknet:get_crop_price", run_type="tool")
def get_crop_price(
    crop: str,
    district: str,
    state: str = "Uttar Pradesh",
    date: Optional[str] = None
) -> str:
    """
    Fetch the wholesale APMC mandi price and modal rate for any crop in a district.
    Supports querying by specific date (e.g. '24/09/2026', 'yesterday', 'today').
    If date is omitted, returns the latest available price.
    """
    norm_crop = CROP_NORM_MAP.get(crop.lower().strip(), crop.strip())
    norm_dist = normalize_district(district)
    target_date = parse_spoken_date(date)
    is_today = (not target_date) or (target_date == datetime.now().strftime("%d/%m/%Y"))

    records = []
    is_live = False
    reporting_date = None

    # Try live data.gov.in API if user didn't request an older date
    if _price_service.api_key and is_today:
        try:
            direct, state_wide, rep_date = _price_service.fetch_live_prices(state, norm_dist, norm_crop)
            if direct:
                records = direct
                is_live = True
                reporting_date = rep_date
            elif state_wide:
                records = state_wide
                reporting_date = rep_date
        except Exception:
            pass

    # Historical lookup (by specific target_date or latest available)
    if not records:
        hist_records, _ = _price_service.fetch_historical(state, norm_dist, norm_crop, target_date=target_date)
        records = hist_records
        if records:
            reporting_date = records[0].get("arrival_date")

    if not records:
        date_msg = f" ({date} को)" if date else ""
        return json.dumps({
            "status": "not_found",
            "crop": norm_crop,
            "district": district,
            "date": target_date or date,
            "message": f"{district} मंडी में {norm_crop} का भाव{date_msg} उपलब्ध नहीं है।"
        }, ensure_ascii=False)

    top = records[0]
    market = clean_market_name(top.get("market", district))
    variety = re.sub(r"\(.*?\)", "", top.get("variety", "सामान्य")).strip()

    try:
        modal_p = float(top.get("modal_price", 0))
        min_p = float(top.get("min_price", 0))
        max_p = float(top.get("max_price", 0))
    except (ValueError, TypeError):
        modal_p = min_p = max_p = 0

    return json.dumps({
        "status": "success",
        "crop": norm_crop,
        "district": district,
        "market": market,
        "variety": variety,
        "modal_price": modal_p,
        "min_price": min_p,
        "max_price": max_p,
        "reporting_date": reporting_date,
        "is_live_today": is_live,
        "verified_rate_rs_per_quintal": f"₹{modal_p:.0f}"
    }, ensure_ascii=False)


# -------------------------------------------------------------------------
# Tool 2: Compare Mandi Arbitrage (Only when asked where to sell / comparison)
# -------------------------------------------------------------------------
@traceable(name="ArbitrageEngine:compare_mandi_arbitrage", run_type="tool")
def compare_mandi_arbitrage(
    crop: str,
    district: str,
    state: str = "Uttar Pradesh",
    quantity_quintals: float = 25.0
) -> str:
    """
    Compare commodity prices across multiple APMC mandis within a district
    to find the highest-paying market and calculate transport net profit.
    Call this ONLY when a farmer asks where to sell, asks for higher profit, or asks to compare mandis.
    """
    norm_crop = CROP_NORM_MAP.get(crop.lower().strip(), crop.strip())
    norm_dist = normalize_district(district)
    records = []

    if _price_service.api_key:
        try:
            direct, state_wide, _ = _price_service.fetch_live_prices(state, norm_dist, norm_crop)
            records = direct or state_wide or []
        except Exception:
            pass

    if not records:
        hist_records, _ = _price_service.fetch_historical(state, norm_dist, norm_crop)
        records = hist_records or []

    # Group by market and keep latest record per market
    market_latest = {}
    for r in records:
        m_name = clean_market_name(r.get("market", ""))
        if not m_name or m_name in market_latest:
            continue
        try:
            modal = float(r.get("modal_price", 0))
            if modal > 0:
                market_latest[m_name] = modal
        except (ValueError, TypeError):
            continue

    if len(market_latest) < 2:
        return json.dumps({
            "status": "insufficient_mandis",
            "message": f"{district} क्षेत्र की सभी मंडियों में भाव लगभग एक समान है।"
        }, ensure_ascii=False)

    sorted_mandis = sorted(market_latest.items(), key=lambda x: x[1], reverse=True)
    top_market, top_price = sorted_mandis[0]
    low_market, low_price = sorted_mandis[-1]
    spread = top_price - low_price

    # Transport deduction: Rs 15/quintal
    freight = 15.0
    net_gain = (spread - freight) * quantity_quintals if spread > freight else 0.0

    return json.dumps({
        "status": "success",
        "crop": norm_crop,
        "district": district,
        "best_market": top_market,
        "best_price": top_price,
        "comparison_market": low_market,
        "comparison_price": low_price,
        "price_difference": spread,
        "net_gain_on_trolley_rs": net_gain,
        "recommend_travel": spread > 30.0
    }, ensure_ascii=False)


# -------------------------------------------------------------------------
# Tool 3: Check MSP Floor (Only when asked about government MSP / floor rate)
# -------------------------------------------------------------------------
@traceable(name="MSPEngine:check_msp_floor", run_type="tool")
def check_msp_floor(crop: str) -> str:
    """
    Look up the official Government Minimum Support Price (MSP) floor rate for a crop.
    Call this ONLY when a farmer asks about MSP, government rate, or minimum guaranteed price.
    """
    norm_crop = CROP_NORM_MAP.get(crop.lower().strip(), crop.strip())

    msp_data = {}
    if os.path.exists(MSP_FILE):
        with open(MSP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            msp_data = data.get("2026_27", {})

    found_info = None
    for k, v in msp_data.items():
        if k.lower() in norm_crop.lower() or norm_crop.lower() in k.lower():
            found_info = v
            break

    if not found_info:
        return json.dumps({
            "status": "not_notified",
            "crop": norm_crop,
            "message": f"{norm_crop} के लिए कोई प्रत्यक्ष सरकारी MSP अधिसूचित नहीं है।"
        }, ensure_ascii=False)

    return json.dumps({
        "status": "success",
        "crop": norm_crop,
        "msp_rate_per_quintal": found_info.get("msp"),
        "season": found_info.get("season", "Rabi")
    }, ensure_ascii=False)


# LiveKit Tools Export
try:
    from livekit.agents import llm
    get_crop_price_tool = llm.function_tool(description="Fetch wholesale mandi price for a crop in a district.")(get_crop_price)
    compare_mandi_arbitrage_tool = llm.function_tool(description="Compare prices across nearby mandis.")(compare_mandi_arbitrage)
    check_msp_floor_tool = llm.function_tool(description="Look up official Government MSP floor rate for a crop.")(check_msp_floor)
    LIVEKIT_TOOLS = [get_crop_price_tool, compare_mandi_arbitrage_tool, check_msp_floor_tool]
except Exception:
    LIVEKIT_TOOLS = []


if __name__ == "__main__":
    print("[*] Testing Clean Modular Tools...")
    print("Price Tool:", get_crop_price("Wheat", "Jhansi"))
    print("\nArbitrage Tool:", compare_mandi_arbitrage("Wheat", "Jhansi"))
    print("\nMSP Tool:", check_msp_floor("Wheat"))

