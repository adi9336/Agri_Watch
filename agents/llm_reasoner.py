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

from agents.tools import (
    get_crop_price,
    compare_mandi_arbitrage,
    check_msp_floor,
    get_crop_price_trend,
    consult_economic_specialist
)
from agents.state import AgentState
from agents.observability import traceable

logger = logging.getLogger("agriwatch.reasoner")

# 1. Define LangChain Structured Tools for LLM
@tool
def get_crop_price_tool(
    crop: str,
    district_or_mandi: str,
    state: Optional[str] = None,
    date: Optional[str] = None
) -> str:
    """
    Fetch wholesale APMC mandi price and modal rate for any crop in a district OR specific mandi.
    Pass district_or_mandi: Name of the district OR mandi (e.g. 'Rath', 'Mauranipur', 'Jhansi', 'Agra', 'Atarra', 'Dabra').
    The system automatically resolves any mandi name to its official district! Never ask the farmer for district if they named a mandi.
    Strictly pass a date. If the farmer did not mention a date, pass date='today'.
    Args:
        crop: Name of the crop (e.g. 'Wheat', 'Gram', 'Mustard')
        district_or_mandi: District or Mandi name (e.g. 'Rath', 'Mauranipur', 'Jhansi', 'Agra')
        state: State name (optional, e.g. 'Madhya Pradesh', 'Uttar Pradesh')
        date: Target date ('today', 'yesterday', 'पिछले हफ्ते', or 'DD/MM/YYYY'). Defaults to 'today'.
    """
    if not date:
        date = "today"
    return get_crop_price(crop=crop, district=district_or_mandi, state=state, date=date)

@tool
def compare_mandi_arbitrage_tool(crop: str, district_or_mandi: str, state: Optional[str] = None) -> str:
    """
    Compare commodity prices across multiple APMC mandis within a district or neighboring region
    to find the highest-paying market and calculate transport net profit.
    Pass district_or_mandi: District or Mandi name (e.g. 'Rath', 'Jhansi', 'Satna').
    """
    return compare_mandi_arbitrage(crop=crop, district=district_or_mandi, state=state)

@tool
def check_msp_floor_tool(crop: str) -> str:
    """
    Look up the official Government Minimum Support Price (MSP) floor rate for a crop.
    Call this ONLY when a farmer asks about MSP, government rate, or minimum guaranteed price.
    """
    return check_msp_floor(crop=crop)

@tool
def get_crop_price_trend_tool(
    crop: str,
    district_or_mandi: str,
    timeframe: Optional[str] = None,
    state: Optional[str] = None
) -> str:
    """
    Analyzes historical price movement, trend direction (Rising / Falling / Stable),
    and multi-day/monthly price ranges (Min to Max) for a crop in a district.
    Call this when a farmer asks:
    - About past prices across multiple days, weeks, or a month (e.g. 'पिछले एक महीने का भाव', 'दिन के हिसाब से भाव', 'पिछले हफ्ते का हाल').
    - Whether prices are rising, falling, or stable.
    """
    return get_crop_price_trend(crop=crop, district=district_or_mandi, timeframe=timeframe, state=state)

@tool
def consult_economic_specialist_tool(
    crop: str,
    district: str,
    query_type: Optional[str] = "holding_strategy",
    holding_days: Optional[int] = 30,
    vehicle_type: Optional[str] = "tractor",
    quantity_quintals: Optional[float] = 50.0,
    state: Optional[str] = None
) -> str:
    """
    Summons the Specialized Economic & Holding Strategy Sub-Agent for deep holding storage ROI and vehicle freight calculations.
    Call this ONLY when a farmer explicitly asks:
    - Whether they should hold/store crop in a warehouse/godown vs sell now (e.g. 'माल रोक कर बेचूँ या अभी?', 'वेयरहाउस में रखने का फायदा होगा या नुकसान?', 'स्टोर करने का खर्चा बताओ').
    - For vehicle-specific freight or transport profit calculations (e.g. 'ट्रैक्टर से ले जाऊँ तो कितना बचेगा?', 'पिकअप या गाड़ी का भाड़ा जोड़कर बताओ').
    - For deep financial calculations (e.g. 'पूरा हिसाब बताओ', 'विस्तार से नफा-नुकसान समझाओ').
    Do NOT call this for regular fast price discovery.
    """
    return consult_economic_specialist(
        crop=crop,
        district=district,
        query_type=query_type or "holding_strategy",
        holding_days=holding_days or 30,
        vehicle_type=vehicle_type or "tractor",
        quantity_quintals=quantity_quintals or 50.0,
        state=state
    )

LANGCHAIN_TOOLS = [
    get_crop_price_tool,
    compare_mandi_arbitrage_tool,
    check_msp_floor_tool,
    get_crop_price_trend_tool,
    consult_economic_specialist_tool
]
TOOL_MAP = {t.name: t for t in LANGCHAIN_TOOLS}

# 2. Strict Voice Agent System Prompt
SYSTEM_PROMPT = """You are Agri-Watch, a voice assistant for Indian farmers. Your reply is spoken aloud by TTS.
ALWAYS reply in simple Hindi (Devanagari), 1-2 short sentences, starting with "किसान भाई,". No markdown, bullets or emojis. Say prices as "₹X प्रति क्विंटल".

TOOLS (answer only what was asked; never add MSP or other mandis unprompted):
- Price of a crop at a mandi/district -> get_crop_price_tool. Pass the spoken place name as-is in district_or_mandi (e.g. Rath, Mauranipur, Jhansi); the system resolves districts, so never ask for the district if a mandi/town was named. Always pass date: 'today' if none said, 'yesterday' for कल, or the given date.
- Where to sell / nearby or other mandis / compare -> compare_mandi_arbitrage_tool. Name the top 2-3 mandis with prices (you may use companion_summary_hi). Never say "no mandi found" if the tool returned prices.
- MSP / सरकारी भाव -> check_msp_floor_tool.
- Rising/falling, trend, past week/month prices -> get_crop_price_trend_tool. Give the range and overall change.
- Hold vs sell now, warehouse cost, vehicle/freight full calculation -> consult_economic_specialist_tool; summarise its companion_summary_hi.

MISSING INFO: Place but no crop (and none in session context) -> ask which crop, no tool. Crop but no place (and none in context) -> ask for district or mandi, no tool.
FOLLOW-UPS: Fill anything missing from [सत्र संदर्भ] (active crop/district). Never re-ask a crop that is already in context. E.g. after "Lucknow chana", "और गेहूं?" = wheat in Lucknow; "और कटनी में?" = same crop in Katni; "आसपास की मंडी?" = compare tool with the context crop.

NO HALLUCINATION: Use only modal_price and dates returned by tools. If status is not_found, say the price is not in the official record for that place/date. Never invent prices or dates.
DATES: is_today=true -> "आज [मंडी] में [फसल] का भाव ₹X प्रति क्विंटल है". Asked today but is_exact_date=false -> say today's rate is not yet recorded and give the reporting_date price. Asked another date and is_exact_date=false -> say that date is unavailable and give the nearest reporting_date price. For compare results with is_today=false, mention the reporting_date of the best mandi.
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
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
            "qwen/qwen3.8-27b",
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
            max_tokens=400,
            reasoning_effort="low",
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
        crop_val = session_ctx['crop']
        crop_hi = "चना" if crop_val.lower() in ("gram", "bengal gram", "chana") else crop_val
        context_parts.append(f"सक्रिय_फसल={crop_val} ({crop_hi})")
    if session_ctx.get("district"):
        context_parts.append(f"सक्रिय_जिला={session_ctx['district']}")
    context_hint = f"\n[सत्र संदर्भ: {', '.join(context_parts)}]" if context_parts else ""

    messages = [SystemMessage(content=SYSTEM_PROMPT + context_hint)]
    # Feed recent conversational context (up to last 6 turns), filtering empty content
    for msg in chat_history[-4:]:
        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if not content:
            continue
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
                dist_val = t_args.get("district") or t_args.get("district_or_mandi")
                if dist_val:
                    detected_dist = dist_val
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
            spoken_response = (final_ai_msg.content or "").strip()
            if not spoken_response:
                crop_lbl = detected_crop or updated_ctx.get("crop", "")
                dist_lbl = detected_dist or updated_ctx.get("district", "")
                spoken_response = f"किसान भाई, {dist_lbl} मंडी में {crop_lbl} का भाव दर्ज कर लिया गया है।"

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
        spoken_response = (ai_msg.content or "").strip()
        if not spoken_response:
            logger.warning("[!] LLM returned empty response without tool calls, applying safety response.")
            spoken_response = "किसान भाई, कृपया अपना प्रश्न दोबारा बोलें, मैं सही भाव पता करके बताता हूँ।"

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
