"""
Agri_watch - LangGraph Conversational Protocol & Greeting Node
Handles farmer greetings, gratitude, continuation prompts, identity questions,
and graceful off-topic guardrails.
"""

from typing import Dict, Any
from agents.state import AgentState
from agents.observability import traceable


@traceable(name="LangGraphNode:GreetingAndGuardrails", run_type="chain")
def greeting_node(state: AgentState) -> Dict[str, Any]:
    """Handles non-transactional conversational turns with respect and natural Indic tone."""
    intent = state.get("intent", "GREETING")
    crop_hi = state.get("crop_hindi")
    dist_hi = state.get("district_hindi")

    if intent == "GREETING":
        resp = "हाँ किसान भाई, राम राम! आप किस फसल का मंडी भाव या सरकारी MSP जानना चाहते हैं?"

    elif intent == "IDENTITY_HELP":
        resp = (
            "मैं एग्री-वॉच हूँ - भारतीय किसानों के लिए स्वतंत्र मंडी और मूल्य सलाहकार। "
            "मैं आपको सरकारी एगमार्कनेट के ताज़ा थोक भाव, मंडियों के बीच मुनाफे का अंतर और "
            "न्यूनतम समर्थन मूल्य (MSP) की सही जानकारी देता हूँ। आप किसी भी फसल का नाम बताएं।"
        )

    elif intent == "GRATITUDE":
        resp = "बहुत-बहुत धन्यवाद किसान भाई! किसी भी फसल या मंडी का भाव जानने के लिए कभी भी पूछें। आपका दिन शुभ हो!"

    elif intent == "CONTINUATION":
        if crop_hi:
            resp = f"जी भाई! {crop_hi} के अलावा क्या आप किसी अन्य फसल (जैसे चना, सरसों, मटर) या किसी दूसरे जिले का भाव जानना चाहते हैं?"
        else:
            resp = "जी किसान भाई! आप किस फसल या किस मंडी का ताज़ा भाव देखना चाहते हैं?"

    elif intent == "OFF_TOPIC":
        resp = (
            "किसान भाई, मैं विशेष रूप से कृषि मंडी भाव, मंडियों के मुनाफे की तुलना और सरकारी MSP का "
            "सलाहकार हूँ। कृपया फसल (जैसे गेहूँ, चना, सरसों) या मंडी से जुड़ा प्रश्न पूछें।"
        )

    else:
        resp = "नमस्ते किसान भाई! मैं आपकी क्या सहायता कर सकता हूँ?"

    return {
        "spoken_hindi_response": resp,
        "status": "success"
    }
