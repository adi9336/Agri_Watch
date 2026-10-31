"""
Agri_watch - Agent Tools for Market Intelligence & Mandi Data Ingestion
Exposes callable tools for:
1. LiveKit VoiceAssistant (@llm.function_tool)
2. LangChain Agents (@tool)
3. Direct Python / Multi-Agent Execution
"""

import os
import sys
import json
from typing import Dict, Any, Optional, List

sys.stdout.reconfigure(encoding='utf-8')

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from mandi_tracker import MandiPriceService, normalize_date
from agents.steering_router import SteeringRouter, CROP_SYNONYMS
from agents.observability import traceable

# Initialize underlying engines
_router = SteeringRouter()
_service = _router.service


# -------------------------------------------------------------------------
# Tool 1: Get Crop Price
# -------------------------------------------------------------------------
@traceable(name="Agmarknet:get_crop_price", run_type="tool")
def get_crop_price(
    crop: str,
    district: str,
    state: str = "Uttar Pradesh",
    date: Optional[str] = None
) -> str:
    """
    Fetch the latest wholesale APMC mandi price, variety, min price, max price,
    and modal benchmark price for any agricultural commodity from Agmarknet.

    Args:
        crop: Name of the crop (e.g. Wheat, Paddy, Mustard, Onion, Gram Raw, Maize).
        district: Name of the district (e.g. Jhansi, Etah, Prayagraj, Sambhal, Rajkot).
        state: Name of the Indian state (default: "Uttar Pradesh").
        date: Optional date in DD/MM/YYYY or 'today' (default: None for today/latest).

    Returns:
        JSON string containing matching mandi records, arrival date, and modal prices.
    """
    # Normalize crop name using Indic synonyms
    norm_crop = CROP_SYNONYMS.get(crop.lower(), crop)
    res = _router.process_request(state=state, district=district, crop=norm_crop, date=date)
    
    output = {
        "crop": res["crop"],
        "district": res["district"],
        "state": res["state"],
        "reporting_date": res["reporting_date"],
        "is_live_today": res["is_live"],
        "records_count": res["records_count"],
        "mandis": [
            {
                "market": r.get("market"),
                "variety": r.get("variety"),
                "modal_price_rs_per_quintal": r.get("modal_price"),
                "min_price": r.get("min_price"),
                "max_price": r.get("max_price"),
                "arrival_date": r.get("arrival_date")
            } for r in res.get("records", [])[:5]
        ],
        "spoken_summary_hi": res["spoken_hindi_response"]
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


# -------------------------------------------------------------------------
# Tool 2: Compare Mandi Arbitrage
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
    or neighboring region to find the highest-paying market and calculate transport net profit.

    Args:
        crop: Name of the crop (e.g. Wheat, Mustard, Paddy, Groundnut).
        district: Home district (e.g. Jhansi, Rajkot, Karnal).
        state: State name (default: "Uttar Pradesh").
        quantity_quintals: Farmer produce quantity in quintals (default: 25.0).

    Returns:
        JSON string with top buyer mandi, price spread, and estimated net gain.
    """
    norm_crop = CROP_SYNONYMS.get(crop.lower(), crop)
    res = _router.process_request(state=state, district=district, crop=norm_crop)
    arb = res.get("arbitrage", {})
    
    output = {
        "crop": norm_crop,
        "district": district,
        "reporting_date": res.get("reporting_date"),
        "top_market": arb.get("top_market"),
        "top_price_rs_per_q": arb.get("top_modal"),
        "lowest_market": arb.get("lowest_market"),
        "lowest_price_rs_per_q": arb.get("lowest_modal"),
        "price_spread_rs_per_q": arb.get("spread"),
        "arbitrage_recommended": arb.get("recommend_arbitrage", False),
        "estimated_net_gain_for_trolley_load_rs": arb.get("estimated_net_gain_25q"),
        "advice_hi": res.get("spoken_hindi_response")
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


# -------------------------------------------------------------------------
# Tool 3: Check Govt MSP Floor Price
# -------------------------------------------------------------------------
@traceable(name="MSPPolicy:check_msp_floor", run_type="tool")
def check_msp_floor(crop: str) -> str:
    """
    Look up the official Government of India Minimum Support Price (MSP)
    for 2026-27 to check if market auction bids are below the government safety net.

    Args:
        crop: Name of the crop (e.g. Wheat, Paddy, Mustard, Barley, Gram).

    Returns:
        JSON string with official MSP rate, season (Rabi/Kharif), and Hindi crop name.
    """
    norm_crop = CROP_SYNONYMS.get(crop.lower(), crop)
    msp_val = _router.get_msp(norm_crop)
    
    if msp_val:
        output = {
            "crop": norm_crop,
            "msp_rate_rs_per_quintal": msp_val,
            "season": "Rabi" if norm_crop in ("Wheat", "Mustard", "Barley(Jau)", "Gram Raw(Chholia)", "Masur Dal") else "Kharif",
            "government_floor_status": "Active 2026-27 Government Procurement Guarantee",
            "notice_hi": f"सरकारी समर्थन मूल्य (MSP) ₹{msp_val} प्रति क्विंटल निर्धारित है।"
        }
    else:
        output = {
            "crop": norm_crop,
            "msp_rate_rs_per_quintal": None,
            "notice_hi": f"{norm_crop} के लिए कोई प्रत्यक्ष MSP दर अधिसूचित नहीं है (व्यापार बाजार भाव पर होता है)।"
        }
    return json.dumps(output, ensure_ascii=False, indent=2)


# -------------------------------------------------------------------------
# Tool 4: Find Alternative Mandis for Crop
# -------------------------------------------------------------------------
@traceable(name="Agmarknet:find_alternative_mandis", run_type="tool")
def find_alternative_mandis_for_crop(crop: str, state: str = "Uttar Pradesh") -> str:
    """
    Find active mandis in the state trading a specific commodity when that crop
    is not cultivated or has no arrivals in the farmer's immediate district (e.g. Paddy in Jhansi).

    Args:
        crop: Crop name (e.g. Paddy, Basmati, Cotton).
        state: State name (default: "Uttar Pradesh").

    Returns:
        JSON string listing the closest active mandis trading that crop with latest prices.
    """
    norm_crop = CROP_SYNONYMS.get(crop.lower(), crop)
    alternatives = []
    
    # 1. Try live state-level Agmarknet records
    try:
        _, state_matches, _ = _service.fetch_live_prices(state=state, crop=norm_crop)
    except Exception:
        state_matches = []
        
    # 2. Fall back to historical database if live is unavailable/empty
    if not state_matches:
        hist_records, _ = _service.fetch_historical(state=state, crop=norm_crop, max_results=10)
        state_matches = hist_records
        
    for r in state_matches[:8]:
        alternatives.append({
            "market": r.get("market"),
            "district": r.get("district"),
            "state": r.get("state"),
            "crop": r.get("commodity"),
            "variety": r.get("variety"),
            "modal_price": r.get("modal_price"),
            "date": r.get("arrival_date")
        })

    output = {
        "crop": norm_crop,
        "state": state,
        "alternative_mandis_count": len(alternatives),
        "mandis": alternatives
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


# -------------------------------------------------------------------------
# LiveKit FunctionTool Decorator Exports
# -------------------------------------------------------------------------
try:
    from livekit.agents import llm
    
    get_crop_price_tool = llm.function_tool(description="Fetch wholesale mandi price and variety for a crop in a district.")(get_crop_price)
    compare_mandi_arbitrage_tool = llm.function_tool(description="Compare prices across mandis in a district to find the highest bidder and transport profit.")(compare_mandi_arbitrage)
    check_msp_floor_tool = llm.function_tool(description="Look up official Government MSP floor rate for a crop.")(check_msp_floor)
    find_alternative_mandis_tool = llm.function_tool(description="Find active mandis in the state when a crop has no local arrivals.")(find_alternative_mandis_for_crop)
    
    LIVEKIT_TOOLS = [
        get_crop_price_tool,
        compare_mandi_arbitrage_tool,
        check_msp_floor_tool,
        find_alternative_mandis_tool
    ]
except Exception as e:
    LIVEKIT_TOOLS = []


if __name__ == "__main__":
    print("[*] Testing Agent Tools Module...\n")
    
    # Test 1: get_crop_price
    print("--- Test 1: get_crop_price(Wheat, Jhansi) ---")
    p_data = get_crop_price("Wheat", "Jhansi")
    print(p_data[:300] + "...\n")
    
    # Test 2: compare_mandi_arbitrage
    print("--- Test 2: compare_mandi_arbitrage(Wheat, Jhansi) ---")
    a_data = compare_mandi_arbitrage("Wheat", "Jhansi")
    print(a_data + "\n")
    
    # Test 3: check_msp_floor
    print("--- Test 3: check_msp_floor(Mustard) ---")
    m_data = check_msp_floor("Mustard")
    print(m_data + "\n")
    
    # Test 4: LiveKit Tool Exports
    print(f"[+] LiveKit Tools Exported: {len(LIVEKIT_TOOLS)} tools ready.")
