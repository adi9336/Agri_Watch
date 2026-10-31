"""
Unit Tests for Agri_watch LangGraph Pipeline
Verifies:
1. Indic NLU intent classification & entity resolution
2. Non-looping conversational continuity
3. Disambiguation prompt generation for missing entities
4. Mandi Price discovery & fallback
5. Multi-mandi transportation arbitrage calculations
6. MSP benchmark floor check
7. Multi-turn cross-query context retention
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
        self.assertEqual(out.get("intent"), "GREETING")
        self.assertIn("राम राम", out.get("spoken_hindi_response", ""))

    def test_missing_crop_clarification(self):
        state: AgentState = {"user_query": "झाँसी की मंडी का भाव बताओ", "session_context": {}}
        out = self.graph.invoke(state)
        self.assertEqual(out.get("status"), "clarification")
        self.assertIn("फसल का भाव", out.get("spoken_hindi_response", ""))

    def test_price_inquiry_with_data(self):
        state: AgentState = {"user_query": "झाँसी में गेहूँ का क्या रेट है?", "session_context": {}}
        out = self.graph.invoke(state)
        self.assertEqual(out.get("intent"), "PRICE_INQUIRY")
        self.assertEqual(out.get("crop"), "Wheat")
        self.assertEqual(out.get("district"), "Jhansi")
        self.assertIsNotNone(out.get("mandi_records"))
        self.assertTrue(len(out.get("mandi_records", [])) > 0)
        self.assertIn("गेहूँ", out.get("spoken_hindi_response", ""))

    def test_arbitrage_calculation(self):
        state: AgentState = {"user_query": "कहाँ बेचना फायदेमंद रहेगा गेहूँ?", "session_context": {"district": "Jhansi"}}
        out = self.graph.invoke(state)
        self.assertEqual(out.get("intent"), "ARBITRAGE")
        self.assertIsNotNone(out.get("arbitrage_result"))
        self.assertIn("मुनाफा", out.get("spoken_hindi_response", ""))

    def test_msp_floor_check(self):
        state: AgentState = {"user_query": "गेहूँ का सरकारी समर्थन मूल्य क्या है?", "session_context": {}}
        out = self.graph.invoke(state)
        self.assertEqual(out.get("intent"), "MSP")
        self.assertIsNotNone(out.get("msp_comparison"))
        self.assertEqual(out["msp_comparison"].get("msp_rate"), 2275)
        self.assertIn("2275", out.get("spoken_hindi_response", ""))

    def test_continuation_does_not_loop(self):
        # First turn: Wheat inquiry
        turn1: AgentState = {"user_query": "झाँसी में गेहूँ का भाव बताओ", "session_context": {}}
        out1 = self.graph.invoke(turn1)
        self.assertEqual(out1.get("crop"), "Wheat")

        # Second turn: User says "हाँ ठीक है"
        turn2: AgentState = {"user_query": "हाँ ठीक है", "session_context": out1.get("session_context", {})}
        out2 = self.graph.invoke(turn2)
        self.assertEqual(out2.get("intent"), "CONTINUATION")
        # Ensure it does NOT re-quote the same price; it should prompt for next crop
        self.assertIn("अन्य फसल", out2.get("spoken_hindi_response", ""))


if __name__ == "__main__":
    unittest.main()
