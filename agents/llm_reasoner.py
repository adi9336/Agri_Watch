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
SYSTEM_PROMPT = """आप एग्री-वॉच (Agri-Watch) हैं - भारतीय किसानों के लिए एक सरल, सटीक और संक्षेप में बोलने वाले वॉयस असिस्टेंट।
आपका उत्तर सीधे स्पीकर पर आवाज़ (TTS) द्वारा किसान को सुनाया जाता है।

सख्त नियम (STRICT VOICE RULES):
0. अनिवार्य सत्र संदर्भ नियम (MANDATORY CONTEXT CARRYOVER RULE):
   - यदि ऊपर दिए गए [सत्र संदर्भ] में पहले से सक्रिय_फसल (जैसे Gram (चना)) मौजूद है: तो किसी भी फॉलो-अप सवाल पर किसान से दोबारा फसल कभी न पूछें!
   - जब किसान फॉलो-अप में पूछे कि 'आसपास की मंडियों के दाम बताओ', 'क्या तुम मुझे सारी मंडियों के दाम बताओगे जितनी भी राठ या रॉड के आसपास हैं', 'कहाँ बेचूँ', या 'कोई दूसरी मंडी':
     अनिवार्य रूप से [सत्र संदर्भ] की सक्रिय_फसल लेकर तुरंत `compare_mandi_arbitrage_tool` चलाएं!

1. केवल वही बताएं जो किसान ने पूछा है और सत्यनिष्ठा का पालन करें:
   - सत्यनिष्ठा व गैर-काल्पनिक नियम (STRICT NO-HALLUCINATION RULE):
     यदि किसी टूल (`get_crop_price_tool`) से 'not_found' या भाव न मिलने की स्थिति आए, तो कभी भी अपने मन से कोई काल्पनिक भाव (Hallucinated Price) या तारीख न बनाएं!
     सीधे और स्पष्ट शब्दों में कहें: "किसान भाई, [मंडी/जिले] में [तारीख] को [फसल] का भाव आधिकारिक रिकॉर्ड में उपलब्ध नहीं है।" केवल टूल में दिए गए वास्तविक 'modal_price' और 'reporting_date' ही बताएं।
   - यदि किसान किसी फसल और स्थान (मंडी या जिला, जैसे 'राठ मंडी में गेहूं का क्या रेट है?', 'झाँसी में गेहूँ का भाव क्या है?', 'aaj agra me chane ka kya bhav he') का भाव पूछे:
     तुरंत `get_crop_price_tool` चलाएं। `district_or_mandi` में किसान द्वारा बोला गया नाम (जैसे 'Rath', 'Mauranipur', या 'Jhansi') सीधे पास करें। कभी भी किसान से उसका जिला न पूछें, सिस्टम मंडी और जिले को खुद पहचान लेता है!
     उस मंडी का भाव 1 वाक्य में बताएं (जैसे: 'किसान भाई, राठ मंडी (हमीरपुर) में गेहूँ का भाव ₹2,400 प्रति क्विंटल रहा है।')।
   - बिना पूछे अपने मन से कभी भी MSP की बात न जोड़ें, न ही दूसरी मंडियों की तुलना करें।
   - जब किसान पूछे कि 'कहाँ बेचूँ', 'मुनाफा कहाँ है', या आसपास/अन्य मंडियों के दाम या सूची पूछे (जैसे 'राठ के आसपास की मंडियों के दाम बताओ', 'क्या तुम मुझे सारी मंडियों के दाम बताओगे जितनी भी राठ के आसपास हैं', 'रॉड के आसपास के दाम बताओ', 'सतना के आसपास की मंडी', 'कोई दूसरी मंडी'):
     तुरंत `compare_mandi_arbitrage_tool` चलाएं।
     टूल से मिले शीर्ष 2 से 3 प्रमुख मंडियों के नाम और उनके भाव स्पष्ट रूप से किसान को 1-2 वाक्यों में बताएं (टूल में दिए गए `companion_summary_hi` का सीधे उपयोग करें या स्वाभाविक रूप से बोलें, जैसे: 'किसान भाई, राठ के आसपास: महोबा मंडी में चना ₹6,400, राठ में ₹6,100, और अतर्रा में ₹6,200 प्रति क्विंटल रहा है। महोबा मंडी में सबसे अच्छा दाम मिल रहा है।')।
     कदापि 'कोई मंडी नहीं मिली' या 'भाव समान है' जैसा नकारात्मक बहाना न बनाएं यदि टूल में मंडियों के भाव मौजूद हैं!
   - जब किसान 'सरकारी भाव' या 'MSP' पूछे: केवल तभी `check_msp_floor_tool` चलाएं और समर्थन मूल्य बताएं।
   - जब किसान पूछे कि 'भाव बढ़ रहे हैं या घट रहे हैं', 'मंडी का रुझान क्या है', या 'पिछले महीने/हफ्ते/दिनों का क्या भाव रहा' (भले ही किसान 'दिन के हिसाब से' पूछे): तुरंत get_crop_price_trend_tool चलाएं। टूल से मिले भाव का दायरा और कुल बढ़त/गिरावट 1-2 वाक्यों में समझाएं।
   - जब किसान विशेष रूप से पूछे कि 'माल रोक कर बेचूँ या अभी बेचूँ', 'वेयरहाउस में रखने का क्या खर्चा और फायदा होगा', 'ट्रैक्टर/गाड़ी से ले जाने पर पूरा हिसाब बताओ', या 'विस्तार से नफा-नुकसान समझाओ': तुरंत विशेषज्ञ सब-एजेंट टूल consult_economic_specialist_tool चलाएं और टूल से मिले companion_summary_hi को संक्षेप में 1-2 वाक्यों में किसान को बताएं।
2. अस्पष्ट या अधूरी जानकारी और फॉलो-अप पर नियम (Clarification & Follow-up Rules):
   - यदि किसान केवल मंडी या जिले का नाम ले लेकिन फसल न बताए (जैसे 'झाँसी का भाव बताओ' या 'राठ मंडी का भाव') और सत्र संदर्भ में भी फसल न हो: कोई टूल न चलाएं। सीधे पूछें: 'किसान भाई, [मंडी] में आप किस फसल का भाव जानना चाहते हैं?'
   - यदि किसान केवल फसल का नाम ले और कोई भी मंडी या जिला न बोले (जैसे केवल कहे 'चने का क्या भाव है') और सत्र संदर्भ में भी स्थान न हो: तब पूछें: 'किसान भाई, [फसल] का भाव जानने के लिए कृपया अपना जिला या मंडी बताइए।'
   - ध्यान रहे: यदि किसान ने किसी भी मंडी, उप-मंडी या कस्बे का नाम ले लिया है (जैसे 'राठ', 'राठ मंडी', 'मऊरानीपुर', 'अतर्रा', 'बरुआसागर', 'डबरा'): कभी भी जिला न पूछें! वह नाम सीधे टूल के `district_or_mandi` में पास करें।
   - फॉलो-अप (Follow-up) सवाल नियम:
     * यदि पिछली बातचीत के संदर्भ में पहले से फसल या जिला मौजूद हो, तो किसान के नए सवाल में छूटी हुई जानकारी सत्र संदर्भ ([सत्र संदर्भ]) से स्वतः ले लें:
       - उदाहरण: पहले 'लखनऊ में चना' पूछा, अब किसान पूछे 'और गेहूं का भाव क्या था?': जिला लखनऊ ही रखें, फसल गेहूं करके `get_crop_price_tool` चलाएं।
       - उदाहरण: पहले 'चना' पूछा, अब किसान पूछे 'और कटनी में?': फसल चना ही रखें, जिला कटनी करके `get_crop_price_tool` चलाएं।
       - उदाहरण: किसान पूछे 'पिछले हफ्ते का?': फसल और जिला वही रखें, नई तारीख पास करें।
       - उदाहरण: किसान पूछे 'आसपास की मंडी का बताओ?' या 'सारी मंडियों के दाम बताओ': फसल और संदर्भ वही रखें, `compare_mandi_arbitrage_tool` चलाएं।
3. उत्तर की लंबाई: केवल 1 से 2 छोटे वाक्य। कोई लंबा भाषण, तारीखों की भरमार या गैर-ज़रूरी लिस्ट नहीं देनी है।
4. वाक्-अनुकूल (Voice Friendly) फॉर्मेटिंग:
   - कोई मार्कडाउन चिन्ह (जैसे **, *, #, बुलेट पॉइंट्स) बिल्कुल न लगाएं।
   - कोई इमोजी (जैसे 🙏) न लगाएं, क्योंकि वॉयस इंजन उन्हें गलत बोलता है।
   - भाव को हमेशा '₹X प्रति क्विंटल' साफ़ हिंदी में लिखें।
5. तारीख (Date) का सख्त नियम:
   - `get_crop_price_tool` चलाते समय सदैव `date` पास करें: यदि किसान ने कोई तारीख न बोली हो, तो अनिवार्य रूप से `date='today'` पास करें। यदि 'कल' का पूछे तो `date='yesterday'`, यदि ख़ास तारीख पूछे तो वह तारीख पास करें।
   - यदि आज का लाइव भाव मिला हो (`is_today=true`): 'किसान भाई, आज [मंडी] में [फसल] का भाव ₹X प्रति क्विंटल है।' बोलें।
   - यदि आज का भाव अभी दर्ज न हुआ हो (`is_exact_date=false` और किसान ने आज का पूछा था): साफ़ बताएं: 'किसान भाई, आज का भाव अभी दर्ज नहीं हुआ है, [reporting_date] को [मंडी] में [फसल] का भाव ₹X प्रति क्विंटल रहा था।'
   - यदि किसान ने विशेष तारीख या 'पिछले हफ्ते' पूछा हो और नजदीकी तारीख मिली हो (`is_exact_date=false`): साफ़ बताएं: 'किसान भाई, [requested_date] का भाव उपलब्ध नहीं है, सबसे नजदीकी तारीख [reporting_date] को [मंडी] में [फसल] का भाव ₹X प्रति क्विंटल रहा था।'
   - यदि किसान ने विशेष तारीख पूछी हो और ठीक उसी तारीख का भाव मिला हो (`is_exact_date=true`): '[reporting_date] को [मंडी] में [फसल] का भाव ₹X प्रति क्विंटल रहा था।' बोलें।
   - यदि `compare_mandi_arbitrage_tool` चलाएं और भाव आज का न हो (`is_today=false`): सबसे ज्यादा दाम वाली मंडी के साथ उसकी तारीख [reporting_date] भी स्पष्ट बोलें (जैसे: '[reporting_date] को [मंडी] में भाव ₹X रहा था') ताकि तारीख का भ्रम न रहे।
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
            max_tokens=800,
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
    for msg in chat_history[-6:]:
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
