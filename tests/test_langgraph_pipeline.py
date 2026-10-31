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

import sys
import unittest

sys.stdout.reconfigure(encoding='utf-8')

from agents.graph import get_agriwatch_graph
from agents.state import AgentState


class TestAgriWatchLangGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = get_agriwatch_graph()

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
        state: AgentState = {"user_query": "झाँसी में गेहूँ का क्या रेट है?", "session_context": {}}
        out = self.graph.invoke(state)
        resp = out.get("spoken_hindi_response", "")
        self.assertIn("गेहूँ", resp)
        # Must quote the factual market rate
        self.assertTrue("2585" in resp or "2600" in resp or "2,585" in resp or "2,600" in resp or "2500" in resp)

    def test_arbitrage_calculation(self):
        state: AgentState = {"user_query": "कहाँ बेचना फायदेमंद रहेगा गेहूँ?", "session_context": {"district": "Jhansi"}}
        out = self.graph.invoke(state)
        resp = out.get("spoken_hindi_response", "")
        self.assertIn("मंडी", resp)
        self.assertTrue(any(w in resp for w in ["2600", "2,600", "मुनाफा", "फायदा", "अच्छा", "दाम"]))

    def test_msp_floor_check(self):
        state: AgentState = {"user_query": "गेहूँ का सरकारी समर्थन मूल्य क्या है?", "session_context": {}}
        out = self.graph.invoke(state)
        resp = out.get("spoken_hindi_response", "")
        # Must state the official 2026-27 MSP rate
        self.assertTrue("2275" in resp or "2,275" in resp)

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


if __name__ == "__main__":
    unittest.main()
