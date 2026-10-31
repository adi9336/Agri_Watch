"""
Agri_watch - LangGraph MSP Benchmark Protection Specialist Node
Compares current mandi prices against official Government Minimum Support Price (MSP)
to alert farmers against distress selling and underpayment.
"""

import os
import json
from typing import Dict, Any, Optional
from agents.state import AgentState
from agents.observability import traceable

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
MSP_FILE = os.path.join(PROJECT_ROOT, "data", "msp_benchmarks.json")

_msp_cache: Optional[Dict[str, Any]] = None

def load_msp_benchmarks() -> Dict[str, Any]:
    global _msp_cache
    if _msp_cache is None:
        if os.path.exists(MSP_FILE):
            with open(MSP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                _msp_cache = data.get("2026_27", {})
        else:
            _msp_cache = {}
    return _msp_cache


@traceable(name="LangGraphNode:MSPSpecialist", run_type="tool")
def msp_specialist_node(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates official MSP floor for the requested crop and compares it with modal mandi rates.
    """
    crop = state.get("crop")
    if not crop:
        return {"msp_comparison": None}

    benchmarks = load_msp_benchmarks()
    msp_info = None

    for key, val in benchmarks.items():
        if key.lower() in crop.lower() or crop.lower() in key.lower():
            msp_info = val
            break

    if not msp_info:
        return {"msp_comparison": None}

    msp_rate = msp_info.get("msp")
    records = state.get("mandi_records") or []
    modal_price = None

    if records:
        try:
            modal_price = float(records[0].get("modal_price", 0))
        except (ValueError, TypeError):
            pass

    comparison = {
        "crop": crop,
        "msp_rate": msp_rate,
        "season": msp_info.get("season"),
        "modal_price": modal_price,
        "is_below_msp": (modal_price < msp_rate) if modal_price and msp_rate else False,
        "deficit": (msp_rate - modal_price) if modal_price and msp_rate and modal_price < msp_rate else 0.0
    }

    return {
        "msp_comparison": comparison
    }
