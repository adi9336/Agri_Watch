"""
Agri_watch - Dual-Loop Conversational Steering & Price Arbitrage Router
Coordinates:
1. Entity Disambiguation (Indic synonyms, fuzzy crop and district extraction)
2. Conversational Intent Classification (Greeting, Identity, MSP, Arbitrage, Price)
3. Multi-Turn Session Memory (Tracking crop & district across conversational turns)
4. Live/Historical Mandi Price Ingestion (Agmarknet data engine)
5. Multi-Mandi Arbitrage & Transport Profit Calculation
6. Govt MSP Benchmark Protection
7. Dynamic Spoken Hindi Response Synthesis for Gnani TTS
"""

import os
import sys
import json
import re
from typing import Dict, Any, Optional, List, Tuple

sys.stdout.reconfigure(encoding='utf-8')

# Ensure parent directory is in Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from mandi_tracker import MandiPriceService, normalize_date
from agents.observability import traceable

MSP_FILE = os.path.join(PARENT_DIR, "data", "msp_benchmarks.json")

# Indic Crop Synonym Dictionary (Mapping regional spoken names to official Agmarknet names)
CROP_SYNONYMS = {
    # Wheat
    "गेहूँ": "Wheat", "गेहू": "Wheat", "गेहु": "Wheat", "कनक": "Wheat", "wheat": "Wheat",
    "gehu": "Wheat", "gehun": "Wheat", "kanak": "Wheat",
    # Paddy / Rice
    "धान": "Paddy", "चावल": "Paddy", "बासमती": "Paddy(Basmati)", "dhan": "Paddy",
    "chawal": "Paddy", "paddy": "Paddy", "rice": "Paddy",
    # Mustard
    "सरसों": "Mustard", "राई": "Mustard", "sarson": "Mustard", "mustard": "Mustard", "rai": "Mustard",
    "लाहा": "Mustard", "laha": "Mustard",
    # Gram / Pulses
    "चना": "Gram Raw(Chholia)", "छोलिया": "Gram Raw(Chholia)", "chana": "Gram Raw(Chholia)", "gram": "Gram Raw(Chholia)",
    "मूँग": "Green Gram(Moong)(Whole)", "मूंग": "Green Gram(Moong)(Whole)", "moong": "Green Gram(Moong)(Whole)",
    "मसूर": "Masur Dal", "masur": "Masur Dal",
    "मटर": "Peas(Dry)", "matar": "Peas(Dry)", "peas": "Peas(Dry)",
    "अरहर": "Arhar (Tur/Red Gram)(Whole)", "तुअर": "Arhar (Tur/Red Gram)(Whole)", "arhar": "Arhar (Tur/Red Gram)(Whole)",
    # Coarse cereals & Oilseeds
    "जौ": "Barley(Jau)", "jau": "Barley(Jau)", "barley": "Barley(Jau)",
    "मक्का": "Maize", "makka": "Maize", "bhutta": "Maize", "maize": "Maize",
    "मूंगफली": "Groundnut", "mungfali": "Groundnut", "groundnut": "Groundnut",
    "सोयाबीन": "Soyabean", "soyabean": "Soyabean",
    # Vegetables
    "प्याज": "Onion", "पियाज": "Onion", "कांदा": "Onion", "pyaz": "Onion", "onion": "Onion",
    "टमाटर": "Tomato", "tamatar": "Tomato", "tomato": "Tomato",
    "आलू": "Potato", "alu": "Potato", "potato": "Potato"
}

# Common North Indian Districts mapping
KNOWN_DISTRICTS = {
    "jhansi": ("Jhansi", "Uttar Pradesh"),
    "झाँसी": ("Jhansi", "Uttar Pradesh"),
    "झांसी": ("Jhansi", "Uttar Pradesh"),
    "prayagraj": ("Prayagraj", "Uttar Pradesh"),
    "प्रयागराज": ("Prayagraj", "Uttar Pradesh"),
    "allahabad": ("Prayagraj", "Uttar Pradesh"),
    "etah": ("Etah", "Uttar Pradesh"),
    "एटा": ("Etah", "Uttar Pradesh"),
    "sambhal": ("Sambhal", "Uttar Pradesh"),
    "सम्भल": ("Sambhal", "Uttar Pradesh"),
    "badaun": ("Badaun", "Uttar Pradesh"),
    "बदायूँ": ("Badaun", "Uttar Pradesh"),
    "etawah": ("Etawah", "Uttar Pradesh"),
    "इटावा": ("Etawah", "Uttar Pradesh"),
    "lalitpur": ("Lalitpur", "Uttar Pradesh"),
    "ललितपुर": ("Lalitpur", "Uttar Pradesh"),
    "agra": ("Agra", "Uttar Pradesh"),
    "आगरा": ("Agra", "Uttar Pradesh"),
    "mathura": ("Mathura", "Uttar Pradesh"),
    "मथुरा": ("Mathura", "Uttar Pradesh"),
    "aligarh": ("Aligarh", "Uttar Pradesh"),
    "अलीगढ़": ("Aligarh", "Uttar Pradesh"),
    "rajkot": ("Rajkot", "Gujarat"),
    "राजकोट": ("Rajkot", "Gujarat"),
    "karnal": ("Karnal", "Haryana"),
    "करनाल": ("Karnal", "Haryana"),
    "ludhiana": ("Ludhiana", "Punjab"),
    "लुधियाना": ("Ludhiana", "Punjab")
}


class SteeringRouter:
    def __init__(self, api_key: Optional[str] = None):
        self.service = MandiPriceService(api_key=api_key)
        self.msp_data = self._load_msp_data()
        # Conversational Session State Memory
        self.context = {
            "crop": None,
            "district": None,
            "state": "Uttar Pradesh"
        }

    def _load_msp_data(self) -> Dict[str, Any]:
        if os.path.exists(MSP_FILE):
            with open(MSP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("2026_27", {})
        return {}

    def detect_intent(self, query: str) -> str:
        """Classifies conversational intent from farmer query."""
        q = query.lower()
        
        # 1. Greetings
        if any(w in q for w in ["नमस्ते", "नमस्कार", "राम राम", "प्रणाम", "हेलो", "hello", "hi", "hey"]):
            if not any(crop in q for crop in CROP_SYNONYMS) and not any(dist in q for dist in KNOWN_DISTRICTS):
                return "GREETING"

        # 2. Identity / Help / Capabilities
        if any(w in q for w in ["तुम कौन", "आप कौन", "क्या काम", "क्या करते", "क्या मदद", "help", "who are you"]):
            return "IDENTITY_HELP"

        # 3. Gratitude / Closure
        if any(w in q for w in ["धन्यवाद", "शुक्रिया", "thanks", "thank you", "ठीक है धन्यवाद", "बहुत अच्छा"]):
            return "GRATITUDE"

        # 4. Specific MSP inquiry
        if any(w in q for w in ["समर्थन मूल्य", "एमएसपी", "msp", "सरकारी भाव", "सरकारी रेट", "सरकारी गारंटी"]):
            return "MSP_INQUIRY"

        # 5. Specific Arbitrage inquiry
        if any(w in q for w in ["कहाँ बेचूं", "कहाँ बेचना", "ज्यादा मुनाफा", "मुनाफा कहाँ", "ज्यादा भाव कहाँ", "arbitrage"]):
            return "ARBITRAGE_INQUIRY"

        # Default: Market Price Discovery
        return "PRICE_INQUIRY"

    @traceable(name="NLU:parse_entities", run_type="parser")
    def parse_entities(self, query: str) -> Dict[str, Optional[str]]:
        """Extracts district, state, and crop from spoken natural language."""
        query_clean = query.lower()
        extracted_crop = None
        extracted_district = None
        extracted_state = None

        # 1. Match Crop
        for syn, canonical in CROP_SYNONYMS.items():
            if syn.lower() in query_clean:
                extracted_crop = canonical
                break

        # 2. Match District / State
        for d_key, (d_val, s_val) in KNOWN_DISTRICTS.items():
            if d_key.lower() in query_clean:
                extracted_district = d_val
                extracted_state = s_val
                break

        return {
            "crop": extracted_crop,
            "district": extracted_district,
            "state": extracted_state
        }

    def get_msp(self, crop: str) -> Optional[int]:
        """Looks up MSP for a commodity."""
        for key, val in self.msp_data.items():
            if key.lower() in crop.lower() or crop.lower() in key.lower():
                return val.get("msp")
        return None

    @traceable(name="ArbitrageEngine:calculate", run_type="tool")
    def calculate_arbitrage(self, records: List[Dict]) -> Dict[str, Any]:
        """
        Analyzes records across mandis in a district to identify
        highest bidder and transport economics.
        """
        if not records:
            return {}

        valid_records = []
        for r in records:
            try:
                modal = float(r.get("modal_price", 0))
                if modal > 0:
                    valid_records.append({**r, "modal_float": modal})
            except (ValueError, TypeError):
                continue

        if not valid_records:
            return {}

        valid_records.sort(key=lambda x: x["modal_float"], reverse=True)
        top_mandi = valid_records[0]
        lowest_mandi = valid_records[-1]

        spread = top_mandi["modal_float"] - lowest_mandi["modal_float"]
        # Standard farm transport heuristic: ~Rs 15/Quintal for a 25 km trip
        transport_cost_per_q = 15.0
        standard_load_quintals = 25.0
        net_gain = (spread - transport_cost_per_q) * standard_load_quintals if spread > transport_cost_per_q else 0

        return {
            "top_market": top_mandi.get("market"),
            "top_modal": top_mandi.get("modal_float"),
            "top_variety": top_mandi.get("variety"),
            "top_date": top_mandi.get("arrival_date"),
            "lowest_market": lowest_mandi.get("market"),
            "lowest_modal": lowest_mandi.get("modal_float"),
            "spread": spread,
            "recommend_arbitrage": spread > 30.0,
            "estimated_net_gain_25q": net_gain,
            "total_mandis_reporting": len(set(r.get("market") for r in valid_records))
        }

    @traceable(name="SteeringRouter:process_request", run_type="chain")
    def process_request(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        district: Optional[str] = None,
        crop: Optional[str] = None,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Processes request with intent detection, session memory, and natural synthesis."""
        intent = self.detect_intent(query) if query else "PRICE_INQUIRY"

        # -------------------------------------------------------------
        # Intent 1: Greeting
        # -------------------------------------------------------------
        if intent == "GREETING":
            resp = "राम राम किसान भाई! मैं एग्री-वॉच हूँ। आप किस फसल या किस मंडी का आज का भाव जानना चाहते हैं?"
            return {"intent": intent, "spoken_hindi_response": resp, "crop": None, "district": None, "state": self.context["state"], "reporting_date": None, "is_live": False, "records_count": 0, "records": [], "arbitrage": {}, "msp": None}

        # -------------------------------------------------------------
        # Intent 2: Identity & Help
        # -------------------------------------------------------------
        if intent == "IDENTITY_HELP":
            resp = (
                "मैं एग्री-वॉच हूँ - भारतीय किसानों के लिए स्वतंत्र मंडी और मूल्य सलाहकार। "
                "मैं आपको सरकारी एगमार्कनेट के ताज़ा थोक भाव, मंडियों के बीच मुनाफे का अंतर और "
                "न्यूनतम समर्थन मूल्य (MSP) की सही जानकारी देता हूँ। आप किसी भी फसल का नाम बताएं।"
            )
            return {"intent": intent, "spoken_hindi_response": resp, "crop": None, "district": None, "state": self.context["state"], "reporting_date": None, "is_live": False, "records_count": 0, "records": [], "arbitrage": {}, "msp": None}

        # -------------------------------------------------------------
        # Intent 3: Gratitude / Closure
        # -------------------------------------------------------------
        if intent == "GRATITUDE":
            resp = "बहुत-बहुत धन्यवाद किसान भाई! किसी भी फसल या मंडी का भाव जानने के लिए कभी भी पूछें। आपका दिन शुभ हो!"
            return {"intent": intent, "spoken_hindi_response": resp, "crop": self.context["crop"], "district": self.context["district"], "state": self.context["state"], "reporting_date": None, "is_live": False, "records_count": 0, "records": [], "arbitrage": {}, "msp": None}

        # -------------------------------------------------------------
        # Entity Extraction & Context Memory Updating
        # -------------------------------------------------------------
        if query:
            extracted = self.parse_entities(query)
            if extracted["crop"]:
                self.context["crop"] = extracted["crop"]
            if extracted["district"]:
                self.context["district"] = extracted["district"]
            if extracted["state"]:
                self.context["state"] = extracted["state"]

        # Apply parameters or memory
        crop = crop or self.context["crop"]
        district = district or self.context["district"]
        state = state or self.context["state"] or "Uttar Pradesh"

        # -------------------------------------------------------------
        # Intent 4: Explicit MSP Inquiry
        # -------------------------------------------------------------
        if intent == "MSP_INQUIRY":
            if not crop:
                resp = "किसान भाई, आप किस फसल का सरकारी समर्थन मूल्य (MSP) जानना चाहते हैं? जैसे गेहूँ, चना, धान या सरसों?"
                return {"intent": intent, "spoken_hindi_response": resp, "crop": None, "district": district, "state": state, "reporting_date": None, "is_live": False, "records_count": 0, "records": [], "arbitrage": {}, "msp": None}
            msp_val = self.get_msp(crop)
            if msp_val:
                resp = f"किसान भाई, 2026-27 के लिए {crop} का सरकारी समर्थन मूल्य (MSP) ₹{msp_val} प्रति क्विंटल निर्धारित है। यदि कोई व्यापारी इससे कम बोली लगाता है, तो आप सरकारी खरीद केंद्र पर संपर्क कर सकते हैं।"
            else:
                resp = f"{crop} के लिए कोई प्रत्यक्ष MSP दर अधिसूचित नहीं है, इसका व्यापार मंडी में खुली नीलामी के आधार पर होता है।"
            return {"intent": intent, "spoken_hindi_response": resp, "crop": crop, "district": district, "state": state, "reporting_date": None, "is_live": False, "records_count": 0, "records": [], "arbitrage": {}, "msp": msp_val}

        # -------------------------------------------------------------
        # Disambiguation / Clarification when context is incomplete
        # -------------------------------------------------------------
        if not crop and district:
            resp = f"किसान भाई, {district} मंडी में आप किस फसल का भाव जानना चाहते हैं? जैसे गेहूँ, सरसों, चना या मटर?"
            return {"intent": "CLARIFICATION_CROP", "spoken_hindi_response": resp, "crop": None, "district": district, "state": state, "reporting_date": None, "is_live": False, "records_count": 0, "records": [], "arbitrage": {}, "msp": None}

        if not crop and not district:
            resp = "किसान भाई, आप किस फसल या किस जिले की मंडी का भाव जानना चाहते हैं? मुझे बताएं।"
            return {"intent": "CLARIFICATION_BOTH", "spoken_hindi_response": resp, "crop": None, "district": None, "state": state, "reporting_date": None, "is_live": False, "records_count": 0, "records": [], "arbitrage": {}, "msp": None}

        # If crop is present but district is still unknown, default to regional baseline
        if crop and not district:
            district = "Jhansi"
            self.context["district"] = district

        # -------------------------------------------------------------
        # Step 2: Fetch Live or Baseline Mandi Pricing Data
        # -------------------------------------------------------------
        is_live = False
        reporting_date = None
        records = []

        if not date or date.lower() == "today":
            if self.service.api_key:
                try:
                    direct, state_wide, rep_date = self.service.fetch_live_prices(state, district, crop)
                    if direct:
                        records = direct
                        is_live = True
                        reporting_date = rep_date
                    elif state_wide:
                        records = state_wide
                        reporting_date = rep_date
                except Exception as e:
                    print(f"[*] Live API note: {e}")

        # Fallback to historical database
        if not records:
            norm_date = normalize_date(date) if date and date.lower() != "today" else None
            hist_records, _ = self.service.fetch_historical(state, district, crop, target_date=norm_date)
            records = hist_records
            if records:
                reporting_date = records[0].get("arrival_date")

        # Step 3: Run Arbitrage and MSP Analysis
        arbitrage = self.calculate_arbitrage(records)
        msp = self.get_msp(crop)

        # -------------------------------------------------------------
        # Intent 5: Arbitrage Inquiry (Where to sell for top profit)
        # -------------------------------------------------------------
        if intent == "ARBITRAGE_INQUIRY":
            if arbitrage and arbitrage.get("recommend_arbitrage"):
                top_m = arbitrage.get("top_market")
                top_p = arbitrage.get("top_modal")
                low_m = arbitrage.get("lowest_market")
                spread = arbitrage.get("spread")
                net_gain = arbitrage.get("estimated_net_gain_25q")
                resp = (
                    f"किसान भाई, {crop} के लिए सबसे बढ़िया भाव {top_m} में ₹{top_p:.0f} प्रति क्विंटल है। "
                    f"पास की {low_m} की तुलना में यहाँ ₹{spread:.0f} प्रति क्विंटल अधिक मिल रहा है। "
                    f"ट्रॉली (25 क्विंटल) ले जाने पर डीजल खर्च काटकर लगभग ₹{net_gain:.0f} का शुद्ध मुनाफा होगा।"
                )
            else:
                resp = f"किसान भाई, {district} क्षेत्र की सभी मंडियों में {crop} का भाव लगभग बराबर चल रहा है। आप निकटतम मंडी में ही बिक्री कर सकते हैं।"
            return {"intent": intent, "spoken_hindi_response": resp, "crop": crop, "district": district, "state": state, "reporting_date": reporting_date, "is_live": is_live, "records_count": len(records), "records": records[:5], "arbitrage": arbitrage, "msp": msp}

        # -------------------------------------------------------------
        # Intent 6: General Mandi Price Discovery
        # -------------------------------------------------------------
        spoken_response = self._synthesize_spoken_hindi(
            crop=crop,
            district=district,
            state=state,
            records=records,
            arbitrage=arbitrage,
            msp=msp,
            is_live=is_live,
            reporting_date=reporting_date
        )

        return {
            "intent": intent,
            "crop": crop,
            "district": district,
            "state": state,
            "reporting_date": reporting_date,
            "is_live": is_live,
            "records_count": len(records),
            "records": records[:5],
            "arbitrage": arbitrage,
            "msp": msp,
            "spoken_hindi_response": spoken_response
        }

    def _synthesize_spoken_hindi(
        self,
        crop: str,
        district: str,
        state: str,
        records: List[Dict],
        arbitrage: Dict[str, Any],
        msp: Optional[int],
        is_live: bool,
        reporting_date: Optional[str]
    ) -> str:
        """Constructs natural, conversational spoken Hindi for farmers and traders."""
        if not records:
            return f"माफ कीजिए किसान भाई, {district} मंडी में {crop} की कोई हालिया आवक दर्ज नहीं हुई है।"

        top_market = arbitrage.get("top_market", records[0].get("market", f"{district} मंडी"))
        top_modal = arbitrage.get("top_modal", records[0].get("modal_price"))
        top_variety = arbitrage.get("top_variety", records[0].get("variety", "सामान्य"))
        date_str = reporting_date or records[0].get("arrival_date", "हाल के दिन")

        speech_parts = []

        # Intro
        live_tag = "आज" if is_live else f"{date_str} को"
        speech_parts.append(f"किसान भाई, {district} क्षेत्र की {top_market} में {crop} ({top_variety}) का भाव {live_tag} ₹{top_modal:.0f} प्रति क्विंटल रहा है।")

        # MSP comparison
        if msp and top_modal:
            diff = top_modal - msp
            if diff > 0:
                speech_parts.append(f"यह भाव सरकारी समर्थन मूल्य (MSP) ₹{msp} से ₹{diff:.0f} अधिक है।")
            elif diff < 0:
                speech_parts.append(f"ध्यान दें, यह भाव सरकारी समर्थन मूल्य ₹{msp} से ₹{abs(diff):.0f} कम है। आप सरकारी खरीद केंद्र पर भी संपर्क कर सकते हैं।")
            else:
                speech_parts.append(f"यह भाव सरकारी समर्थन मूल्य ₹{msp} के बिल्कुल बराबर है।")

        # Arbitrage / Multi-Mandi advice
        if arbitrage.get("recommend_arbitrage"):
            spread = arbitrage.get("spread", 0)
            net_gain = arbitrage.get("estimated_net_gain_25q", 0)
            lowest_mkt = arbitrage.get("lowest_market")
            speech_parts.append(f"पास की {lowest_mkt} की तुलना में यहाँ ₹{spread:.0f} प्रति क्विंटल अधिक मिल रहा है। यदि आप 25 क्विंटल माल लाते हैं, तो लगभग ₹{net_gain:.0f} का अतिरिक्त लाभ होगा।")
        elif arbitrage.get("total_mandis_reporting", 1) > 1:
            speech_parts.append(f"जिले की अन्य मंडियों में भी भाव इसके लगभग समान चल रहा है।")

        return " ".join(speech_parts)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agri_watch Conversational Steering & Price Arbitrage Router")
    parser.add_argument("--query", type=str, help="Natural language spoken query (e.g. 'झाँसी में गेहूँ का क्या भाव है?')")
    parser.add_argument("--state", type=str, default=None, help="State name")
    parser.add_argument("--district", type=str, default=None, help="District name")
    parser.add_argument("--crop", type=str, default=None, help="Crop name (Wheat, Paddy, Mustard)")
    parser.add_argument("--date", type=str, default=None, help="Date (e.g. 24/09/2026, 2026-07-23, or 'today')")

    args = parser.parse_args()

    router = SteeringRouter()

    print("[*] Running Dual-Loop Steering Router & Multi-Agent Arbitrage...")
    res = router.process_request(
        query=args.query,
        state=args.state,
        district=args.district,
        crop=args.crop,
        date=args.date
    )

    print("\n" + "=" * 65)
    print(f"QUERY ANALYSIS:")
    print(f"  Intent: {res.get('intent')}")
    print(f"  Target: {res['crop']} in {res['district']} ({res['state']})")
    print(f"  Reporting Date: {res['reporting_date']} (Live: {res['is_live']})")
    print(f"  Records Analyzed: {res['records_count']}")
    if res['msp']:
        print(f"  Official Govt MSP: Rs. {res['msp']}/Quintal")
    if res['arbitrage']:
        arb = res['arbitrage']
        print(f"  Top Mandi: {arb.get('top_market')} @ Rs. {arb.get('top_modal')}/Q")
        if arb.get('spread', 0) > 0:
            print(f"  Price Spread: Rs. {arb.get('spread')}/Q | Net gain for 25Q: Rs. {arb.get('estimated_net_gain_25q'):.0f}")
    print("=" * 65)
    print("\nSPONSORED / SYNTHESIZED SPOKEN INDIC RESPONSE (FOR GNANI TTS):")
    print(f"  \"{res['spoken_hindi_response']}\"\n")
