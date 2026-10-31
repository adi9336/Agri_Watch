"""
Agri_watch - LangGraph Multi-Agent Cognitive Pipeline
Assembles and compiles the StateGraph connecting Indic NLU, Guardrail Clarification,
Specialist Price/Arbitrage/MSP nodes, and Indic Spoken Synthesis.
"""

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
    workflow.add_node("nlu", nlu_node)
    workflow.add_node("clarification", clarification_node)
    workflow.add_node("greeting", greeting_node)
    workflow.add_node("price_specialist", price_specialist_node)
    workflow.add_node("arbitrage_specialist", arbitrage_specialist_node)
    workflow.add_node("msp_specialist", msp_specialist_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # 2. Define Edges & Flow
    workflow.add_edge(START, "nlu")

    # Conditional branching from NLU
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
    print("[*] Testing Agri_watch LangGraph Compilation & Execution...")

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
        print(f"Intent : {output.get('intent')}")
        print(f"Crop   : {output.get('crop')} ({output.get('crop_hindi')})")
        print(f"Dist   : {output.get('district')} ({output.get('district_hindi')})")
        print(f"Spoken : {output.get('spoken_hindi_response')}")
