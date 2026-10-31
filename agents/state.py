"""
Agri_watch - LangGraph State Definition
Defines the central schema for conversational memory, Indic entity context,
specialist tool outputs, and spoken synthesis.
"""

from typing import TypedDict, Optional, List, Dict, Any


class AgentState(TypedDict, total=False):
    # Conversational turn info
    turn_id: int
    user_query: str
    language: str

    # Extracted Indic entities
    crop: Optional[str]             # Standard Agmarknet name (e.g., "Wheat", "Mustard")
    crop_hindi: Optional[str]       # Spoken Hindi name (e.g., "गेहूँ", "सरसों")
    district: Optional[str]         # Standard district (e.g., "Jhansi", "Prayagraj")
    district_hindi: Optional[str]   # Spoken Hindi district (e.g., "झाँसी", "प्रयागराज")
    state: Optional[str]            # Standard state (e.g., "Uttar Pradesh")

    # Routing & Intent
    intent: str                     # "PRICE_INQUIRY" | "ARBITRAGE" | "MSP" | "GREETING" | "CLARIFICATION" | "CONTINUATION" | "OFF_TOPIC"
    missing_entities: List[str]     # ["crop"], ["district"], or []

    # Specialist Agent Outputs
    mandi_records: Optional[List[Dict[str, Any]]]
    arbitrage_result: Optional[Dict[str, Any]]
    msp_comparison: Optional[Dict[str, Any]]

    # Response generation
    clarification_prompt: Optional[str]
    spoken_hindi_response: str
    status: str                     # "success" | "clarification" | "error"

    # Multi-turn persistent context
    session_context: Dict[str, Any]

