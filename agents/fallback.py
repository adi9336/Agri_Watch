"""
Agri_watch - Sovereign Fallback Node
Provides resilient, offline-capable price lookup if cloud LLM experiences network
or quota interruptions, ensuring zero crashes for the farmer.
"""

import json
from typing import Dict, Any
from agents.state import AgentState
from agents.tools import get_crop_price, check_msp_floor, CROP_NORM_MAP, DISTRICT_NORM_MAP
from agents.observability import traceable
from agents.i18n import normalize_language, t

HINDI_CROP_NAMES = {
    "Wheat": "गेहूँ",
    "Paddy": "धान",
    "Mustard": "सरसों",
    "Gram": "चना",
    "Peas(Dry)": "मटर",
    "Onion": "प्याज",
    "Potato": "आलू"
}


@traceable(name="LangGraphNode:SovereignFallback", run_type="chain")
def fallback_node(state: AgentState) -> Dict[str, Any]:
    """Fallback handler when cloud LLM is temporarily unavailable."""
    query = state.get("user_query", "").lower()
    session_ctx = state.get("session_context") or {}
    language = normalize_language(state.get("language"))

    # Extract crop
    crop = None
    has_crop = False
    for k, v in CROP_NORM_MAP.items():
        if k in query:
            crop = v
            has_crop = True
            break

    if not has_crop and not session_ctx.get("crop"):
        return {
            "intent": "CLARIFICATION",
            "spoken_hindi_response": t(language, "ask_crop"),
            "status": "clarification",
            "session_context": session_ctx
        }

    crop = crop or session_ctx.get("crop", "Wheat")
    hindi_crop = HINDI_CROP_NAMES.get(crop, crop) if language == "hi-IN" else crop

    # Extract district: from the sentence, else the one remembered from earlier (never guessed)
    district = next((norm_d for d, norm_d in DISTRICT_NORM_MAP.items() if d in query), None)
    district = district or session_ctx.get("district")

    # 1. MSP check
    if any(w in query for w in ["समर्थन मूल्य", "एमएसपी", "msp", "सरकारी भाव"]):
        msp_res = check_msp_floor(crop)
        data = json.loads(msp_res)
        if data.get("status") != "success":
            return {
                "intent": "MSP",
                "spoken_hindi_response": t(language, "no_msp", crop=hindi_crop),
                "status": "success",
                "session_context": session_ctx
            }
        msp_rate = data["msp_rate_per_quintal"]
        return {
            "intent": "MSP",
            "spoken_hindi_response": t(language, "msp", crop=hindi_crop, price=msp_rate),
            "status": "success",
            "session_context": session_ctx
        }

    # 2. Price discovery fallback: ask for the place rather than assume one
    if not district:
        return {
            "intent": "CLARIFICATION",
            "spoken_hindi_response": t(language, "ask_place", crop=hindi_crop),
            "status": "clarification",
            "session_context": session_ctx
        }

    price_res = get_crop_price(crop, district)
    data = json.loads(price_res)
    if data.get("status") == "no_current_price":
        # Remember crop and place so "nearest mandis" / "MSP" next turn needs no re-asking
        updated_ctx = {**session_ctx, "crop": crop, "district": district}
        key = "no_current_price_msp" if data.get("msp_available") else "no_current_price"
        return {
            "intent": "PRICE",
            "spoken_hindi_response": t(language, key, place=district, crop=hindi_crop),
            "status": "success",
            "crop": crop,
            "district": district,
            "session_context": updated_ctx
        }
    if data.get("status") != "success":
        return {
            "intent": "PRICE",
            "spoken_hindi_response": t(language, "no_price", place=district, crop=hindi_crop),
            "status": "success",
            "session_context": session_ctx
        }
    modal = data["modal_price"]
    market = data.get("market", district)

    updated_ctx = dict(session_ctx)
    updated_ctx["crop"] = crop
    updated_ctx["district"] = district
    return {
        "intent": "PRICE",
        "spoken_hindi_response": t(language, "price", market=market, crop=hindi_crop, price=f"{modal:.0f}"),
        "status": "success",
        "crop": crop,
        "district": district,
        "session_context": updated_ctx
    }

