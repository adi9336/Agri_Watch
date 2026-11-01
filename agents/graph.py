"""
Agri_watch - LangGraph Multi-Agent Cognitive Pipeline
Combines:
1. Fast-Path Guardrail & Scope Validation Node (Sub-millisecond exits for off-topic, greetings, and missing entities)
2. Groq LLM Autonomous Reasoning Node (Native tool calling for Mandi Prices, Arbitrage, and MSP)
3. Sovereign Fallback Node (Zero-crash resilience if cloud LLM is unavailable)
"""

import os
import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END

from agents.state import AgentState
from agents.guardrail import guardrail_node
from agents.llm_reasoner import llm_reasoner_node
from agents.fallback import fallback_node

logger = logging.getLogger("agriwatch.graph")


def route_guardrail(state: AgentState) -> str:
    """Routes based on scope guardrail check."""
    if state.get("status") == "fast_exit":
        return "fast_exit"
    return "proceed_to_llm"


def route_llm_result(state: AgentState) -> str:
    """Routes based on LLM execution status."""
    if state.get("status") == "fallback":
        return "fallback"
    return "success"


def build_agriwatch_graph():
    """Builds and compiles the consolidated 3-node Agri_watch LangGraph StateGraph."""
    workflow = StateGraph(AgentState)

    # 1. Register Nodes
    workflow.add_node("guardrail", guardrail_node)
    workflow.add_node("llm_reasoner", llm_reasoner_node)
    workflow.add_node("fallback", fallback_node)

    # 2. Define Flow & Conditional Edges
    workflow.add_edge(START, "guardrail")

    # Branching from Guardrail (Fast exits vs LLM processing)
    workflow.add_conditional_edges(
        "guardrail",
        route_guardrail,
        {
            "fast_exit": END,
            "proceed_to_llm": "llm_reasoner"
        }
    )

    # Branching from LLM Reasoner (Success vs Fallback)
    workflow.add_conditional_edges(
        "llm_reasoner",
        route_llm_result,
        {
            "success": END,
            "fallback": "fallback"
        }
    )

    workflow.add_edge("fallback", END)

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
    print("[*] Testing Consolidated Agri_watch LangGraph Architecture...")

    graph = get_agriwatch_graph()
    test_queries = [
        ("Greeting", "राम राम भैया"),
        ("Off-Topic Guardrail", "आज दिल्ली में मौसम कैसा है?"),
        ("Missing Crop Disambiguation", "झाँसी का भाव बताओ"),
        ("Price Discovery", "झाँसी में गेहूँ का क्या रेट है?"),
        ("Arbitrage Inquiry", "कहाँ बेचना फायदेमंद रहेगा गेहूँ?"),
        ("MSP Inquiry", "गेहूँ का सरकारी समर्थन मूल्य क्या है?"),
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
        print(f"Status : {output.get('status')}")
        print(f"Intent : {output.get('intent')}")
        print(f"Spoken : {output.get('spoken_hindi_response')}")
