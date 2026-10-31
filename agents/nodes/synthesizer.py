"""
Agri_watch - LangGraph Indic Spoken Synthesizer Node
Transforms multi-agent analytical data into pure, respectful, highly legible
spoken Hindi optimized for Gnani Timbre TTS phonetics.
"""

import re
from typing import Dict, Any, List
from agents.state import AgentState
from agents.observability import traceable


def clean_market_name(market: str) -> str:
    """Cleans APMC codes and English artifacts for natural Hindi speech."""
    if not market:
        return "मंडी"
    clean = re.sub(r"\bAPMC\b", "", market, flags=re.IGNORECASE)
    clean = re.sub(r"\(.*?\)", "", clean)
    clean = clean.strip()
    return f"{clean} मंडी" if not clean.endswith("मंडी") else clean


@traceable(name="LangGraphNode:IndicSynthesizer", run_type="chain")
def synthesizer_node(state: AgentState) -> Dict[str, Any]:
    """
    Synthesizes conversational, spoken Hindi response tailored for Indic voice engines.
    """
    # 1. If a clarification or greeting prompt already exists, pass it through
    if state.get("spoken_hindi_response"):
        return {"spoken_hindi_response": state["spoken_hindi_response"]}

    intent = state.get("intent", "PRICE_INQUIRY")
    crop = state.get("crop")
    crop_hi = state.get("crop_hindi") or crop or "फसल"
    district = state.get("district")
    district_hi = state.get("district_hindi") or district or "मंडी"
    records = state.get("mandi_records") or []
    arbitrage = state.get("arbitrage_result") or {}
    msp_info = state.get("msp_comparison") or {}
    is_live = state.get("is_live", False)
    reporting_date = state.get("reporting_date")

    # -------------------------------------------------------------
    # Case A: Explicit MSP Inquiry
    # -------------------------------------------------------------
    if intent == "MSP":
        if msp_info and msp_info.get("msp_rate"):
            msp_val = msp_info["msp_rate"]
            resp = (
                f"किसान भाई, 2026-27 के लिए {crop_hi} का सरकारी समर्थन मूल्य (MSP) "
                f"₹{msp_val} प्रति क्विंटल निर्धारित है। यदि कोई व्यापारी इससे कम बोली लगाता है, "
                f"तो आप सरकारी खरीद केंद्र पर संपर्क कर सकते हैं।"
            )
        else:
            resp = f"{crop_hi} के लिए कोई प्रत्यक्ष MSP दर अधिसूचित नहीं है, इसका व्यापार मंडी में खुली बोली पर होता है।"
        return {"spoken_hindi_response": resp, "status": "success"}

    # -------------------------------------------------------------
    # Case B: Arbitrage & Logistics Inquiry
    # -------------------------------------------------------------
    if intent == "ARBITRAGE":
        if arbitrage and arbitrage.get("recommend_arbitrage"):
            top_m = clean_market_name(arbitrage.get("top_market", ""))
            top_p = arbitrage.get("top_modal", 0)
            low_m = clean_market_name(arbitrage.get("lowest_market", ""))
            spread = arbitrage.get("spread", 0)
            net_gain = arbitrage.get("estimated_net_gain_25q", 0)
            resp = (
                f"किसान भाई, {crop_hi} के लिए सबसे बढ़िया भाव {top_m} में ₹{top_p:.0f} प्रति क्विंटल है। "
                f"पास की {low_m} की तुलना में यहाँ ₹{spread:.0f} प्रति क्विंटल अधिक मिल रहा है। "
                f"ट्रॉली (25 क्विंटल) ले जाने पर भाड़ा काटकर लगभग ₹{net_gain:.0f} का शुद्ध मुनाफा होगा।"
            )
        else:
            resp = f"किसान भाई, {district_hi} क्षेत्र की मंडियों में {crop_hi} का भाव लगभग बराबर चल रहा है। आप निकटतम मंडी में ही माल दे सकते हैं।"
        return {"spoken_hindi_response": resp, "status": "success"}

    # -------------------------------------------------------------
    # Case C: Standard Mandi Price Discovery
    # -------------------------------------------------------------
    if not records:
        resp = f"क्षमा करें किसान भाई, {district_hi} मंडी में {crop_hi} का ताज़ा भाव उपलब्ध नहीं हो पाया है। कृपया थोड़ी देर बाद पुनः प्रयास करें।"
        return {"spoken_hindi_response": resp, "status": "no_data"}

    top_record = records[0]
    market_clean = clean_market_name(top_record.get("market", district_hi))
    variety = top_record.get("variety", "सामान्य")
    variety_clean = re.sub(r"\(.*?\)", "", variety).strip()

    try:
        modal_p = float(top_record.get("modal_price", 0))
        min_p = float(top_record.get("min_price", 0))
        max_p = float(top_record.get("max_price", 0))
    except (ValueError, TypeError):
        modal_p = min_p = max_p = 0

    # Build primary price sentence
    if is_live:
        date_intro = "आज"
    elif reporting_date:
        date_intro = f"{reporting_date} को"
    else:
        date_intro = "हाल ही में"

    sentences = [
        f"किसान भाई, {market_clean} में {date_intro} {crop_hi} ({variety_clean}) का औसत भाव ₹{modal_p:.0f} प्रति क्विंटल रहा।"
    ]

    if min_p > 0 and max_p > min_p:
        sentences.append(f"नीलामी ₹{min_p:.0f} से ₹{max_p:.0f} के बीच हुई।")

    # MSP benchmark check alert
    if msp_info and msp_info.get("msp_rate"):
        msp_rate = msp_info["msp_rate"]
        if modal_p > 0 and modal_p < msp_rate:
            deficit = msp_rate - modal_p
            sentences.append(
                f"ध्यान दें, यह भाव सरकारी MSP (₹{msp_rate}) से ₹{deficit:.0f} कम है। "
                f"संभव हो तो सरकारी खरीद केंद्र पर बेचें।"
            )

    # Multi-mandi arbitrage opportunity cue
    if arbitrage and arbitrage.get("recommend_arbitrage") and arbitrage.get("top_market") != top_record.get("market"):
        alt_m = clean_market_name(arbitrage.get("top_market", ""))
        alt_p = arbitrage.get("top_modal", 0)
        sentences.append(
            f"पास की {alt_m} में भाव ₹{alt_p:.0f} चल रहा है, जहाँ आपको बेहतर दाम मिल सकता है।"
        )

    spoken_text = " ".join(sentences)
    return {
        "spoken_hindi_response": spoken_text,
        "status": "success"
    }

