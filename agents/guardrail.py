"""
Agri_watch - Guardrail & Fast-Path Routing Node
Enforces project scope (Mandi Prices, Arbitrage, MSP only).
Handles greetings, affirmations, and missing entity clarifications directly
in sub-millisecond time without consuming LLM inference tokens.
"""

import re
from typing import Dict, Any, Optional
from agents.state import AgentState
from agents.observability import traceable

# Indic crop identifiers for fast disambiguation check
KNOWN_CROPS = [
    "गेहूँ", "गेहू", "gehu", "wheat", "धान", "dhan", "चावल", "paddy", "बासमती",
    "सरसों", "sarson", "mustard", "राई", "चना", "chana", "मूँग", "moong",
    "मसूर", "masur", "मटर", "matar", "अरहर", "तुअर", "arhar", "मक्का", "makka",
    "मूंगफली", "सोयाबीन", "प्याज", "pyaz", "कांदा", "टमाटर", "आलू", "alu"
]

KNOWN_DISTRICTS = [
    "झाँसी", "झांसी", "jhansi", "प्रयागराज", "prayagraj", "इलाहाबाद", "allahabad",
    "एटा", "etah", "सम्भल", "sambhal", "बदायूँ", "बदायूं", "badaun", "इटावा", "etawah",
    "ललितपुर", "lalitpur", "आगरा", "agra", "मथुरा", "mathura", "अलीगढ़", "aligarh",
    "राजकोट", "rajkot", "करनाल", "karnal", "लुधियाना", "ludhiana"
]


@traceable(name="LangGraphNode:GuardrailAndScope", run_type="chain")
def guardrail_node(state: AgentState) -> Dict[str, Any]:
    """
    Validates user query against project boundary:
    1. Off-topic (Weather, Crop diseases, Politics) -> Fast Polite Redirect
    2. Greetings (Namaste, Ram Ram) -> Fast Greeting
    3. Continuation (Haan, Ok, Theek hai) -> Prompt for next query (No repeat loops)
    4. Missing Crop (Only district mentioned) -> Clarification Prompt
    5. Valid Market Query -> Proceeds to LLM Reasoner
    """
    query = state.get("user_query", "").strip()
    q_lower = query.lower()
    session_ctx = state.get("session_context") or {}

    # -------------------------------------------------------------
    # 1. Scope Guardrail: Off-Topic / Out of Scope Check
    # (Strictly block crop diseases, weather, politics, non-mandi topics)
    # -------------------------------------------------------------
    off_topic_patterns = [
        "मौसम", "बारिश", "weather", "rain", "तापमान",
        "कीड़ा", "कीट", "दवा", "कीटनाशक", "रोग", "बीमारी", "doctor", "disease", "pesticide",
        "खाद", "यूरिया", "dap", "उर्वरक", "fertilizer",
        "क्रिकेट", "मैच", "चुनाव", "राजनीति", "cricket", "election", "politics"
    ]
    if any(p in q_lower for p in off_topic_patterns):
        return {
            "intent": "OFF_TOPIC",
            "status": "fast_exit",
            "spoken_hindi_response": "किसान भाई, मैं केवल कृषि मंडी भाव, मंडियों के मुनाफे की तुलना और सरकारी MSP का सलाहकार हूँ। कृपया मंडी भाव से जुड़ा प्रश्न पूछें।"
        }

    # -------------------------------------------------------------
    # 2. Conversational Fillers / Continuation (Prevents looping)
    # -------------------------------------------------------------
    is_affirmation = any(w in q_lower for w in ["हाँ", "ठीक है", "अच्छा", "ok", "okay", "theek hai"]) and len(query.split()) <= 4
    has_crop_mention = any(c in q_lower for c in KNOWN_CROPS)
    has_dist_mention = any(d in q_lower for d in KNOWN_DISTRICTS)

    if is_affirmation and not has_crop_mention and not has_dist_mention:
        return {
            "intent": "CONTINUATION",
            "status": "fast_exit",
            "spoken_hindi_response": "जी भाई! क्या आप किसी अन्य फसल या दूसरी मंडी का भाव जानना चाहते हैं?"
        }

    # -------------------------------------------------------------
    # 3. Simple Greetings
    # -------------------------------------------------------------
    is_greeting = any(w in q_lower for w in ["नमस्ते", "नमस्कार", "राम राम", "राम-राम", "प्रणाम", "हेलो", "hello", "hi", "hey"])
    if is_greeting and not has_crop_mention and not has_dist_mention:
        return {
            "intent": "GREETING",
            "status": "fast_exit",
            "spoken_hindi_response": "राम राम किसान भाई! बताइए, आप किस फसल या मंडी का भाव जानना चाहते हैं?"
        }

    # -------------------------------------------------------------
    # 4. Missing Crop Disambiguation
    # (Farmer mentioned a district but forgot to name the crop)
    # -------------------------------------------------------------
    if has_dist_mention and not has_crop_mention and not session_ctx.get("crop"):
        # Extract matched district name for a personalized prompt
        matched_dist = next((d for d in KNOWN_DISTRICTS if d in q_lower), "इस")
        return {
            "intent": "CLARIFICATION",
            "status": "fast_exit",
            "spoken_hindi_response": f"किसान भाई, {matched_dist} मंडी में आप किस फसल का भाव जानना चाहते हैं?"
        }

    # -------------------------------------------------------------
    # 5. In-Scope Agricultural Query -> Proceed to LLM Reasoner
    # -------------------------------------------------------------
    return {
        "status": "proceed_to_llm"
    }

