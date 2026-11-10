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
    "alu": "Potato", "आलू": "Potato", "potato": "Potato",
    "soybean": "Soyabean", "soyabean": "Soyabean", "soya": "Soyabean", "सोयाबीन": "Soyabean",
    "maize": "Maize", "makka": "Maize", "corn": "Maize", "मक्का": "Maize",
    "groundnut": "Groundnut", "moongphali": "Groundnut", "peanut": "Groundnut", "मूंगफली": "Groundnut", "मूँगफली": "Groundnut",
    "urad": "Black Gram(Urad)", "उड़द": "Black Gram(Urad)", "black gram": "Black Gram(Urad)",
    "masur": "Masur Dal(Lentil)", "lentil": "Masur Dal(Lentil)", "मसूर": "Masur Dal(Lentil)",
    "barley": "Barley(Jau)", "jau": "Barley(Jau)", "जौ": "Barley(Jau)",
    "jowar": "Jowar", "jowar(sorghum)": "Jowar", "jwar": "Jowar", "sorghum": "Jowar", "ज्वार": "Jowar",
    "bajra": "Bajra", "pearl millet": "Bajra", "बाजरा": "Bajra",
    "ragi": "Ragi", "nachni": "Ragi", "mandua": "Ragi", "finger millet": "Ragi", "रागी": "Ragi", "नाचनी": "Ragi",
    "til": "Sesamum", "sesame": "Sesamum", "sesamum": "Sesamum", "तिल": "Sesamum",
    "ramtil": "Niger Seed", "niger": "Niger Seed", "nigerseed": "Niger Seed", "रामतिल": "Niger Seed",
    "sunflower": "Sunflower", "surajmukhi": "Sunflower", "सूरजमुखी": "Sunflower",
    "cotton": "Cotton", "kapas": "Cotton", "कपास": "Cotton",
    "copra": "Copra", "khopra": "Copra", "खोपरा": "Copra",
    "jute": "Jute", "pat": "Jute", "जूट": "Jute", "पटसन": "Jute",
    "tur": "Red gram", "tuar": "Red gram", "toor": "Red gram", "red gram/arhar/tur(whole)": "Red gram"
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

    # Today's rate asked but not uploaded: don't pass off an older rate as current,
    # let the agent offer the nearest mandis or the MSP instead
    if is_today and not records:
        msp_info = lookup_msp(norm_crop)
        return json.dumps({
            "status": "no_current_price",
            "crop": norm_crop,
            "district": district,
            "msp_available": bool(msp_info),
            "message": f"{district} मंडी में {norm_crop} का आज का भाव अभी अपलोड नहीं हुआ है।"
        }, ensure_ascii=False)

    # 2. Historical & nearest-date database lookup (a specific past date was asked)
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
        "verified_rate_rs_per_quintal": f"₹{modal_p:.0f}",
        **msp_comparison(norm_crop, modal_p)
    }, ensure_ascii=False)


# -------------------------------------------------------------------------
# Tool 2: Nearest Mandis Comparison (Only when asked where to sell / nearby mandis)
# -------------------------------------------------------------------------
DISTRICT_COORDS_PATH = os.path.join(PARENT_DIR, "data", "district_coords.json")
NEARBY_RADIUS_KM = 150      # Candidate search radius around the farmer's mandi
NEAREST_MANDI_COUNT = 5     # Mandis read out to the farmer
RECENT_WINDOW_DAYS = 60     # Prefer mandi rates reported within this many days
ROAD_FACTOR = 1.3           # Straight-line distance -> approximate road distance
_DISTRICT_COORDS: Optional[Dict[str, Dict[str, float]]] = None


def _district_key(district: str, state: str) -> str:
    return f"{(district or '').strip().lower()}|{(state or '').strip().lower()}"


def _load_district_coords() -> Dict[str, Dict[str, float]]:
    global _DISTRICT_COORDS
    if _DISTRICT_COORDS is None:
        _DISTRICT_COORDS = {}
        if os.path.exists(DISTRICT_COORDS_PATH):
            with open(DISTRICT_COORDS_PATH, "r", encoding="utf-8") as f:
                _DISTRICT_COORDS = json.load(f)
    return _DISTRICT_COORDS


def _road_km(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Approximate road distance between two district centroids (haversine x road factor)."""
    from math import radians, sin, cos, asin, sqrt
    lat1, lon1, lat2, lon2 = map(radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * asin(sqrt(h)) * ROAD_FACTOR


def _nearby_districts(district: str, state: str) -> Dict[str, float]:
    """Maps district|state keys within NEARBY_RADIUS_KM of the origin to their approximate road km."""
    coords = _load_district_coords()
    origin = coords.get(_district_key(district, state))
    if not origin:
        # No centroid for the origin: fall back to the curated neighbour list (distance unknown)
        names = [district] + NEIGHBORING_DISTRICTS.get(district, [])
        return {k: None for k in coords if k.split("|")[0] in {n.lower() for n in names}} or \
            {_district_key(n, state): None for n in names}
    nearby = {}
    for key, point in coords.items():
        km = _road_km(origin, point)
        if km <= NEARBY_RADIUS_KM:
            nearby[key] = km
    return nearby


def _parse_arrival_date(d_str: str) -> datetime:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime((d_str or "").strip(), fmt)
        except ValueError:
            pass
    return datetime.min


@traceable(name="NearbyMandis:compare_mandi_arbitrage", run_type="tool")
def compare_mandi_arbitrage(
    crop: str,
    district: str,
    state: Optional[str] = None
) -> str:
    """
    Lists the 5 mandis nearest to the farmer's mandi/district that recently reported the crop,
    sorted by rate (highest first). Transport cost is deliberately not estimated.
    Call this when a farmer asks where to sell or about nearby/other mandis.
    """
    norm_crop = CROP_NORM_MAP.get(crop.lower().strip(), crop.strip())
    resolved_dist, resolved_market, resolved_state = resolve_location(district, state)
    nearby = _nearby_districts(resolved_dist, resolved_state)
    nearby_names = {k.split("|")[0] for k in nearby}

    def _distance_for(r_dist: str, r_state: str) -> Optional[float]:
        key = _district_key(r_dist, r_state)
        if key in nearby:
            return nearby[key]
        # State names occasionally differ between datasets; fall back to district name only
        return next((km for k, km in nearby.items() if k.split("|")[0] == r_dist.strip().lower()), None)

    market_latest: Dict[str, Dict[str, Any]] = {}

    def _consider(row: Dict[str, Any]):
        r_dist = (row.get("district") or "").strip()
        if r_dist.lower() not in nearby_names or not is_commodity_match(norm_crop, row.get("commodity", "")):
            return
        m_clean = clean_market_name(row.get("market", ""))
        try:
            modal = float(row.get("modal_price", 0))
        except (ValueError, TypeError):
            return
        if not m_clean or modal <= 0:
            return
        r_date = (row.get("arrival_date") or "").strip()
        prev = market_latest.get(m_clean)
        if prev is None or _parse_arrival_date(r_date) > _parse_arrival_date(prev["arrival_date"]):
            km = _distance_for(r_dist, row.get("state", ""))
            market_latest[m_clean] = {
                "market": m_clean,
                "market_hi": MARKET_HI_MAP.get(m_clean, m_clean + " मंडी"),
                "district": r_dist,
                "modal_price": modal,
                "arrival_date": r_date,
                "distance_km": round(km) if km is not None else None
            }

    # 1. Live data.gov.in rates (state-wide records are filtered to nearby districts only)
    if _price_service.api_key:
        try:
            direct, state_wide, _ = _price_service.fetch_live_prices(resolved_state, resolved_dist, norm_crop)
            for r in (direct or []) + (state_wide or []):
                _consider(r)
        except Exception:
            pass

    # 2. Historical records from the local snapshot
    cache_file = _price_service.ensure_local_cache()
    if os.path.exists(cache_file):
        import csv
        with open(cache_file, mode="r", encoding="utf-8", errors="ignore") as f:
            for row in csv.DictReader(f):
                _consider(row)

    if not market_latest:
        return json.dumps({
            "status": "not_found",
            "crop": norm_crop,
            "district": district,
            "message": f"{district} और आसपास के क्षेत्र में {norm_crop} की कोई हालिया आवक दर्ज नहीं मिली है।"
        }, ensure_ascii=False)

    # Prefer recent rates (older ones only if too few mandis reported), then the nearest, then sort by rate
    now = datetime.now()
    recent = [m for m in market_latest.values()
              if (now - _parse_arrival_date(m["arrival_date"])).days <= RECENT_WINDOW_DAYS]
    if len(recent) < NEAREST_MANDI_COUNT:
        recent = list(market_latest.values())
    nearest = sorted(recent, key=lambda m: (m["distance_km"] is None, m["distance_km"] or 0))[:NEAREST_MANDI_COUNT]
    by_rate = sorted(nearest, key=lambda m: m["modal_price"], reverse=True)
    best = by_rate[0]

    today_str = datetime.now().strftime("%d/%m/%Y")
    crop_display = (lookup_msp(norm_crop) or {}).get("name_hi", norm_crop)
    place_display = clean_market_name(district)

    def _spoken(m: Dict[str, Any]) -> str:
        km = f" (लगभग {m['distance_km']} किमी)" if m["distance_km"] else ""
        return f"{m['market_hi']}{km} ₹{m['modal_price']:.0f}"

    companion_summary_hi = (
        f"किसान भाई, {place_display} के पास की {len(by_rate)} मंडियों में {crop_display} का भाव: "
        + ", ".join(_spoken(m) for m in by_rate)
        + f" प्रति क्विंटल। सबसे ऊँचा भाव {best['market_hi']} में है।"
    )

    return json.dumps({
        "status": "success",
        "crop": norm_crop,
        "district": district,
        "resolved_district": resolved_dist,
        "reporting_date": best["arrival_date"],
        "is_today": best["arrival_date"] == today_str,
        "best_market": best["market_hi"],
        "best_price": best["modal_price"],
        "price_difference": best["modal_price"] - by_rate[-1]["modal_price"],
        "distance_note": "Approximate road km between district centres; transport cost not estimated.",
        "nearby_mandis": [{
            "market": m["market_hi"],
            "district": m["district"],
            "distance_km": m["distance_km"],
            "modal_price": m["modal_price"],
            "rate_display": f"₹{m['modal_price']:.0f} प्रति क्विंटल",
            "arrival_date": m["arrival_date"]
        } for m in by_rate],
        "companion_summary_hi": companion_summary_hi,
        **msp_comparison(norm_crop, best["modal_price"])
    }, ensure_ascii=False)


def lookup_msp(norm_crop: str) -> Optional[Dict[str, Any]]:
    """Returns the 2026-27 MSP entry for a normalized crop name, or None if not notified."""
    msp_data = {}
    if os.path.exists(MSP_FILE):
        with open(MSP_FILE, "r", encoding="utf-8") as f:
            msp_data = json.load(f).get("2026_27", {})
    for k, v in msp_data.items():
        if k.lower() in norm_crop.lower() or norm_crop.lower() in k.lower():
            return v
    return None


def msp_comparison(norm_crop: str, price: float) -> Dict[str, Any]:
    """Compares a mandi price against MSP so the agent can warn when the farmer is offered less."""
    info = lookup_msp(norm_crop)
    if not info or not price:
        return {"msp": None, "below_msp": False}
    msp = float(info["msp"])
    return {
        "msp": msp,
        "below_msp": price < msp,
        "msp_gap_per_quintal": round(msp - price) if price < msp else 0
    }


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
    found_info = lookup_msp(norm_crop)

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
# Tool 5: Hold-or-Sell Advisor (Progressive Disclosure - only on explicit storage questions)
# -------------------------------------------------------------------------
@traceable(name="Specialist:consult_economic_specialist", run_type="tool")
def consult_economic_specialist(
    crop: str,
    district: str,
    holding_days: int = 30,
    quantity_quintals: Optional[float] = None,
    state: Optional[str] = None
) -> str:
    """
    Decides whether storing a crop for holding_days is likely to beat selling today,
    from the recent price trend versus warehouse rent, handling, storage loss and interest.
    Invoked ONLY when a farmer explicitly asks about holding, storing or warehouse costs.
    """
    from agents.specialists.economic_advisor import run_economic_specialist
    res = run_economic_specialist(
        crop=crop,
        district=district,
        holding_days=holding_days,
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
    consult_economic_specialist_tool = llm.function_tool(description="Hold-or-sell advice: recent price trend versus warehouse storage cost.")(consult_economic_specialist)
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

