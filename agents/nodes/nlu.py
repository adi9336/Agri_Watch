"""
Agri_watch - LangGraph Indic NLU & Entity Extraction Node
Extracts crop names, districts, states, and farmer intent from spoken Indic input.
"""

import re
from typing import Dict, Any, Optional, Tuple, List
from agents.state import AgentState
from agents.observability import traceable

# Indic Crop Synonym Dictionary (Spoken names to official Agmarknet names)
CROP_SYNONYMS: Dict[str, str] = {
    # Wheat
    "गेहूँ": "Wheat", "गेहू": "Wheat", "गेहु": "Wheat", "कनक": "Wheat", "wheat": "Wheat",
    "gehu": "Wheat", "gehun": "Wheat", "kanak": "Wheat",
    # Paddy / Rice
    "धान": "Paddy", "चावल": "Paddy", "बासमती": "Paddy(Basmati)", "dhan": "Paddy",
    "chawal": "Paddy", "paddy": "Paddy", "rice": "Paddy",
    # Mustard
    "सरसों": "Mustard", "राई": "Mustard", "sarson": "Mustard", "mustard": "Mustard", "rai": "Mustard",
    "लाहा": "Mustard", "laha": "Mustard",
    # Gram / Pulses
    "चना": "Gram Raw(Chholia)", "छोलिया": "Gram Raw(Chholia)", "chana": "Gram Raw(Chholia)", "gram": "Gram Raw(Chholia)",
    "मूँग": "Green Gram(Moong)(Whole)", "मूंग": "Green Gram(Moong)(Whole)", "moong": "Green Gram(Moong)(Whole)",
    "मसूर": "Masur Dal", "masur": "Masur Dal",
    "मटर": "Peas(Dry)", "matar": "Peas(Dry)", "peas": "Peas(Dry)",
    "अरहर": "Arhar (Tur/Red Gram)(Whole)", "तुअर": "Arhar (Tur/Red Gram)(Whole)", "arhar": "Arhar (Tur/Red Gram)(Whole)",
    # Coarse cereals & Oilseeds
    "जौ": "Barley(Jau)", "jau": "Barley(Jau)", "barley": "Barley(Jau)",
    "मक्का": "Maize", "makka": "Maize", "bhutta": "Maize", "maize": "Maize",
    "मूंगफली": "Groundnut", "mungfali": "Groundnut", "groundnut": "Groundnut",
    "सोयाबीन": "Soyabean", "soyabean": "Soyabean",
    # Vegetables
    "प्याज": "Onion", "पियाज": "Onion", "कांदा": "Onion", "pyaz": "Onion", "onion": "Onion",
    "टमाटर": "Tomato", "tamatar": "Tomato", "tomato": "Tomato",
    "आलू": "Potato", "alu": "Potato", "potato": "Potato"
}

# Spoken Hindi Display Names for TTS
CROP_HINDI_NAMES: Dict[str, str] = {
    "Wheat": "गेहूँ",
    "Paddy": "धान",
    "Paddy(Basmati)": "बासमती धान",
    "Mustard": "सरसों",
    "Gram Raw(Chholia)": "चना",
    "Green Gram(Moong)(Whole)": "मूँग",
    "Masur Dal": "मसूर",
    "Peas(Dry)": "मटर",
    "Arhar (Tur/Red Gram)(Whole)": "अरहर",
    "Barley(Jau)": "जौ",
    "Maize": "मक्का",
    "Groundnut": "मूंगफली",
    "Soyabean": "सोयाबीन",
    "Onion": "प्याज",
    "Tomato": "टमाटर",
    "Potato": "आलू"
}

KNOWN_DISTRICTS: Dict[str, Tuple[str, str, str]] = {
    # Key: (Canonical District, Hindi District, State)
    "jhansi": ("Jhansi", "झाँसी", "Uttar Pradesh"),
    "झाँसी": ("Jhansi", "झाँसी", "Uttar Pradesh"),
    "झांसी": ("Jhansi", "झाँसी", "Uttar Pradesh"),
    "prayagraj": ("Prayagraj", "प्रयागराज", "Uttar Pradesh"),
    "प्रयागराज": ("Prayagraj", "प्रयागराज", "Uttar Pradesh"),
    "allahabad": ("Prayagraj", "प्रयागराज", "Uttar Pradesh"),
    "इलाहाबाद": ("Prayagraj", "प्रयागराज", "Uttar Pradesh"),
    "etah": ("Etah", "एटा", "Uttar Pradesh"),
    "एटा": ("Etah", "एटा", "Uttar Pradesh"),
    "sambhal": ("Sambhal", "सम्भल", "Uttar Pradesh"),
    "सम्भल": ("Sambhal", "सम्भल", "Uttar Pradesh"),
    "badaun": ("Badaun", "बदायूँ", "Uttar Pradesh"),
    "बदायूँ": ("Badaun", "बदायूँ", "Uttar Pradesh"),
    "बदायूं": ("Badaun", "बदायूँ", "Uttar Pradesh"),
    "etawah": ("Etawah", "इटावा", "Uttar Pradesh"),
    "इटावा": ("Etawah", "इटावा", "Uttar Pradesh"),
    "lalitpur": ("Lalitpur", "ललितपुर", "Uttar Pradesh"),
    "ललितपुर": ("Lalitpur", "ललितपुर", "Uttar Pradesh"),
    "agra": ("Agra", "आगरा", "Uttar Pradesh"),
    "आगरा": ("Agra", "आगरा", "Uttar Pradesh"),
    "mathura": ("Mathura", "मथुरा", "Uttar Pradesh"),
    "मथुरा": ("Mathura", "मथुरा", "Uttar Pradesh"),
    "aligarh": ("Aligarh", "अलीगढ़", "Uttar Pradesh"),
    "अलीगढ़": ("Aligarh", "अलीगढ़", "Uttar Pradesh"),
    "rajkot": ("Rajkot", "राजकोट", "Gujarat"),
    "राजकोट": ("Rajkot", "राजकोट", "Gujarat"),
    "karnal": ("Karnal", "करनाल", "Haryana"),
    "करनाल": ("Karnal", "करनाल", "Haryana"),
    "ludhiana": ("Ludhiana", "लुधियाना", "Punjab"),
    "लुधियाना": ("Ludhiana", "लुधियाना", "Punjab")
}


@traceable(name="LangGraphNode:IndicNLU", run_type="parser")
def nlu_node(state: AgentState) -> Dict[str, Any]:
    """
    Parses user utterance, extracts crop & district entities,
    determines intent, and resolves missing entities with session memory.
    """
    query = state.get("user_query", "").strip()
    q_lower = query.lower()
    session_ctx = state.get("session_context") or {}

    # 1. Entity Extraction
    extracted_crop: Optional[str] = None
    extracted_crop_hindi: Optional[str] = None
    extracted_dist: Optional[str] = None
    extracted_dist_hindi: Optional[str] = None
    extracted_state: Optional[str] = None

    for syn, canonical in CROP_SYNONYMS.items():
        if syn.lower() in q_lower:
            extracted_crop = canonical
            extracted_crop_hindi = CROP_HINDI_NAMES.get(canonical, syn)
            break

    for d_key, (canon_dist, hi_dist, canon_state) in KNOWN_DISTRICTS.items():
        if d_key.lower() in q_lower:
            extracted_dist = canon_dist
            extracted_dist_hindi = hi_dist
            extracted_state = canon_state
            break

    # Context inheritance from multi-turn memory
    resolved_crop = extracted_crop or session_ctx.get("crop")
    resolved_crop_hindi = extracted_crop_hindi or session_ctx.get("crop_hindi")
    resolved_dist = extracted_dist or session_ctx.get("district")
    resolved_dist_hindi = extracted_dist_hindi or session_ctx.get("district_hindi")
    resolved_state = extracted_state or session_ctx.get("state", "Uttar Pradesh")

    # If district is totally absent but crop is requested, set default regional baseline
    if resolved_crop and not resolved_dist:
        resolved_dist = "Jhansi"
        resolved_dist_hindi = "झाँसी"

    # 2. Intent Classification (Ordered by specificity)
    intent = "PRICE_INQUIRY"

    # Specific Specialist Inquiries first
    if any(w in q_lower for w in ["समर्थन मूल्य", "एमएसपी", "msp", "सरकारी भाव", "सरकारी रेट", "सरकारी गारंटी"]):
        intent = "MSP"

    elif any(w in q_lower for w in [
        "कहाँ बेचूं", "कहाँ बेचना", "कहा बेचू", "कहा बेचना", "ज्यादा मुनाफा", "मुनाफा कहाँ",
        "ज्यादा भाव कहाँ", "arbitrage", "pass wali mandi", "फायदेमंद", "मुनाफा", "तुलना"
    ]):
        intent = "ARBITRAGE"

    elif any(w in q_lower for w in ["तुम कौन", "आप कौन", "क्या काम", "क्या करते", "क्या मदद", "help", "who are you", "kya kar sakte"]):
        intent = "IDENTITY_HELP"

    elif any(w in q_lower for w in ["धन्यवाद", "शुक्रिया", "thanks", "thank you", "ठीक है धन्यवाद", "बहुत अच्छा"]):
        intent = "GRATITUDE"

    elif any(w in q_lower for w in ["मौसम", "बारिश", "weather", "rain", "cricket", "match", "election", "राजनीति"]):
        intent = "OFF_TOPIC"

    # Conversational Greeting (only if no specific crop/district was mentioned)
    elif any(w in q_lower for w in ["नमस्ते", "नमस्कार", "राम राम", "राम-राम", "प्रणाम", "हेलो", "hello", "hi", "hey"]) and not extracted_crop and not extracted_dist:
        intent = "GREETING"

    # Conversational Fillers / Continuation (only standalone affirmations without new entities)
    elif (re.search(r"(^|\s)(हाँ|अच्छा|ok|okay|बताओ|और बताओ|theek hai|aur batao|yes|sahi hai)($|\s|[?.!])", q_lower)) and not extracted_crop and not extracted_dist:
        intent = "CONTINUATION"

    # 3. Check for missing entities
    missing_entities: List[str] = []
    if intent in ("PRICE_INQUIRY", "MSP", "ARBITRAGE"):
        if not resolved_crop:
            missing_entities.append("crop")
        if not resolved_dist:
            missing_entities.append("district")

    # Update session context
    updated_ctx = dict(session_ctx)
    if resolved_crop:
        updated_ctx["crop"] = resolved_crop
        updated_ctx["crop_hindi"] = resolved_crop_hindi
    if resolved_dist:
        updated_ctx["district"] = resolved_dist
        updated_ctx["district_hindi"] = resolved_dist_hindi
    if resolved_state:
        updated_ctx["state"] = resolved_state

    return {
        "crop": resolved_crop,
        "crop_hindi": resolved_crop_hindi,
        "district": resolved_dist,
        "district_hindi": resolved_dist_hindi,
        "state": resolved_state,
        "intent": intent,
        "missing_entities": missing_entities,
        "session_context": updated_ctx
    }
