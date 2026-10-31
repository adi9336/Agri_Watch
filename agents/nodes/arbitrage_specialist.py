"""
Agri_watch - LangGraph Multi-Mandi Arbitrage Specialist Node
Calculates price spread between mandis, factors in transport/diesel logistics,
and computes actionable net profit for the farmer.
"""

from typing import Dict, Any, List
from agents.state import AgentState
from agents.observability import traceable


@traceable(name="LangGraphNode:ArbitrageSpecialist", run_type="tool")
def arbitrage_specialist_node(state: AgentState) -> Dict[str, Any]:
    """
    Analyzes price spread between local and neighboring mandis,
    deducts freight costs, and determines whether inter-mandi transport is profitable.
    """
    records = state.get("mandi_records") or []
    if not records:
        return {"arbitrage_result": None}

    # Group by market and keep the latest record for each distinct market
    market_latest: Dict[str, Dict[str, Any]] = {}
    for r in records:
        m_name = r.get("market")
        if not m_name:
            continue
        try:
            modal = float(r.get("modal_price", 0))
            if modal <= 0:
                continue
        except (ValueError, TypeError):
            continue

        if m_name not in market_latest:
            market_latest[m_name] = {**r, "modal_float": modal}

    valid_markets = list(market_latest.values())
    if len(valid_markets) < 2:
        return {"arbitrage_result": None}

    valid_markets.sort(key=lambda x: x["modal_float"], reverse=True)
    top_mandi = valid_markets[0]
    lowest_mandi = valid_markets[-1]

    spread = top_mandi["modal_float"] - lowest_mandi["modal_float"]
    # Standard rural tempo/tractor trolley transport cost: ~Rs 15-20/quintal for 25km trip
    transport_cost_per_q = 15.0
    standard_load_quintals = 25.0
    net_gain = (spread - transport_cost_per_q) * standard_load_quintals if spread > transport_cost_per_q else 0.0

    arbitrage_data = {
        "top_market": top_mandi.get("market"),
        "top_modal": top_mandi.get("modal_float"),
        "top_variety": top_mandi.get("variety"),
        "top_date": top_mandi.get("arrival_date"),
        "lowest_market": lowest_mandi.get("market"),
        "lowest_modal": lowest_mandi.get("modal_float"),
        "spread": spread,
        "recommend_arbitrage": spread > 30.0,
        "estimated_net_gain_25q": net_gain,
        "total_mandis_reporting": len(valid_markets)
    }

    return {
        "arbitrage_result": arbitrage_data
    }
