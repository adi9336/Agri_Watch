"""
Agri_watch - Dual-Loop Conversational Steering & Price Arbitrage Router
Coordinates:
1. Entity Disambiguation (Indic synonyms, fuzzy crop and district extraction)
2. Live/Historical Mandi Price Ingestion (Agmarknet data engine)
3. Multi-Mandi Arbitrage & Transport Profit Calculation
4. Govt MSP Benchmark Protection
5. Spoken Hindi Response Synthesis for Gnani TTS
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
    # Gram / Pulses
    "चना": "Gram Raw(Chholia)", "छोलिया": "Gram Raw(Chholia)", "chana": "Gram Raw(Chholia)", "gram": "Gram Raw(Chholia)",
    "मूँग": "Green Gram(Moong)(Whole)", "मूंग": "Green Gram(Moong)(Whole)", "moong": "Green Gram(Moong)(Whole)",
    "मसूर": "Masur Dal", "masur": "Masur Dal",
    "मटर": "Peas(Dry)", "matar": "Peas(Dry)", "peas": "Peas(Dry)",
    # Coarse cereals & Oilseeds
    "जौ": "Barley(Jau)", "jau": "Barley(Jau)", "barley": "Barley(Jau)",
    "मक्का": "Maize", "makka": "Maize", "bhutta": "Maize", "maize": "Maize",
    "मूंगफली": "Groundnut", "mungfali": "Groundnut", "groundnut": "Groundnut",
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

    def _load_msp_data(self) -> Dict[str, Any]:
        if os.path.exists(MSP_FILE):
            with open(MSP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("2026_27", {})
        return {}

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

    def process_request(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        district: Optional[str] = None,
        crop: Optional[str] = None,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Processes request and synthesizes spoken response."""
        # Step 1: Parse entities if query provided
        if query:
            extracted = self.parse_entities(query)
            state = state or extracted["state"]
            district = district or extracted["district"]
            crop = crop or extracted["crop"]

        # Default fallbacks if omitted
        state = state or "Uttar Pradesh"
        district = district or "Jhansi"
        crop = crop or "Wheat"

        # Step 2: Fetch pricing data
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

        # Fallback to historical baseline if live returned 0 or old date requested
        if not records:
            norm_date = normalize_date(date) if date and date.lower() != "today" else None
            hist_records, _ = self.service.fetch_historical(state, district, crop, target_date=norm_date)
            records = hist_records
            if records:
                reporting_date = records[0].get("arrival_date")

        # Step 3: Run Arbitrage and MSP Analysis
        arbitrage = self.calculate_arbitrage(records)
        msp = self.get_msp(crop)

        # Step 4: Synthesize Spoken Indic Output for Gnani TTS
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

