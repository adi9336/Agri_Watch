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

from mandi_tracker import MandiPriceService, normalize_date, is_commodity_match
from agents.observability import traceable

MSP_FILE = os.path.join(PARENT_DIR, "data", "msp_benchmarks.json")
_price_service = MandiPriceService()

# Common Indic crop synonyms for tool input normalization
CROP_NORM_MAP = {
    "gehu": "Wheat", "gehun": "Wheat", "गेहूँ": "Wheat", "गेहू": "Wheat", "wheat": "Wheat",
    "dhan": "Paddy", "धान": "Paddy", "chawal": "Paddy", "paddy": "Paddy",
    "sarson": "Mustard", "सरसों": "Mustard", "mustard": "Mustard", "rai": "Mustard",
    "chana": "Gram", "chane": "Gram", "चने": "Gram", "चना": "Gram", "gram": "Gram", "chickpea": "Gram",
    "arhar": "Red gram", "तुअर": "Red gram", "अरहर": "Red gram",
    "moong": "Green Gram", "मूँग": "Green Gram", "मूंग": "Green Gram",
    "matar": "Peas(Dry)", "मटर": "Peas(Dry)",
    "pyaz": "Onion", "प्याज": "Onion", "onion": "Onion",
    "alu": "Potato", "आलू": "Potato", "potato": "Potato"
}

# Common Indic district mapping to English APMC database keys
DISTRICT_NORM_MAP = {
    "झाँसी": "Jhansi", "झांसी": "Jhansi", "jhansi": "Jhansi",
    "कटनी": "Katni", "katni": "Katni",
    "सतना": "Satna", "satna": "Satna",
    "दमोह": "Damoh", "damoh": "Damoh",
    "जबलपुर": "Jabalpur", "jabalpur": "Jabalpur",
    "ग्वालियर": "Gwalior", "gwalior": "Gwalior",
    "सागर": "Sagar", "sagar": "Sagar",
    "उज्जैन": "Ujjain", "ujjain": "Ujjain",
    "इंदौर": "Indore", "indore": "Indore",
    "विदिशा": "Vidisha", "vidisha": "Vidisha",
    "रायसेन": "Raisen", "raisen": "Raisen",
    "सीहोर": "Sehore", "sehore": "Sehore",
    "भोपाल": "Bhopal", "bhopal": "Bhopal",
    "कोटा": "Kota", "kota": "Kota",
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
    "लुधियाना": "Ludhiana", "ludhiana": "Ludhiana",
    "थाने": "Thane", "ठाणे": "Thane", "thane": "Thane",
    "कल्याण": "Kalyan", "kalyan": "Kalyan",
    "पालघर": "Palghar", "palghar": "Palghar"
}

# Automatic State Association to prevent wrong-state fallback lookups
DISTRICT_STATE_MAP = {
    "Damoh": "Madhya Pradesh", "Satna": "Madhya Pradesh", "Katni": "Madhya Pradesh",
    "Jabalpur": "Madhya Pradesh", "Gwalior": "Madhya Pradesh", "Sagar": "Madhya Pradesh",
    "Ujjain": "Madhya Pradesh", "Indore": "Madhya Pradesh", "Vidisha": "Madhya Pradesh",
    "Raisen": "Madhya Pradesh", "Sehore": "Madhya Pradesh", "Bhopal": "Madhya Pradesh",
    "Jhansi": "Uttar Pradesh", "Agra": "Uttar Pradesh", "Mathura": "Uttar Pradesh",
    "Aligarh": "Uttar Pradesh", "Prayagraj": "Uttar Pradesh", "Etah": "Uttar Pradesh",
    "Sambhal": "Uttar Pradesh", "Badaun": "Uttar Pradesh", "Etawah": "Uttar Pradesh",
    "Lalitpur": "Uttar Pradesh", "Kanpur": "Uttar Pradesh", "Lucknow": "Uttar Pradesh",
    "Varanasi": "Uttar Pradesh", "Barabanki": "Uttar Pradesh",
    "Kota": "Rajasthan", "Rajkot": "Gujarat", "Karnal": "Haryana", "Ludhiana": "Punjab",
    "Thane": "Maharashtra", "Kalyan": "Maharashtra", "Palghar": "Maharashtra", "Mumbai": "Maharashtra", "Pune": "Maharashtra"
}


# Market Directory mapping: market_name -> {market, district, state}
MARKET_DIR_PATH = os.path.join(PARENT_DIR, "data", "market_directory.json")
_MARKET_DIRECTORY = {}
if os.path.exists(MARKET_DIR_PATH):
    try:
        with open(MARKET_DIR_PATH, "r", encoding="utf-8") as f:
            _MARKET_DIRECTORY = json.load(f)
    except Exception:
        pass

# Ensure critical markets are accurately mapped to their official APMC district and state
_MARKET_DIRECTORY.update({
    "kalyan": {"market": "APMC Kalyan", "district": "Thane", "state": "Maharashtra"},
    "thane": {"market": "APMC Kalyan", "district": "Thane", "state": "Maharashtra"},
    "थाने": {"market": "APMC Kalyan", "district": "Thane", "state": "Maharashtra"},
    "ठाणे": {"market": "APMC Kalyan", "district": "Thane", "state": "Maharashtra"},
    "कल्याण": {"market": "APMC Kalyan", "district": "Thane", "state": "Maharashtra"},
    "थाने कल्याण": {"market": "APMC Kalyan", "district": "Thane", "state": "Maharashtra"},
    "ठाणे कल्याण": {"market": "APMC Kalyan", "district": "Thane", "state": "Maharashtra"}
})


STT_PHONETIC_VARIANTS = {
    "रॉड": "rath", "राड": "rath", "राट": "rath", "रठ": "rath", "rod": "rath", "raad": "rath", "raat": "rath",
    "मौ": "mauranipur", "उरई": "orai", "अतर्रा": "atarra", "बरुआसागर": "barwasagar",
    "झाँसी": "jhansi", "झांसी": "jhansi", "महोबा": "mahoba", "बाँदा": "banda", "बांदा": "banda", "हमीरपुर": "hamirpur"
}

NEIGHBORING_DISTRICTS = {
    # Bundelkhand / Central UP & MP
    "Hamirpur": ["Mahoba", "Jhansi", "Banda", "Jalaun", "Kanpur Dehat", "Fatehpur"],
    "Mahoba": ["Hamirpur", "Jhansi", "Banda", "Chhatarpur"],
    "Jhansi": ["Hamirpur", "Mahoba", "Jalaun", "Lalitpur", "Tikamgarh", "Datia", "Shivpuri"],
    "Banda": ["Hamirpur", "Mahoba", "Chitrakoot", "Fatehpur"],
    "Jalaun": ["Hamirpur", "Jhansi", "Kanpur Dehat", "Auraiya", "Bhind"],
    "Lalitpur": ["Jhansi", "Tikamgarh", "Sagar", "Guna", "Ashoknagar"],
    "Chitrakoot": ["Banda", "Satna", "Prayagraj", "Kaushambi"],
    "Prayagraj": ["Kaushambi", "Pratapgarh", "Mirzapur", "Bhadohi", "Chitrakoot", "Rewa"],
    
    # MP Key Hubs
    "Damoh": ["Sagar", "Katni", "Panna", "Jabalpur", "Narsinghpur"],
    "Sagar": ["Damoh", "Vidisha", "Lalitpur", "Tikamgarh", "Raisen", "Narsinghpur"],
    "Katni": ["Damoh", "Jabalpur", "Satna", "Panna", "Umaria"],
    "Jabalpur": ["Katni", "Damoh", "Narsinghpur", "Seoni", "Mandla"],
    "Satna": ["Panna", "Rewa", "Katni", "Banda", "Chitrakoot"],
    "Rewa": ["Satna", "Sidhi", "Prayagraj"],
    "Vidisha": ["Sagar", "Bhopal", "Raisen", "Guna", "Ashoknagar"],
    "Bhopal": ["Sehore", "Raisen", "Rajgarh", "Vidisha"],
    "Sehore": ["Bhopal", "Raisen", "Hoshangabad", "Dewas", "Shajapur"],
    "Indore": ["Ujjain", "Dewas", "Dhar", "Khargone"],
    "Ujjain": ["Indore", "Dewas", "Dhar", "Ratlam", "Shajapur", "Agar Malwa"],
    
    # Western UP / Braj
    "Agra": ["Mathura", "Firozabad", "Etah", "Hathras", "Bharatpur", "Dholpur"],
    "Mathura": ["Agra", "Hathras", "Aligarh", "Palwal", "Bharatpur"],
    "Aligarh": ["Mathura", "Hathras", "Bulandshahr", "Kasganj", "Sambhal", "Badaun"],
    "Etah": ["Kasganj", "Mainpuri", "Firozabad", "Agra", "Aligarh"],
    "Etawah": ["Mainpuri", "Auraiya", "Jalaun", "Bhind", "Agra"],
    
    # Haryana / Punjab / Rajasthan
    "Karnal": ["Kurukshetra", "Panipat", "Kaithal", "Yamunanagar"],
    "Ludhiana": ["Jalandhar", "Moga", "Barnala", "Fatehgarh Sahib", "Rupnagar"],
    "Kota": ["Bundi", "Baran", "Jhalawar"],
    "Rajkot": ["Morbi", "Jamnagar", "Junagadh", "Amreli", "Surendranagar"]
}

MARKET_HI_MAP = {
    "Raath": "राठ मंडी",
    "Mahoba": "महोबा मंडी",
    "Mauranipur": "मऊरानीपुर मंडी",
    "Maudaha": "मौदहा मंडी",
    "Muskara": "मुस्करा मंडी",
    "Jhansi": "झाँसी मंडी",
    "Banda": "बाँदा मंडी",
    "Atarra": "अतर्रा मंडी",
    "Charkhari": "चरखारी मंडी",
    "Bharuasumerpur": "भरुआ सुमेरपुर मंडी",
    "Moth": "मोठ मंडी",
    "Gurusarai": "गुरसराय मंडी",
    "Orai": "उरई मंडी",
    "Damoh": "दमोह मंडी",
    "Satna": "सतना मंडी",
    "Katni": "कटनी मंडी",
    "Sagar": "सागर मंडी",
    "Jabalpur": "जबलपुर मंडी",
    "Vidisha": "विदिशा मंडी"
}

def resolve_location(loc: str, explicit_state: Optional[str] = None) -> tuple:
    """
    Intelligently resolves any mandi name, sub-market, tehsil, or district (in Hindi or English)
    to (resolved_district, resolved_market, resolved_state).
    Example:
      'राठ' / 'rath' -> ('Hamirpur', 'Raath APMC', 'Uttar Pradesh')
      'मऊरानीपुर' / 'mauranipur' -> ('Jhansi', 'Mauranipur APMC', 'Uttar Pradesh')
      'Jhansi' / 'झांसी' -> ('Jhansi', None, 'Uttar Pradesh')
    """
    if not loc:
        return "Jhansi", None, explicit_state or "Uttar Pradesh"

    loc_clean = loc.strip().lower()
    # Strip common noise words and proximity phrases
    loc_clean = re.sub(r"\b(mandi|मंडी|apmc|market|bazar|बाजार|जिला|jila|tehsil|तहसील|के आसपास|आसपास|के पास|पास की|के नजदीक|आस पास)\b", "", loc_clean).strip()
    loc_clean = re.sub(r"^(के|की|में|से)\s+", "", loc_clean).strip()
    loc_clean = re.sub(r"\s+(के|की|में|से)$", "", loc_clean).strip()
    if not loc_clean:
        loc_clean = loc.strip().lower()

    # Phonetic alias mapping for Indian STT transcriptions (e.g. रॉड -> rath)
    if loc_clean in STT_PHONETIC_VARIANTS:
        loc_clean = STT_PHONETIC_VARIANTS[loc_clean]

    # 1. Direct match in market directory
    if loc_clean in _MARKET_DIRECTORY:
        entry = _MARKET_DIRECTORY[loc_clean]
        state = explicit_state or entry.get("state") or infer_state(entry["district"])
        return entry["district"], entry.get("market"), state

    # 2. Direct match in district norm map
    for k, v in DISTRICT_NORM_MAP.items():
        if k.lower() == loc_clean:
            return v, None, explicit_state or infer_state(v)

    # 3. Substring / Prefix match in market directory (for length >= 3)
    if len(loc_clean) >= 3:
        for k, v in _MARKET_DIRECTORY.items():
            if k == loc_clean or k.startswith(loc_clean) or loc_clean.startswith(k):
                state = explicit_state or v.get("state") or infer_state(v["district"])
                return v["district"], v.get("market"), state

    # 4. Partial check in district norm map
    for k, v in DISTRICT_NORM_MAP.items():
        if k.lower() in loc_clean:
            return v, None, explicit_state or infer_state(v)

    norm_d = normalize_district(loc)
    return norm_d, None, explicit_state or infer_state(norm_d)


def infer_state(district: str, explicit_state: Optional[str] = None) -> str:
    """Infers official state if not explicitly specified by user or defaulted."""
    if explicit_state and explicit_state.strip().lower() not in ("", "none", "null", "uttar pradesh"):
        return explicit_state.strip()
    norm_d = normalize_district(district)
    return DISTRICT_STATE_MAP.get(norm_d, explicit_state or "Uttar Pradesh")


def normalize_district(dist: str) -> str:
    """Normalizes district from Devanagari/slang to English APMC database key."""
    if not dist:
        return "Jhansi"
    dist_clean = dist.strip().lower()
    # 1. Exact match first
    for k, v in DISTRICT_NORM_MAP.items():
        if k.lower() == dist_clean:
            return v
    # 2. Check if known district keyword is contained in user input (e.g., "झाँसी जिला")
    for k, v in DISTRICT_NORM_MAP.items():
        if k.lower() in dist_clean:
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
    if any(w in d_clean for w in ("today", "aaj", "आज")):
        return datetime.now().strftime("%d/%m/%Y")
    if any(w in d_clean for w in ("yesterday", "kal", "कल", "beeta kal", "बीता कल")):
        return (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
    if any(w in d_clean for w in ("हफ्ते", "हफ्ता", "सप्ताह", "week", "last week")):
        return (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
    return normalize_date(date_str)


# -------------------------------------------------------------------------
# Tool 1: Get Crop Price (Clean, factual, single-purpose, date-aware)
# -------------------------------------------------------------------------
@traceable(name="Agmarknet:get_crop_price", run_type="tool")
def get_crop_price(
    crop: str,
    district: str,
    state: Optional[str] = None,
    date: Optional[str] = None
) -> str:
    """
    Fetch wholesale APMC mandi price and modal rate for any crop in a district.
    Strictly accepts a date. Defaults to 'today' if not provided.
    If today's auction is not yet published, automatically retrieves the nearest available date.
    """
    norm_crop = CROP_NORM_MAP.get(crop.lower().strip(), crop.strip())
    resolved_dist, resolved_market, resolved_state = resolve_location(district, state)
    
    # Strict date resolution: Default to today
    resolved_date_input = date if date else "today"
    target_date = parse_spoken_date(resolved_date_input)
    today_str = datetime.now().strftime("%d/%m/%Y")
    is_today = (target_date == today_str) or (resolved_date_input.lower() in ("today", "aaj", "आज"))

    records = []
    is_live = False
    reporting_date = None

    # 1. Try live data.gov.in API for today's data (must match target district)
    if _price_service.api_key and is_today:
        try:
            direct, _, rep_date = _price_service.fetch_live_prices(resolved_state, resolved_dist, norm_crop, market=resolved_market)
            if direct:
                records = direct
                is_live = True
                reporting_date = rep_date or today_str
        except Exception:
            pass

    # 2. Historical & nearest-date database lookup
    if not records:
        hist_records, _ = _price_service.fetch_historical(resolved_state, resolved_dist, norm_crop, target_date=target_date, market=resolved_market)
        records = hist_records
        if records:
            reporting_date = records[0].get("arrival_date")

    if not records:
        date_msg = f" ({resolved_date_input} को)" if resolved_date_input else ""
        return json.dumps({
            "status": "not_found",
            "crop": norm_crop,
            "district": district,
            "date": target_date or resolved_date_input,
            "message": f"{district} मंडी में {norm_crop} का भाव{date_msg} उपलब्ध नहीं है।"
        }, ensure_ascii=False)

    top = records[0]
    market = clean_market_name(top.get("market", resolved_market or resolved_dist))
    variety = re.sub(r"\(.*?\)", "", top.get("variety", "सामान्य")).strip()

    try:
        modal_p = float(top.get("modal_price", 0))
        min_p = float(top.get("min_price", 0))
        max_p = float(top.get("max_price", 0))
    except (ValueError, TypeError):
        modal_p = min_p = max_p = 0

    is_exact_match = is_live or (reporting_date == target_date)
    if is_live:
        date_note = "आज का ताज़ा भाव"
    elif is_exact_match:
        date_note = f"{reporting_date} की तारीख का भाव"
    else:
        date_note = f"आज का भाव अभी दर्ज नहीं हुआ है, सबसे नजदीकी तारीख {reporting_date} का भाव"

    return json.dumps({
        "status": "success",
        "crop": norm_crop,
        "district": district,
        "market": market,
        "variety": variety,
        "modal_price": modal_p,
        "min_price": min_p,
        "max_price": max_p,
        "requested_date": target_date,
        "reporting_date": reporting_date,
        "is_exact_date": is_exact_match,
        "is_today": is_live or (reporting_date == today_str),
        "date_note": date_note,
        "verified_rate_rs_per_quintal": f"₹{modal_p:.0f}"
    }, ensure_ascii=False)


# -------------------------------------------------------------------------
# Tool 2: Compare Mandi Arbitrage (Only when asked where to sell / comparison)
# -------------------------------------------------------------------------
@traceable(name="ArbitrageEngine:compare_mandi_arbitrage", run_type="tool")
def compare_mandi_arbitrage(
    crop: str,
    district: str,
    state: Optional[str] = None,
    quantity_quintals: float = 25.0
) -> str:
    """
    Compare commodity prices across multiple APMC mandis within a district or neighboring regional cluster
    to find the highest-paying market, list nearby mandis with verified rates, and calculate transport net profit.
    Call this when a farmer asks where to sell, asks for higher profit, or asks about nearby/other mandis.
    """
    norm_crop = CROP_NORM_MAP.get(crop.lower().strip(), crop.strip())
    resolved_dist, resolved_market, resolved_state = resolve_location(district, state)
    cluster_districts = [resolved_dist] + NEIGHBORING_DISTRICTS.get(resolved_dist, [])
    cluster_lower = {d.lower() for d in cluster_districts}

    market_latest = {}
    today_str = datetime.now().strftime("%d/%m/%Y")

    def _parse_d(d_str: str) -> datetime:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(d_str.strip(), fmt)
            except Exception:
                pass
        return datetime.min

    # 1. Try live data.gov.in API for target district if available
    if _price_service.api_key:
        try:
            direct, state_wide, rep_date = _price_service.fetch_live_prices(resolved_state, resolved_dist, norm_crop)
            for r in (direct or state_wide or []):
                m_raw = r.get("market", "")
                m_clean = clean_market_name(m_raw)
                if not m_clean:
                    continue
                try:
                    modal = float(r.get("modal_price", 0))
                    if modal > 0:
                        r_date = r.get("arrival_date", today_str)
                        if m_clean not in market_latest or _parse_d(r_date) >= _parse_d(market_latest[m_clean]["arrival_date"]):
                            market_latest[m_clean] = {
                                "market": m_clean,
                                "market_hi": MARKET_HI_MAP.get(m_clean, m_clean + " मंडी"),
                                "district": r.get("district", resolved_dist),
                                "modal_price": modal,
                                "arrival_date": r_date
                            }
                except (ValueError, TypeError):
                    continue
        except Exception:
            pass

    # 2. Ingest historical records across all cluster districts from local cache
    cache_file = _price_service.ensure_local_cache()
    if os.path.exists(cache_file):
        try:
            import csv
            with open(cache_file, mode="r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    r_dist = row.get("district", "").strip()
                    if r_dist.lower() in cluster_lower:
                        r_comm = row.get("commodity", "")
                        if is_commodity_match(norm_crop, r_comm):
                            m_raw = row.get("market", "")
                            m_clean = clean_market_name(m_raw)
                            if not m_clean:
                                continue
                            try:
                                modal = float(row.get("modal_price", 0))
                                if modal <= 0:
                                    continue
                            except (ValueError, TypeError):
                                continue
                            r_date = row.get("arrival_date", "").strip()
                            if m_clean not in market_latest or _parse_d(r_date) > _parse_d(market_latest[m_clean]["arrival_date"]):
                                market_latest[m_clean] = {
                                    "market": m_clean,
                                    "market_hi": MARKET_HI_MAP.get(m_clean, m_clean + " मंडी"),
                                    "district": r_dist,
                                    "modal_price": modal,
                                    "arrival_date": r_date
                                }
        except Exception:
            pass

    if not market_latest:
        return json.dumps({
            "status": "not_found",
            "crop": norm_crop,
            "district": district,
            "message": f"किसान भाई, {district} और आसपास के क्षेत्र में {norm_crop} की कोई हालिया आवक दर्ज नहीं मिली है।"
        }, ensure_ascii=False)

    sorted_mandis = sorted(market_latest.values(), key=lambda x: x["modal_price"], reverse=True)
    top_mandi = sorted_mandis[0]
    low_mandi = sorted_mandis[-1]
    spread = top_mandi["modal_price"] - low_mandi["modal_price"]

    # Locate local mandi if specified by user or in reference district
    local_mandi = None
    if resolved_market:
        res_m_clean = clean_market_name(resolved_market).lower()
        local_mandi = next((m for m in sorted_mandis if res_m_clean in m["market"].lower()), None)
    if not local_mandi:
        local_mandi = next((m for m in sorted_mandis if m["district"].lower() == resolved_dist.lower()), None)

    local_price = local_mandi["modal_price"] if local_mandi else low_mandi["modal_price"]
    local_name = local_mandi["market_hi"] if local_mandi else (clean_market_name(district) + " मंडी")
    effective_spread = top_mandi["modal_price"] - local_price

    # Transport freight: ₹15/quintal
    freight = 15.0
    net_gain = (effective_spread - freight) * quantity_quintals if effective_spread > freight else 0.0

    # Build clean structured list of nearby reporting mandis
    nearby_mandis = []
    for m in sorted_mandis[:5]:
        nearby_mandis.append({
            "market": m["market_hi"],
            "district": m["district"],
            "modal_price": m["modal_price"],
            "rate_display": f"₹{m['modal_price']:.0f} प्रति क्विंटल",
            "arrival_date": m["arrival_date"]
        })

    # Generate authoritative spoken Hindi summary
    crop_display = "चना" if norm_crop.lower() in ("gram", "bengal gram", "chana") else norm_crop
    dist_display = clean_market_name(district)

    if len(sorted_mandis) >= 2 and effective_spread > 20 and local_mandi and local_mandi["market"] != top_mandi["market"]:
        third_m = next((m for m in sorted_mandis if m["market"] not in (top_mandi["market"], local_mandi["market"])), None)
        third_part = f", और {third_m['market_hi']} में ₹{third_m['modal_price']:.0f}" if third_m else ""
        companion_summary_hi = (
            f"किसान भाई, {dist_display} के आसपास: {top_mandi['market_hi']} में {crop_display} सबसे ऊँचे भाव ₹{top_mandi['modal_price']:.0f}, "
            f"{local_name} में ₹{local_price:.0f}{third_part} प्रति क्विंटल रहा है। "
            f"{top_mandi['market_hi']} में ₹{effective_spread:.0f} प्रति क्विंटल अधिक दाम मिल सकता है।"
        )
    elif len(sorted_mandis) >= 2 and spread > 20:
        second_m = sorted_mandis[1]
        companion_summary_hi = (
            f"किसान भाई, {dist_display} के आसपास: {top_mandi['market_hi']} में {crop_display} सबसे ऊँचे भाव ₹{top_mandi['modal_price']:.0f} "
            f"और {second_m['market_hi']} में ₹{second_m['modal_price']:.0f} प्रति क्विंटल रहा है। "
            f"{top_mandi['market_hi']} में सबसे अच्छा दाम मिल रहा है।"
        )
    elif len(sorted_mandis) >= 2:
        m1 = sorted_mandis[0]["market_hi"]
        m2 = sorted_mandis[1]["market_hi"]
        companion_summary_hi = (
            f"किसान भाई, {dist_display} और आसपास की मंडियों (जैसे {m1} और {m2}) में {crop_display} का भाव लगभग ₹{top_mandi['modal_price']:.0f} "
            f"प्रति क्विंटल ही चल रहा है, इसलिए कहीं अलग ले जाने पर विशेष बचत नहीं होगी।"
        )
    else:
        companion_summary_hi = (
            f"किसान भाई, {dist_display} क्षेत्र में केवल {top_mandi['market_hi']} में ही {crop_display} का भाव ₹{top_mandi['modal_price']:.0f} "
            f"प्रति क्विंटल दर्ज हुआ है। आसपास की अन्य मंडियों में अभी नई आवक दर्ज नहीं हुई है।"
        )

    return json.dumps({
        "status": "success",
        "crop": norm_crop,
        "district": district,
        "resolved_district": resolved_dist,
        "reporting_date": top_mandi["arrival_date"],
        "is_today": (top_mandi["arrival_date"] == today_str),
        "best_market": top_mandi["market_hi"],
        "best_price": top_mandi["modal_price"],
        "local_market": local_name,
        "local_price": local_price,
        "price_difference": effective_spread,
        "net_gain_on_trolley_rs": net_gain,
        "recommend_travel": effective_spread > 30.0,
        "nearby_mandis": nearby_mandis,
        "companion_summary_hi": companion_summary_hi
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


# -------------------------------------------------------------------------
# Tool 4: Get Crop Price Trend & Multi-Day Companion Intelligence
# -------------------------------------------------------------------------
@traceable(name="Agmarknet:get_crop_price_trend", run_type="tool")
def get_crop_price_trend(
    crop: str,
    district: str,
    timeframe: Optional[str] = None,
    state: Optional[str] = None
) -> str:
    """
    Analyzes historical price movement, trend direction (Rising / Falling / Stable),
    and multi-day/monthly price ranges (Min to Max) for a crop in a district.
    Call this when a farmer asks:
    - About past prices across multiple days, weeks, or a month (e.g. 'पिछले एक महीने का भाव', 'दिन के हिसाब से भाव', 'पिछले हफ्ते का हाल').
    - Whether prices are rising, falling, or stable.
    - If they should sell now or wait.
    """
    norm_crop = CROP_NORM_MAP.get(crop.lower().strip(), crop.strip())
    resolved_dist, resolved_market, resolved_state = resolve_location(district, state)
    norm_dist = resolved_dist

    hist_records, _ = _price_service.fetch_historical(resolved_state, norm_dist, norm_crop, market=resolved_market, max_results=100)
    records = list(hist_records or [])

    # Include live data if available
    if _price_service.api_key:
        try:
            direct, _, _ = _price_service.fetch_live_prices(resolved_state, norm_dist, norm_crop)
            if direct:
                records.extend(direct)
        except Exception:
            pass

    if not records:
        return json.dumps({
            "status": "not_found",
            "crop": norm_crop,
            "district": district,
            "message": f"{district} मंडी में {norm_crop} के रुझान का पुराना डेटा उपलब्ध नहीं है।"
        }, ensure_ascii=False)

    dated_points = []
    seen = set()
    for r in records:
        try:
            arr_date = r.get("arrival_date", "").strip()
            dt = datetime.strptime(arr_date, "%d/%m/%Y")
            p = float(r.get("modal_price", 0))
            m = clean_market_name(r.get("market", district))
            key = (arr_date, p, m)
            if key not in seen and p > 0:
                seen.add(key)
                dated_points.append((dt, arr_date, p, m))
        except (ValueError, TypeError):
            continue

    if not dated_points:
        return json.dumps({
            "status": "not_found",
            "crop": norm_crop,
            "district": district,
            "message": f"{district} मंडी में {norm_crop} का रुझान उपलब्ध नहीं है।"
        }, ensure_ascii=False)

    dated_points.sort(key=lambda x: x[0])

    min_pt = min(dated_points, key=lambda x: x[2])
    max_pt = max(dated_points, key=lambda x: x[2])
    start_pt = dated_points[0]
    latest_pt = dated_points[-1]

    min_price = min_pt[2]
    max_price = max_pt[2]
    latest_price = latest_pt[2]
    latest_date = latest_pt[1]
    market = latest_pt[3]

    if len(dated_points) >= 3:
        baseline_price = sum(p[2] for p in dated_points[-5:-1]) / len(dated_points[-5:-1])
    else:
        baseline_price = start_pt[2]

    diff = latest_price - baseline_price
    total_change = latest_price - start_pt[2]

    if diff > 30:
        trend = "RISING"
        advice = "भाव बढ़ रहे हैं, बाज़ार में मांग अच्छी है।"
    elif diff < -30:
        trend = "FALLING"
        advice = "भाव में थोड़ी गिरावट देखी जा रही है।"
    else:
        trend = "STABLE"
        advice = "भाव पिछले दिनों से लगभग स्थिर बने हुए हैं।"

    time_label = "पिछले दिनों में"
    if timeframe:
        tf_lower = timeframe.lower()
        if any(w in tf_lower for w in ("महीने", "महीना", "month", "30")):
            time_label = "पिछले एक महीने में"
        elif any(w in tf_lower for w in ("हफ्ते", "हफ्ता", "week", "7")):
            time_label = "पिछले हफ्ते"

    # Pre-formulated Indic companion synthesis (ready for voice TTS)
    if min_price == max_price:
        summary_hi = f"किसान भाई, {time_label} {district} मंडी में {norm_crop} का भाव ₹{latest_price:.0f} प्रति क्विंटल पर स्थिर रहा है।"
    else:
        change_phrase = f" कुल मिलाकर भाव में ₹{abs(total_change):.0f} की बढ़त दर्ज हुई है।" if total_change > 30 else (
            f" कुल मिलाकर भाव में ₹{abs(total_change):.0f} की गिरावट देखी गई है।" if total_change < -30 else
            " भाव सामान्य दायरे में स्थिर बने हुए हैं।"
        )
        summary_hi = f"किसान भाई, {time_label} {district} मंडी में {norm_crop} का भाव ₹{min_price:.0f} से ₹{max_price:.0f} प्रति क्विंटल के बीच रहा है।{change_phrase}"

    return json.dumps({
        "status": "success",
        "crop": norm_crop,
        "district": district,
        "market": market,
        "timeframe": timeframe or "recent_history",
        "price_range": f"₹{min_price:.0f} से ₹{max_price:.0f}",
        "min_price": min_price,
        "max_price": max_price,
        "latest_price": f"₹{latest_price:.0f}",
        "latest_date": latest_date,
        "trend_direction": trend,
        "trend_summary": advice,
        "price_change_rs": f"₹{diff:+.0f}",
        "companion_summary_hi": summary_hi
    }, ensure_ascii=False)


# -------------------------------------------------------------------------
# Tool 5: Consult Economic Specialist (Progressive Disclosure - Deep Holding/Freight)
# -------------------------------------------------------------------------
@traceable(name="Specialist:consult_economic_specialist", run_type="tool")
def consult_economic_specialist(
    crop: str,
    district: str,
    query_type: str = "holding_strategy",
    holding_days: int = 30,
    vehicle_type: str = "tractor",
    quantity_quintals: float = 50.0,
    state: Optional[str] = None
) -> str:
    """
    Summons the Specialized Economic Sub-Agent for deep holding storage ROI and vehicle freight logistics.
    Invoked ONLY on explicit demand when a farmer asks whether to store/hold or for detailed vehicle calculations.
    """
    from agents.specialists.economic_advisor import run_economic_specialist
    res = run_economic_specialist(
        query_type=query_type,
        crop=crop,
        district=district,
        holding_days=holding_days,
        vehicle_type=vehicle_type,
        quantity_quintals=quantity_quintals,
        state=state
    )
    return json.dumps(res, ensure_ascii=False)


# LiveKit Tools Export
try:
    from livekit.agents import llm
    get_crop_price_tool = llm.function_tool(description="Fetch wholesale mandi price for a crop in a district.")(get_crop_price)
    compare_mandi_arbitrage_tool = llm.function_tool(description="Compare prices across nearby mandis.")(compare_mandi_arbitrage)
    check_msp_floor_tool = llm.function_tool(description="Look up official Government MSP floor rate for a crop.")(check_msp_floor)
    get_crop_price_trend_tool = llm.function_tool(description="Analyzes historical price movement, trend direction, and multi-day/monthly price ranges.")(get_crop_price_trend)
    consult_economic_specialist_tool = llm.function_tool(description="Deep holding ROI, warehouse storage fees, and vehicle-specific freight calculations.")(consult_economic_specialist)
    LIVEKIT_TOOLS = [
        get_crop_price_tool,
        compare_mandi_arbitrage_tool,
        check_msp_floor_tool,
        get_crop_price_trend_tool,
        consult_economic_specialist_tool
    ]
except Exception:
    LIVEKIT_TOOLS = []


if __name__ == "__main__":
    print("[*] Testing Clean Modular Tools...")
    print("Price Tool:", get_crop_price("Wheat", "Jhansi"))
    print("\nArbitrage Tool:", compare_mandi_arbitrage("Wheat", "Jhansi"))
    print("\nMSP Tool:", check_msp_floor("Wheat"))

