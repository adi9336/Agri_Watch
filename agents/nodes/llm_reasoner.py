"""
Agri_watch - Groq LLM Reasoning & Tool Calling Engine
Uses Groq for ultra-low-latency (<250ms) Indic reasoning, autonomous tool selection,
and natural spoken Hindi response generation with resilient model auto-discovery.
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

# 2. Sovereign Indic System Prompt (Strictly optimized for Voice Output)
SYSTEM_PROMPT = """आप एग्री-वॉच (Agri-Watch) हैं - भारतीय किसानों के लिए एक सरल, सटीक और संक्षेप में बोलने वाले वॉयस असिस्टेंट (Voice Agent)।
आपका उत्तर सीधे स्पीकर पर आवाज़ (TTS) द्वारा किसान को सुनाया जाता है। इसलिए आपके जवाब बहुत छोटे, सीधे और केवल पूछे गए सवाल तक सीमित होने चाहिए।

सख्त नियम (STRICT VOICE AGENT RULES):
1. केवल वही बताएं जो किसान ने पूछा है (कदापि बिना पूछे अतिरिक्त विवरण न दें):
   - यदि किसान केवल किसी फसल का भाव पूछे (जैसे 'झाँसी में गेहूँ का क्या रेट है?'): तो केवल उस जिले/मंडी का औसत भाव 1 या 2 छोटे वाक्यों में बताएं। उदाहरण: 'किसान भाई, झाँसी मंडी में गेहूँ का भाव ₹2,600 प्रति क्विंटल है।'
   - बिना पूछे अपने मन से कभी भी MSP की बात न जोड़ें, न ही दूसरी मंडियों की तुलना करें।
   - जब किसान स्पष्ट पूछे कि 'कहाँ बेचूँ', 'मुनाफा कहाँ है', या मंडियों की तुलना करे: केवल तभी `compare_mandi_arbitrage_tool` चलाएं और सबसे ज्यादा दाम देने वाली मंडी बताएं।
   - जब किसान 'सरकारी भाव' या 'MSP' पूछे: केवल तभी `check_msp_floor_tool` चलाएं।
2. उत्तर की लंबाई: अधिकतम 1 से 2 छोटे वाक्य। कोई लंबा पैराग्राफ, तारीखों की भरमार या लिस्ट नहीं देनी है।
3. वाक्-अनुकूल (Voice Friendly) फॉर्मेटिंग:
   - कोई मार्कडाउन चिन्ह (जैसे **, *, #, बुलेट पॉइंट्स) न लगाएं।
   - कोई इमोजी (जैसे 🙏) न लगाएं, क्योंकि वॉयस इंजन उन्हें गलत बोलता है।
   - भाव को हमेशा '₹X प्रति क्विंटल' साफ़ और साधारण हिंदी में लिखें।
4. यदि किसान ने फसल का नाम न बताया हो (जैसे केवल 'झाँसी का भाव बताओ'), तो मन से फसल का अनुमान न लगाएं। तुरंत पूछें: 'किसान भाई, आप झाँसी मंडी में किस फसल का भाव जानना चाहते हैं?'
5. यदि किसान केवल 'हाँ', 'ठीक है', 'अच्छा', 'बताओ' या 'ok' कहे, तो पुराना भाव कभी भी दोबारा न दोहराएं। उनसे पूछें: 'जी भाई, क्या आप किसी अन्य फसल या दूसरी मंडी का भाव जानना चाहते हैं?'
"""

_active_groq_model: Optional[str] = None


def resolve_groq_model(groq_key: str) -> str:
    """Dynamically resolves the best available chat completion model on Groq."""
    global _active_groq_model
    if _active_groq_model:
        return _active_groq_model

    # Check manual override
    env_model = os.getenv("GROQ_MODEL")
    if env_model:
        _active_groq_model = env_model
        return _active_groq_model

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        available_ids = [m.id for m in client.models.list().data]

        preferences = [
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-120b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "openai/gpt-oss-20b"
        ]
        for pref in preferences:
            if pref in available_ids:
                _active_groq_model = pref
                logger.info(f"[*] Auto-selected Groq model: {_active_groq_model}")
                return _active_groq_model

        # Fallback to any non-whisper, non-guard model
        chat_models = [m for m in available_ids if not m.startswith("whisper") and "guard" not in m]
        if chat_models:
            _active_groq_model = chat_models[0]
            return _active_groq_model
    except Exception as e:
        logger.warning(f"[!] Groq model resolution warning: {e}")

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
            max_tokens=600,
            api_key=groq_key
        )
    except Exception as e:
        logger.warning(f"[!] Could not initialize ChatGroq: {e}")
        return None


@traceable(name="LangGraphNode:GroqReasoner", run_type="llm")
def groq_reasoner_node(state: AgentState) -> Dict[str, Any]:
    """
    LLM Reasoning Node: Uses Groq to reason over farmer utterance,
    decide whether to call tools, execute tools, and formulate natural spoken Hindi.
    """
    llm = get_groq_llm()
    if not llm:
        return {"status": "llm_fallback"}

    query = state.get("user_query", "").strip()
    session_ctx = state.get("session_context") or {}

    # Build context message intelligently
    context_hint = ""
    is_affirmation = any(w in query.lower() for w in ["हाँ", "ठीक है", "अच्छा", "ok", "okay", "theek hai"]) and len(query.split()) <= 4
    if is_affirmation and session_ctx.get("crop"):
        context_hint = f"\n[पिछला संदर्भ: किसान को पहले {session_ctx.get('crop')} का भाव दिया जा चुका है। अब वे केवल 'हाँ/ठीक है' बोल रहे हैं। भाव दोबारा बिल्कुल न दोहराएं, केवल पूछें कि क्या वे किसी दूसरी फसल या मंडी का भाव जानना चाहते हैं।]"
    elif session_ctx.get("crop") or session_ctx.get("district"):
        context_hint = f"\n[पिछला संदर्भ: फसल={session_ctx.get('crop')}, जिला={session_ctx.get('district')}]"

    messages = [
        SystemMessage(content=SYSTEM_PROMPT + context_hint),
        HumanMessage(content=query)
    ]

    try:
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

            # Update persistent context and deduce intent
            updated_ctx = dict(session_ctx)
            extracted_crop = None
            extracted_dist = None
            detected_intent = "PRICE_INQUIRY"

            for tc in ai_msg.tool_calls:
                t_name = tc.get("name", "")
                if "arbitrage" in t_name:
                    detected_intent = "ARBITRAGE"
                elif "msp" in t_name:
                    detected_intent = "MSP"
                elif "price" in t_name:
                    detected_intent = "PRICE_INQUIRY"

                args = tc.get("args", {})
                if "crop" in args:
                    extracted_crop = args["crop"]
                    updated_ctx["crop"] = extracted_crop
                if "district" in args:
                    extracted_dist = args["district"]
                    updated_ctx["district"] = extracted_dist

            return {
                "spoken_hindi_response": spoken_response,
                "intent": detected_intent,
                "crop": extracted_crop or updated_ctx.get("crop"),
                "district": extracted_dist or updated_ctx.get("district"),
                "status": "success",
                "session_context": updated_ctx
            }

        # Direct conversational response (e.g. greeting, affirmation, or clarification prompt)
        spoken_response = ai_msg.content.strip()
        resp_lower = spoken_response.lower()

        if is_affirmation:
            conv_intent = "CONTINUATION"
            conv_status = "success"
        elif any(w in query.lower() for w in ["राम", "नमस्ते", "नमस्कार", "hello", "hi"]):
            conv_intent = "GREETING"
            conv_status = "success"
        elif "फसल" in spoken_response or "जिला" in spoken_response or "?" in spoken_response:
            conv_intent = "CLARIFICATION"
            conv_status = "clarification"
        else:
            conv_intent = "CONVERSATION"
            conv_status = "success"

        return {
            "spoken_hindi_response": spoken_response,
            "intent": conv_intent,
            "crop": session_ctx.get("crop"),
            "district": session_ctx.get("district"),
            "status": conv_status,
            "session_context": session_ctx
        }

    except Exception as e:
        logger.warning(f"[!] Groq execution encountered error, falling back to sovereign pipeline: {e}")
        return {"status": "llm_fallback"}
