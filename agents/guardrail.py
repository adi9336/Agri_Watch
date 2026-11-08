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
from agents.i18n import GREETING_WORDS, t

# -------------------------------------------------------------
# Agri_watch - Scope & Conversational Fast-Path Guardrail
# Intercepts off-topic queries, standalone greetings, and short affirmations
# in sub-millisecond time. Entity parsing & reasoning is left to the LLM.
# -------------------------------------------------------------

OFF_TOPIC_PATTERNS = {
    "मौसम", "बारिश", "weather", "rain", "तापमान",
    "कीड़ा", "कीट", "दवा", "कीटनाशक", "रोग", "बीमारी", "doctor", "disease", "pesticide",
    "खाद", "यूरिया", "dap", "उर्वरक", "fertilizer",
    "क्रिकेट", "मैच", "चुनाव", "राजनीति", "cricket", "election", "politics"
}

AFFIRMATION_WORDS = {
    "हाँ", "हां", "ठीक", "ठीक है", "अच्छा", "ok", "okay", "theek", "theek hai",
    "ओके", "राइट", "ओके राइट", "सही", "सही है", "अच्छा जी", "हाँजी", "जी", "शुक्रिया", "धन्यवाद"
}


@traceable(name="LangGraphNode:GuardrailAndScope", run_type="chain")
def guardrail_node(state: AgentState) -> Dict[str, Any]:
    """
    Validates user query against project boundary:
    1. Off-topic (Weather, Crop diseases, Politics) -> Fast Polite Redirect
    2. Standalone Affirmation (Haan, Ok, Theek hai) -> Prompt for next query (No repeat loops)
    3. Standalone Greeting (Namaste, Ram Ram) -> Fast Greeting
    4. Market Queries & Disambiguation -> Delegates to LLM Reasoner
    """
    query = state.get("user_query", "").strip()
    q_lower = query.lower()
    session_ctx = state.get("session_context") or {}
    language = state.get("language")

    # 1. Scope Guardrail: Off-Topic / Out of Scope Check (Tokenized boundary check)
    tokens = set(re.split(r'[\s,।!?;:()"\'-]+', q_lower))
    if tokens & OFF_TOPIC_PATTERNS:
        return {
            "intent": "OFF_TOPIC",
            "status": "fast_exit",
            "spoken_hindi_response": t(language, "off_topic"),
            "session_context": session_ctx
        }

    # 2. Conversational Fillers / Continuation (Prevents looping)
    words = q_lower.split()
    if len(words) <= 3 and any(w in AFFIRMATION_WORDS for w in [q_lower, " ".join(words[:2]), words[0]]):
        return {
            "intent": "CONTINUATION",
            "status": "fast_exit",
            "spoken_hindi_response": t(language, "continuation"),
            "session_context": session_ctx
        }

    # 3. Simple Standalone Greetings (only if short and purely a greeting)
    if len(words) <= 3 and any(w in GREETING_WORDS for w in [q_lower, " ".join(words[:2]), words[0]]):
        return {
            "intent": "GREETING",
            "status": "fast_exit",
            "spoken_hindi_response": t(language, "greet_reply"),
            "session_context": session_ctx
        }

    # 4. In-Scope Market Query -> Proceed to LLM Reasoner
    return {
        "status": "proceed_to_llm",
        "session_context": session_ctx
    }

