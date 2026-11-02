"""
Unit Tests for Agri_watch Specialized Economic & Holding Sub-Agent
Verifies Progressive Disclosure pattern:
1. Deterministic storage holding ROI math
2. Vehicle freight calculations
3. LangGraph autonomous delegation to the specialist on explicit farmer demand
"""

import os
import sys
import unittest

sys.stdout.reconfigure(encoding='utf-8')

# Ensure parent directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from agents.graph import get_agriwatch_graph
from agents.state import AgentState
from agents.specialists.economic_advisor import (
    evaluate_holding_strategy,
    evaluate_vehicle_arbitrage,
    run_economic_specialist
)


class TestSpecialistSubAgent(unittest.TestCase):
    def test_holding_strategy_math(self):
        # Test holding calculation on Wheat in Jhansi
        res = evaluate_holding_strategy(crop="Wheat", district="Jhansi", holding_days=30, quantity_quintals=50.0)
        self.assertIn(res.get("status"), ["success", "partial"])
        self.assertIn(res.get("decision"), ["HOLD", "SELL_NOW", "NEUTRAL"])
        self.assertIn("holding_cost_per_qtl", res)
        self.assertIn("companion_summary_hi", res)
        # Check that voice response contains relevant keywords
        spoken = res["companion_summary_hi"]
        self.assertTrue(any(w in spoken for w in ["वेयरहाउस", "खर्च", "फसल", "मंडी", "बेचना"]))

    def test_vehicle_arbitrage_math(self):
        # Test tractor load calculation
        res = evaluate_vehicle_arbitrage(crop="Wheat", district="Jhansi", vehicle_type="tractor", load_quintals=50.0)
        self.assertIn("companion_summary_hi", res)
        spoken = res["companion_summary_hi"]
        self.assertTrue(len(spoken) > 10)

    def test_langgraph_invokes_specialist_on_holding_query(self):
        graph = get_agriwatch_graph()
        # Farmer explicitly asks if they should hold in warehouse or sell now
        state: AgentState = {
            "user_query": "झाँसी में गेहूँ को वेयरहाउस में रोक कर रखें या अभी बेचें? पूरा हिसाब बताओ",
            "session_context": {}
        }
        out = graph.invoke(state)
        resp = out.get("spoken_hindi_response", "")
        # Response should contain warehouse / holding / selling advice
        self.assertTrue(any(w in resp for w in ["वेयरहाउस", "रोक", "खर्च", "बेचना", "मंडी", "फायदा", "नुकसान"]))


if __name__ == "__main__":
    unittest.main()
