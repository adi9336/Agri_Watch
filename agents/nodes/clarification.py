"""
Agri_watch - LangGraph Clarification & Disambiguation Node
Handles incomplete entities gracefully with polite spoken Indic prompts.
"""

from typing import Dict, Any
from agents.state import AgentState
from agents.observability import traceable


@traceable(name="LangGraphNode:Clarification", run_type="chain")
def clarification_node(state: AgentState) -> Dict[str, Any]:
    """Generates polite clarification prompts in Hindi when mandatory entities are missing."""
    missing = state.get("missing_entities") or []
    district_hi = state.get("district_hindi") or state.get("district")

    if "crop" in missing and district_hi:
        prompt = f"किसान भाई, {district_hi} मंडी में आप किस फसल का भाव जानना चाहते हैं? जैसे गेहूँ, सरसों, चना या मटर?"
    elif "crop" in missing and not district_hi:
        prompt = "किसान भाई, आप किस फसल का मंडी भाव या समर्थन मूल्य जानना चाहते हैं? मुझे फसल और जिले का नाम बताएं।"
    elif "district" in missing:
        crop_hi = state.get("crop_hindi") or "फसल"
        prompt = f"किसान भाई, आप {crop_hi} का भाव किस जिले या मंडी में देखना चाहते हैं? जैसे झाँसी, प्रयागराज या एटा?"
    else:
        prompt = "किसान भाई, कृपया फसल और अपने जिले का नाम बताएं ताकि मैं आपको ताज़ा मंडी भाव बता सकूँ।"

    return {
        "clarification_prompt": prompt,
        "spoken_hindi_response": prompt,
        "status": "clarification"
    }

