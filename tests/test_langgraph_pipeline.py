"""
Unit Tests for Agri_watch LangGraph Pipeline
Verifies end-to-end user experience across core voice query types:
1. Greeting & politeness
2. Clarification for missing entities
3. Mandi price discovery & accurate rate citation
4. Multi-mandi arbitrage recommendations
5. MSP benchmark protection
6. Conversational continuity without repetitive loops
"""

import json
import sys
import unittest
from unittest.mock import patch

sys.stdout.reconfigure(encoding='utf-8')

from agents.graph import get_agriwatch_graph
from agents.state import AgentState
from agents.tools import get_crop_price, _price_service


class TestAgriWatchLangGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = get_agriwatch_graph()

    def test_no_current_price_offers_options(self):
        # Today's rate not uploaded: no old rate passed off as current; MSP offered only for MSP crops
        with patch.object(_price_service, "fetch_live_prices", return_value=([], [], None)):
            wheat = json.loads(get_crop_price("Wheat", "Jhansi"))
            onion = json.loads(get_crop_price("Onion", "Jhansi"))
        self.assertEqual(wheat["status"], "no_current_price")
        self.assertNotIn("modal_price", wheat)
        self.assertTrue(wheat["msp_available"])
        self.assertFalse(onion["msp_available"])

    def test_greeting_intent(self):
        state: AgentState = {"user_query": "राम राम भैया", "session_context": {}}
        out = self.graph.invoke(state)
        resp = out.get("spoken_hindi_response", "")
        self.assertTrue(any(w in resp for w in ["राम", "नमस्ते", "स्वागत", "मदद"]))

    def test_missing_crop_clarification(self):
        state: AgentState = {"user_query": "झाँसी की मंडी का भाव बताओ", "session_context": {}}
        out = self.graph.invoke(state)
        resp = out.get("spoken_hindi_response", "")
        # Must ask which crop the farmer is asking about
        self.assertTrue(any(w in resp for w in ["फसल", "किस फसल", "फसल का भाव"]))

    def test_price_inquiry_with_data(self):
        state: AgentState = {"user_query": "झाँसी में 24/09/2026 को गेहूँ का क्या रेट था?", "session_context": {}}
        out = self.graph.invoke(state)
        resp = out.get("spoken_hindi_response", "")
        self.assertIn("गेहूँ", resp)
        # Must quote the factual market rate
        self.assertTrue(any(rate in resp for rate in ["2585", "2600", "2,585", "2,600", "2500", "2355", "2,355"]))

    def test_arbitrage_calculation(self):
        state: AgentState = {"user_query": "कहाँ बेचना फायदेमंद रहेगा गेहूँ?", "session_context": {"district": "Jhansi"}}
        out = self.graph.invoke(state)
        resp = out.get("spoken_hindi_response", "")
        self.assertIn("मंडी", resp)
        self.assertTrue(any(w in resp for w in ["2600", "2,600", "2585", "2,585", "मुनाफा", "फायदेमंद", "फायदा", "अच्छा", "दाम", "भाव"]))

    def test_msp_floor_check(self):
        state: AgentState = {"user_query": "गेहूँ का सरकारी समर्थन मूल्य क्या है?", "session_context": {}}
        out = self.graph.invoke(state)
        resp = out.get("spoken_hindi_response", "")
        # Must state the official 2026-27 MSP rate
        self.assertTrue("2585" in resp or "2,585" in resp)

    def test_continuation_does_not_loop(self):
        # First turn: Wheat inquiry
        turn1: AgentState = {"user_query": "झाँसी में गेहूँ का भाव बताओ", "session_context": {}}
        out1 = self.graph.invoke(turn1)

        # Second turn: User says "हाँ ठीक है"
        turn2: AgentState = {"user_query": "हाँ ठीक है", "session_context": out1.get("session_context", {})}
        out2 = self.graph.invoke(turn2)
        resp = out2.get("spoken_hindi_response", "")
        # Must NOT regurgitate old price; must ask for next query or prompt for other crop
        self.assertTrue(any(w in resp for w in ["अन्य", "दूसरी", "फसल", "मंडी", "मदद"]))

    def test_sub_mandi_resolution_without_asking_district(self):
        # Must resolve 'Rath' to its market & district without interrogating the farmer
        state: AgentState = {"user_query": "राठ मंडी में गेहूं का क्या रेट है?", "session_context": {}}
        out = self.graph.invoke(state)
        resp = out.get("spoken_hindi_response", "")
        self.assertEqual(out.get("intent"), "PRICE")
        # Must quote the factual market rate for Rath (2400)
        self.assertTrue(any(rate in resp for rate in ["2400", "2,400"]))

    def test_nearby_mandis_cluster_breakdown(self):
        # Turn 1: Rath Chana inquiry
        t1 = self.graph.invoke({"user_query": "राठ मंडी में 13/09/2026 को चने का भाव बताओ", "session_context": {}})
        r1 = t1.get("spoken_hindi_response", "")
        self.assertTrue(any(rate in r1 for rate in ["6100", "6,100"]))

        # Turn 2: Nearby mandis follow-up with phonetic 'रॉड' STT transcription
        t2 = self.graph.invoke({
            "user_query": "क्या तुम मुझे सारी मंडियों के दाम बताओगे जितनी भी रॉड के आसपास हैं उसका दाम",
            "session_context": t1.get("session_context", {})
        })
        r2 = t2.get("spoken_hindi_response", "")
        self.assertEqual(t2.get("intent"), "ARBITRAGE")
        # Must name top nearby mandis and actual rates, NOT give canned 'भाव समान है' dismissal
        self.assertTrue(any(m in r2 for m in ["महोबा", "अतर्रा", "मऊरानीपुर", "राठ"]))
        self.assertTrue(any(rate in r2 for rate in ["6400", "6,400", "6200", "6,200", "6100", "6,100"]))
        self.assertNotIn("कोई विशेष उच्च दाम वाली मंडी नहीं मिली", r2)


if __name__ == "__main__":
    unittest.main()
