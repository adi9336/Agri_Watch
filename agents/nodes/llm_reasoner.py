"""
Agri_watch - Groq LLM Reasoning & Tool Calling Engine
Uses Groq (Llama-3.3-70b-versatile) for ultra-low-latency (<250ms) Indic reasoning,
autonomous tool selection, and natural spoken Hindi response generation.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq

from agents.tools import get_crop_price, compare_mandi_arbitrage, check_msp_floor
from agents.state import AgentState
from agents.observability import traceable

logger = logging.getLogger("agriwatch.groq")

# 1. Define LangChain Structured Tools for LLM
@tool
def get_crop_price_tool(crop: str, district: str, state: str = "Uttar Pradesh") -> str:
    """
    Fetch the latest wholesale APMC mandi price, variety, and modal benchmark rate
    for an agricultural commodity in a district.
    """
    return get_crop_price(crop=crop, district=district, state=state)

@tool
def compare_mandi_arbitrage_tool(crop: str, district: str, state: str = "Uttar Pradesh") -> str:
    """
    Compare commodity prices across multiple APMC mandis within a district or neighboring
    region to find the highest-paying market and calculate transport net profit.
    """
    return compare_mandi_arbitrage(crop=crop, district=district, state=state)

@tool
def check_msp_floor_tool(crop: str) -> str:
    """
    Look up the official Government Minimum Support Price (MSP) floor rate for a crop.
    """
    return check_msp_floor(crop=crop)

LANGCHAIN_TOOLS = [get_crop_price_tool, compare_mandi_arbitrage_tool, check_msp_floor_tool]
TOOL_MAP = {t.name: t for t in LANGCHAIN_TOOLS}

# 2. Sovereign Indic System Prompt
SYSTEM_PROMPT = """आप एग्री-वॉच (Agri-Watch) हैं - भारतीय किसानों और ग्रामीण व्यापारियों के लिए आधिकारिक स्वतंत्र मंडी, आर्बिट्रेज और MSP सलाहकार।
आप सदैव सरल, आदरणीय, स्पष्ट और ठेठ ग्रामीण हिंदी में बात करते हैं।

आपके पास तीन प्रमुख टूल्स (Tools) हैं:
1. get_crop_price_tool: किसी जिले में किसी फसल (गेहूँ, धान, सरसों, चना, आदि) का ताज़ा मंडी भाव, न्यूनतम-अधिकतम व औसत (Modal) रेट पता करना।
2. compare_mandi_arbitrage_tool: आसपास की मंडियों के बीच भाव की तुलना करना, सबसे ज्यादा दाम देने वाली मंडी खोजना और ट्रैक्टर/ट्रॉली भाड़ा काटकर शुद्ध मुनाफा बताना।
3. check_msp_floor_tool: भारत सरकार का आधिकारिक न्यूनतम समर्थन मूल्य (MSP 2026-27) चेक करना ताकि किसान को कम दाम पर न बेचना पड़े।

नियम:
1. जब किसान किसी फसल का भाव पूछे, तो तुरंत `get_crop_price_tool` चलाएं।
2. जब किसान पूछे कि 'कहाँ बेचूँ', 'कहाँ ज्यादा फायदा होगा', या मंडियों की तुलना करे, तो `compare_mandi_arbitrage_tool` चलाएं।
3. जब किसान MSP या सरकारी भाव पूछे, तो `check_msp_floor_tool` चलाएं।
4. यदि किसान ने केवल जिला बताया और फसल नहीं बताई (या अधूरी बात की), तो मन से फसल न चुनें - सम्मानपूर्वक पूछें: "किसान भाई, आप किस फसल का भाव जानना चाहते हैं?"
5. यदि किसान केवल अभिवादन करे (जैसे "नमस्ते", "राम-राम", "हेलो"), तो आदरपूर्वक उत्तर दें और पूछें कि वे किस फसल का भाव जानना चाहते हैं।
6. यदि किसान पूर्व बातचीत के बाद "हाँ ठीक है", "बताओ" कहे, तो पिछली फसल को दोहराने के बजाय पूछें कि क्या वे किसी दूसरी फसल का भाव जानना चाहते हैं।
7. अंतिम उत्तर हमेशा आवाज़ (TTS) के लिए अनुकूलित शुद्ध हिंदी में दें। भाव को '₹X प्रति क्विंटल' स्पष्ट कहें।
"""


def get_groq_llm() -> Optional[ChatGroq]:
    """Instantiates ChatGroq if GROQ_API_KEY is available."""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        return None
    try:
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=600,
            api_key=groq_key
        )
    except Exception as e:
        logger.warning(f"[!] Could not initialize ChatGroq: {e}")
        return None


@traceable(name="LangGraphNode:GroqReasoner", run_type="llm")
def groq_reasoner_node(state: AgentState) -> Dict[str, Any]:
    """
    LLM Reasoning Node: Uses Groq (Llama-3.3-70b) to reason over farmer utterance,
    decide whether to call tools, execute tools, and formulate natural spoken Hindi.
    """
    llm = get_groq_llm()
    if not llm:
        # Fallback signal indicating Groq key is not configured
        return {"status": "llm_fallback"}

    query = state.get("user_query", "").strip()
    session_ctx = state.get("session_context") or {}

    # Build context message
    context_hint = ""
    if session_ctx.get("crop") or session_ctx.get("district"):
        context_hint = f"\n[पिछला संदर्भ: फसल={session_ctx.get('crop')}, जिला={session_ctx.get('district')}]"

    messages = [
        SystemMessage(content=SYSTEM_PROMPT + context_hint),
        HumanMessage(content=query)
    ]

    llm_with_tools = llm.bind_tools(LANGCHAIN_TOOLS)
    ai_msg: AIMessage = llm_with_tools.invoke(messages)

    # If the LLM decided to invoke tools:
    if ai_msg.tool_calls:
        logger.info(f"[*] Groq LLM autonomous tool calls: {ai_msg.tool_calls}")
        messages.append(ai_msg)

        for tc in ai_msg.tool_calls:
            t_name = tc.get("name")
            t_args = tc.get("args", {})
            selected_tool = TOOL_MAP.get(t_name)
            if selected_tool:
                try:
                    tool_output = selected_tool.invoke(t_args)
                except Exception as ex:
                    tool_output = f"Tool execution notice: {ex}"
                messages.append(ToolMessage(content=str(tool_output), tool_call_id=tc["id"]))

        # Second LLM turn: Synthesize final Hindi voice response using tool data
        final_ai_msg: AIMessage = llm.invoke(messages)
        spoken_response = final_ai_msg.content.strip()

        # Update persistent context if extracted
        updated_ctx = dict(session_ctx)
        for tc in ai_msg.tool_calls:
            args = tc.get("args", {})
            if "crop" in args:
                updated_ctx["crop"] = args["crop"]
            if "district" in args:
                updated_ctx["district"] = args["district"]

        return {
            "spoken_hindi_response": spoken_response,
            "status": "success",
            "session_context": updated_ctx
        }

    # Direct conversational response (e.g. greeting or clarification prompt)
    spoken_response = ai_msg.content.strip()
    return {
        "spoken_hindi_response": spoken_response,
        "status": "success"
    }
