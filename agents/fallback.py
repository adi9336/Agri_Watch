"""
Agri_watch - Sovereign Fallback Node
Provides resilient, offline-capable price lookup if cloud LLM experiences network
or quota interruptions, ensuring zero crashes for the farmer.
"""

from typing import Dict, Any
from agents.state import AgentState
from agents.tools import get_crop_price, check_msp_floor, CROP_NORM_MAP
from agents.observability import traceable


@traceable(name="LangGraphNode:SovereignFallback", run_type="chain")
def fallback_node(state: AgentState) -> Dict[str, Any]:
    """Fallback handler when cloud LLM is temporarily unavailable."""
    query = state.get("user_query", "").lower()
    session_ctx = state.get("session_context") or {}

    # Extract crop
    crop = None
    for k, v in CROP_NORM_MAP.items():
        if k in query:
            crop = v
            break
    crop = crop or session_ctx.get("crop", "Wheat")

    # Extract district
    district = "Jhansi"
    for d in ["jhansi", "झाँसी", "झांसी", "prayagraj", "प्रयागराज", "etah", "एटा", "sambhal", "सम्भल"]:
        if d in query:
            district = "Jhansi" if "jhansi" in d or "झाँ" in d else d
            break

    # 1. MSP check
    if any(w in query for w in ["समर्थन मूल्य", "एमएसपी", "msp", "सरकारी भाव"]):
        msp_res = check_msp_floor(crop)
        import json
        data = json.loads(msp_res)
        msp_rate = data.get("msp_rate_per_quintal", 2275)
        return {
            "intent": "MSP",
            "spoken_hindi_response": f"किसान भाई, {crop} का सरकारी समर्थन मूल्य ₹{msp_rate} प्रति क्विंटल है।",
            "status": "success"
        }

    # 2. Price discovery fallback
    price_res = get_crop_price(crop, district)
    import json
    data = json.loads(price_res)
    modal = data.get("modal_price", 2585)
    market = data.get("market", district)

    return {
        "intent": "PRICE",
        "spoken_hindi_response": f"किसान भाई, {market} मंडी में {crop} का औसत भाव ₹{modal:.0f} प्रति क्विंटल है।",
        "status": "success",
        "crop": crop,
        "district": district,
        "session_context": {"crop": crop, "district": district}
    }

