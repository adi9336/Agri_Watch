"""
Agri_watch - LangGraph Multi-Agent Cognitive Pipeline
Combines:
1. Groq LLM (Llama-3.3-70b) Autonomous Reasoning & Native Tool Calling (when GROQ_API_KEY is active)
2. Sovereign Indic State Fallback Pipeline (NLU, Clarification, Specialist Nodes, Synthesizer)
"""

import os
import logging
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END

from agents.state import AgentState
from agents.nodes.nlu import nlu_node
from agents.nodes.clarification import clarification_node
from agents.nodes.greeting import greeting_node
from agents.nodes.price_specialist import price_specialist_node
from agents.nodes.arbitrage_specialist import arbitrage_specialist_node
from agents.nodes.msp_specialist import msp_specialist_node
from agents.nodes.synthesizer import synthesizer_node
from agents.nodes.llm_reasoner import groq_reasoner_node

logger = logging.getLogger("agriwatch.graph")


def entry_router(state: AgentState) -> str:
    """Routes to Groq LLM reasoner if GROQ_API_KEY is set, else sovereign NLU."""
    if os.getenv("GROQ_API_KEY"):
        return "groq_reasoner"
    return "nlu"


def route_after_groq(state: AgentState) -> str:
    """Checks if Groq succeeded or needs fallback to sovereign Indic pipeline."""
    if state.get("status") == "llm_fallback":
        return "nlu"
    return END


def route_after_nlu(state: AgentState) -> str:
    """Conditional router determining next graph node based on intent and entity completeness."""
    intent = state.get("intent", "PRICE_INQUIRY")
    missing = state.get("missing_entities") or []

    # Non-transactional conversational turns
    if intent in ("GREETING", "IDENTITY_HELP", "GRATITUDE", "CONTINUATION", "OFF_TOPIC"):
        return "greeting"

    # Missing critical entities (e.g. crop missing)
    if "crop" in missing:
        return "clarification"

    # Transactional pricing pipeline
    return "price_specialist"


def build_agriwatch_graph():
    """Builds and compiles the Agri_watch LangGraph StateGraph."""
    workflow = StateGraph(AgentState)

    # 1. Register Nodes
    workflow.add_node("groq_reasoner", groq_reasoner_node)
    workflow.add_node("nlu", nlu_node)
    workflow.add_node("clarification", clarification_node)
    workflow.add_node("greeting", greeting_node)
    workflow.add_node("price_specialist", price_specialist_node)
    workflow.add_node("arbitrage_specialist", arbitrage_specialist_node)
    workflow.add_node("msp_specialist", msp_specialist_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # 2. Define Routing & Edges
    workflow.add_conditional_edges(
        START,
        entry_router,
        {
            "groq_reasoner": "groq_reasoner",
            "nlu": "nlu"
        }
    )

    # Branching from Groq LLM Node
    workflow.add_conditional_edges(
        "groq_reasoner",
        route_after_groq,
        {
            "nlu": "nlu",
            END: END
        }
    )

    # Conditional branching from Sovereign Indic NLU
    workflow.add_conditional_edges(
        "nlu",
        route_after_nlu,
        {
            "greeting": "greeting",
            "clarification": "clarification",
            "price_specialist": "price_specialist"
        }
    )

    # Terminal edges for non-data nodes
    workflow.add_edge("greeting", END)
    workflow.add_edge("clarification", END)

    # Specialist pipeline execution
    workflow.add_edge("price_specialist", "arbitrage_specialist")
    workflow.add_edge("arbitrage_specialist", "msp_specialist")
    workflow.add_edge("msp_specialist", "synthesizer")
    workflow.add_edge("synthesizer", END)

    # 3. Compile executable graph
    return workflow.compile()


# Singleton compiled graph instance
_compiled_graph = None

def get_agriwatch_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_agriwatch_graph()
    return _compiled_graph


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print("[*] Testing Agri_watch LangGraph (with Groq LLM integration)...")

    graph = get_agriwatch_graph()
    test_queries = [
        ("Greeting", "राम राम भैया"),
        ("Price Inquiry", "झाँसी में गेहूँ का क्या रेट है?"),
        ("Arbitrage Inquiry", "कहाँ बेचना फायदेमंद रहेगा गेहूँ?"),
        ("MSP Inquiry", "गेहूँ का सरकारी समर्थन मूल्य क्या है?"),
        ("Missing Crop", "झाँसी का भाव बताओ"),
        ("Continuation Affirmation", "हाँ ठीक है")
    ]

    session_ctx = {}
    for label, q in test_queries:
        print(f"\n--- Test: {label} ('{q}') ---")
        state_input: AgentState = {
            "turn_id": 1,
            "user_query": q,
            "session_context": session_ctx
        }
        output = graph.invoke(state_input)
        session_ctx = output.get("session_context", {})
        print(f"Spoken : {output.get('spoken_hindi_response')}")
