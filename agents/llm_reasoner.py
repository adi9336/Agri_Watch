"""
Agri_watch - Groq LLM Autonomous Reasoner & Tool Calling Node
Acts as the deliberative cognitive engine for Mandi Pricing, Multi-Mandi Arbitrage,
and MSP Benchmarks with strict voice conciseness rules.
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

from agents.tools import get_crop_price, compare_mandi_arbitrage, check_msp_floor, get_crop_price_trend
from agents.state import AgentState
from agents.observability import traceable

logger = logging.getLogger("agriwatch.reasoner")

# 1. Define LangChain Structured Tools for LLM
@tool
def get_crop_price_tool(
    crop: str,
    district: str,
    state: Optional[str] = None,
    date: Optional[str] = None
) -> str:
    """
    Fetch wholesale APMC mandi price and modal rate for any crop in a district.
    Strictly pass a date. If the farmer did not mention a date, pass date='today'.
    If today's auction rate is not yet published on the portal, it automatically retrieves the nearest available date.
    Args:
        crop: Name of the crop (e.g. 'Wheat', 'Gram', 'Mustard')
        district: Name of the district (e.g. 'Jhansi', 'Agra', 'Katni')
        state: State name (optional, e.g. 'Madhya Pradesh', 'Uttar Pradesh')
        date: Target date ('today', 'yesterday', 'पिछले हफ्ते', or 'DD/MM/YYYY'). Defaults to 'today'.
    """
    if not date:
        date = "today"
    return get_crop_price(crop=crop, district=district, state=state, date=date)

@tool
def compare_mandi_arbitrage_tool(crop: str, district: str, state: str = "Uttar Pradesh") -> str:
    """
    Compare commodity prices across multiple APMC mandis within a district
    to find the highest-paying market and calculate transport net profit.
    Call this ONLY when a farmer asks where to sell, asks for higher profit, or asks to compare mandis.
    """
    return compare_mandi_arbitrage(crop=crop, district=district, state=state)

@tool
def check_msp_floor_tool(crop: str) -> str:
    """
    Look up the official Government Minimum Support Price (MSP) floor rate for a crop.
    Call this ONLY when a farmer asks about MSP, government rate, or minimum guaranteed price.
    """
    return check_msp_floor(crop=crop)

@tool
def get_crop_price_trend_tool(crop: str, district: str, state: str = "Uttar Pradesh") -> str:
    """
    Analyzes historical price movement and trend direction (Rising / Falling / Stable) for a crop in a district.
    Call this ONLY when a farmer asks whether prices are rising, falling, or if they should sell now or wait.
    """
    return get_crop_price_trend(crop=crop, district=district, state=state)

LANGCHAIN_TOOLS = [get_crop_price_tool, compare_mandi_arbitrage_tool, check_msp_floor_tool, get_crop_price_trend_tool]
TOOL_MAP = {t.name: t for t in LANGCHAIN_TOOLS}

# 2. Strict Voice Agent System Prompt
SYSTEM_PROMPT = """आप एग्री-वॉच (Agri-Watch) हैं - भारतीय किसानों के लिए एक सरल, सटीक और संक्षेप में बोलने वाले वॉयस असिस्टेंट।
आपका उत्तर सीधे स्पीकर पर आवाज़ (TTS) द्वारा किसान को सुनाया जाता है।

सख्त नियम (STRICT VOICE RULES):
1. केवल वही बताएं जो किसान ने पूछा है (कदापि बिना पूछे अतिरिक्त विवरण न दें):
   - यदि किसान किसी फसल का भाव पूछे (जैसे 'झाँसी में गेहूँ का भाव क्या है?' या 'aaj agra me chane ka kya bhav he'): केवल `get_crop_price_tool` चलाएं और उस मंडी का भाव 1 वाक्य में बताएं (जैसे: 'किसान भाई, आगरा मंडी में चने का भाव ₹6,640 प्रति क्विंटल रहा है।')।
   - बिना पूछे अपने मन से कभी भी MSP की बात न जोड़ें, न ही दूसरी मंडियों की तुलना करें।
   - जब किसान स्पष्ट पूछे कि 'कहाँ बेचूँ', 'मुनाफा कहाँ है', या मंडियों की तुलना करे: केवल तभी `compare_mandi_arbitrage_tool` चलाएं और सबसे ज्यादा दाम देने वाली मंडी बताएं।
   - जब किसान 'सरकारी भाव' या 'MSP' पूछे: केवल तभी `check_msp_floor_tool` चलाएं और समर्थन मूल्य बताएं।
   - जब किसान पूछे कि 'भाव बढ़ रहे हैं या घट रहे हैं', 'मंडी का रुझान क्या है', या 'अभी बेचूँ या रुकूँ': केवल तभी `get_crop_price_trend_tool` चलाएं और भाव का रुझान बताएं।
2. अस्पष्ट या अधूरी जानकारी पर स्पष्टीकरण (Clarification Rules):
   - यदि किसान केवल मंडी या जिले का नाम ले लेकिन फसल न बताए (जैसे 'झाँसी का भाव बताओ'): कोई टूल न चलाएं। सीधे पूछें: 'किसान भाई, [मंडी] में आप किस फसल का भाव जानना चाहते हैं?'
   - यदि किसान केवल फसल का नाम ले लेकिन जिला न बताए (जैसे 'चने का क्या भाव है'): कोई टूल न चलाएं। सीधे पूछें: 'किसान भाई, [फसल] का भाव जानने के लिए कृपया अपना जिला या मंडी बताइए।'
   - यदि सवाल में या पिछली बातचीत के संदर्भ में फसल और जिला दोनों मौजूद हों (जैसे पहले 'चना' और फिर 'आगरा'): तुरंत `get_crop_price_tool` चलाएं।
3. उत्तर की लंबाई: केवल 1 से 2 छोटे वाक्य। कोई लंबा भाषण, तारीखों की भरमार या गैर-ज़रूरी लिस्ट नहीं देनी है।
4. वाक्-अनुकूल (Voice Friendly) फॉर्मेटिंग:
   - कोई मार्कडाउन चिन्ह (जैसे **, *, #, बुलेट पॉइंट्स) बिल्कुल न लगाएं।
   - कोई इमोजी (जैसे 🙏) न लगाएं, क्योंकि वॉयस इंजन उन्हें गलत बोलता है।
   - भाव को हमेशा '₹X प्रति क्विंटल' साफ़ हिंदी में लिखें।
5. तारीख (Date) का सख्त नियम:
   - `get_crop_price_tool` चलाते समय सदैव `date` पास करें: यदि किसान ने कोई तारीख न बोली हो, तो अनिवार्य रूप से `date='today'` पास करें। यदि 'कल' का पूछे तो `date='yesterday'`, यदि ख़ास तारीख पूछे तो वह तारीख पास करें।
   - यदि आज का लाइव भाव मिला हो (`is_today=true`): 'किसान भाई, आज [मंडी] में [फसल] का भाव ₹X प्रति क्विंटल है।' बोलें।
   - यदि आज का भाव अभी दर्ज न हुआ हो और टूल ने नजदीकी तारीख का भाव दिया हो (`is_exact_date=false`): साफ़ बताएं: 'किसान भाई, आज का भाव अभी दर्ज नहीं हुआ है, [reporting_date] को [मंडी] में [फसल] का भाव ₹X प्रति क्विंटल रहा था।'
   - यदि किसान ने विशेष तारीख पूछी हो: '[reporting_date] को [मंडी] में [फसल] का भाव ₹X प्रति क्विंटल रहा था।' बोलें।
"""

_active_groq_model: Optional[str] = None


def resolve_groq_model(groq_key: str) -> str:
    """Dynamically resolves the active chat model on Groq."""
    global _active_groq_model
    if _active_groq_model:
        return _active_groq_model

    env_model = os.getenv("GROQ_MODEL")
    if env_model:
        _active_groq_model = env_model
        return _active_groq_model

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        available_ids = [m.id for m in client.models.list().data]

        preferences = [
            "openai/gpt-oss-120b",
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant"
        ]
        for pref in preferences:
            if pref in available_ids:
                _active_groq_model = pref
                logger.info(f"[*] Auto-selected Groq model: {_active_groq_model}")
                return _active_groq_model

        chat_models = [m for m in available_ids if not m.startswith("whisper") and "guard" not in m]
        if chat_models:
            _active_groq_model = chat_models[0]
            return _active_groq_model
    except Exception as e:
        logger.warning(f"[!] Groq model auto-resolve warning: {e}")

    _active_groq_model = "qwen/qwen3.8-27b"
    return _active_groq_model


def get_groq_llm() -> Optional[ChatGroq]:
    """Instantiates ChatGroq if GROQ_API_KEY is available."""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        return None
    try:
        model_name = resolve_groq_model(groq_key)
        return ChatGroq(
            model=model_name,
            temperature=0.1,
            max_tokens=300,
            api_key=groq_key
        )
    except Exception as e:
        logger.warning(f"[!] Could not initialize ChatGroq: {e}")
        return None


@traceable(name="LangGraphNode:LLMReasoner", run_type="llm")
def llm_reasoner_node(state: AgentState) -> Dict[str, Any]:
    """
    Deliberative LLM Reasoning Node: Uses Groq to reason, select tools,
    and formulate concise, spoken-ready Hindi answers.
    """
    llm = get_groq_llm()
    if not llm:
        return {"status": "fallback"}

    query = state.get("user_query", "").strip()
    session_ctx = dict(state.get("session_context") or {})
    chat_history = session_ctx.get("chat_history") or []

    context_parts = []
    if session_ctx.get("crop"):
        context_parts.append(f"फसल={session_ctx['crop']}")
    if session_ctx.get("district"):
        context_parts.append(f"जिला={session_ctx['district']}")
    context_hint = f"\n[सत्र संदर्भ: {', '.join(context_parts)}]" if context_parts else ""

    messages = [SystemMessage(content=SYSTEM_PROMPT + context_hint)]
    # Feed recent conversational context (last 4 turns)
    for msg in chat_history[-4:]:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=query))

    try:
        llm_with_tools = llm.bind_tools(LANGCHAIN_TOOLS)
        ai_msg: AIMessage = llm_with_tools.invoke(messages)

        # -------------------------------------------------------------
        # Tool Execution Branch
        # -------------------------------------------------------------
        if ai_msg.tool_calls:
            logger.info(f"[*] LLM decided tool call: {ai_msg.tool_calls}")
            messages.append(ai_msg)

            updated_ctx = dict(session_ctx)
            detected_intent = "PRICE"
            detected_crop = None
            detected_dist = None

            for tc in ai_msg.tool_calls:
                t_name = tc.get("name", "")
                t_args = tc.get("args", {})

                if "arbitrage" in t_name:
                    detected_intent = "ARBITRAGE"
                elif "msp" in t_name:
                    detected_intent = "MSP"
                elif "trend" in t_name:
                    detected_intent = "TREND"
                elif "price" in t_name:
                    detected_intent = "PRICE"

                if "crop" in t_args:
                    detected_crop = t_args["crop"]
                    updated_ctx["crop"] = detected_crop
                if "district" in t_args:
                    detected_dist = t_args["district"]
                    updated_ctx["district"] = detected_dist

                selected_tool = TOOL_MAP.get(t_name)
                if selected_tool:
                    try:
                        tool_output = selected_tool.invoke(t_args)
                    except Exception as ex:
                        tool_output = json.dumps({"status": "error", "message": str(ex)})
                    messages.append(ToolMessage(content=str(tool_output), tool_call_id=tc["id"]))

            # Second turn: Synthesize concise spoken Hindi
            final_ai_msg: AIMessage = llm.invoke(messages)
            spoken_response = final_ai_msg.content.strip()

            # Record turn in persistent history
            updated_history = list(chat_history)
            updated_history.append({"role": "user", "content": query})
            updated_history.append({"role": "assistant", "content": spoken_response})
            updated_ctx["chat_history"] = updated_history[-6:]

            return {
                "spoken_hindi_response": spoken_response,
                "intent": detected_intent,
                "crop": detected_crop or updated_ctx.get("crop"),
                "district": detected_dist or updated_ctx.get("district"),
                "status": "success",
                "session_context": updated_ctx
            }

        # Direct response (Clarification or general response)
        spoken_response = ai_msg.content.strip()
        updated_history = list(chat_history)
        updated_history.append({"role": "user", "content": query})
        updated_history.append({"role": "assistant", "content": spoken_response})
        session_ctx["chat_history"] = updated_history[-6:]

        is_clarification = any(w in spoken_response for w in ["फसल", "जिला", "मंडी", "बताइए", "चाहते हैं"])
        detected_intent = "CLARIFICATION" if is_clarification else "CONVERSATION"

        return {
            "spoken_hindi_response": spoken_response,
            "intent": detected_intent,
            "status": "clarification" if is_clarification else "success",
            "session_context": session_ctx
        }

    except Exception as e:
        logger.warning(f"[!] Groq execution encountered error, routing to fallback: {e}")
        return {"status": "fallback"}
