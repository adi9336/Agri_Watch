"""
Unit Tests for Agri_watch Specialized Economic & Holding Sub-Agent
Verifies Progressive Disclosure pattern:
1. Holding cost arithmetic and robust trend estimation
2. Hold-or-sell decisions and their guard rails (thin data, perishables)
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
from datetime import datetime, timedelta
from agents.specialists.economic_advisor import (
    evaluate_holding_strategy,
    holding_cost_per_qtl,
    theil_sen
)


class TestSpecialistSubAgent(unittest.TestCase):
    def test_holding_strategy_math(self):
        # Test holding calculation on Wheat in Jhansi
        res = evaluate_holding_strategy(crop="Wheat", district="Jhansi", holding_days=30, quantity_quintals=50.0)
        self.assertIn(res.get("status"), ["success", "partial"])
        self.assertIn(res.get("decision"), ["HOLD", "SELL_NOW", "NEUTRAL", "NO_FORECAST"])
        self.assertIn("holding_cost_per_qtl", res)
        self.assertIn("companion_summary_hi", res)
        # Check that voice response contains relevant keywords
        spoken = res["companion_summary_hi"]
        self.assertTrue(any(w in spoken for w in ["वेयरहाउस", "खर्च", "फसल", "मंडी", "बेचना"]))

    def test_holding_cost_components(self):
        cost = holding_cost_per_qtl(price=3000.0, holding_days=45)
        self.assertEqual(cost["warehouse_rent"], 12.0)    # 2 started months x ₹6
        self.assertEqual(cost["handling"], 10.0)
        self.assertEqual(cost["storage_loss"], 22.5)      # 0.5%/month x 1.5 months x ₹3000
        self.assertAlmostEqual(cost["interest"], 25.9, places=1)  # 7%/yr x 45/365 x ₹3000
        self.assertAlmostEqual(cost["total"], 70.4, places=1)

    def test_theil_sen_ignores_outlier(self):
        start = datetime(2026, 9, 1)
        series = [(start + timedelta(days=i), 2000.0 + 10 * i) for i in range(10)]
        series[5] = (series[5][0], 5000.0)                # one bad variety report
        trend = theil_sen(series)
        self.assertAlmostEqual(trend["slope"], 10.0, delta=1.0)
        self.assertGreaterEqual(trend["agreement"], 0.7)

    def test_perishable_crop_never_holds(self):
        res = evaluate_holding_strategy(crop="Onion", district="Nashik", holding_days=30)
        self.assertEqual(res.get("decision"), "NO_FORECAST")

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
