"""
Agri_watch - LangGraph State Definition
Defines the central schema for conversational turns, extracted entities,
tool execution payloads, and spoken voice output.
"""

from typing import TypedDict, Optional, List, Dict, Any


class AgentState(TypedDict, total=False):
    # Turn Info
    turn_id: int
    user_query: str

    # Extracted Entities
    crop: Optional[str]
    district: Optional[str]
    state: Optional[str]

    # Routing & Intent Classification
    intent: str                  # "PRICE" | "ARBITRAGE" | "MSP" | "GREETING" | "OFF_TOPIC" | "CLARIFICATION" | "CONTINUATION"
    status: str                  # "proceed_to_llm" | "fast_exit" | "success" | "clarification" | "fallback"

    # Tool Execution
    tool_calls: Optional[List[Dict[str, Any]]]
    tool_results: Optional[List[Dict[str, Any]]]

    # Output Voice Response
    spoken_hindi_response: str

    # Persistent multi-turn session memory
    session_context: Dict[str, Any]
