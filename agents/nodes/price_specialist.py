"""
Agri_watch - LangGraph Mandi Price Specialist Node
Fetches live APMC prices from data.gov.in API with instant fallback to
historical database snapshot and nearby mandis when the local mandi is closed.
"""

from typing import Dict, Any, List, Optional
from agents.state import AgentState
from agents.observability import traceable
from mandi_tracker import MandiPriceService


# Shared singleton instance
_price_service: Optional[MandiPriceService] = None

def get_price_service() -> MandiPriceService:
    global _price_service
    if _price_service is None:
        _price_service = MandiPriceService()
    return _price_service


@traceable(name="LangGraphNode:MandiPriceSpecialist", run_type="tool")
def price_specialist_node(state: AgentState) -> Dict[str, Any]:
    """
    Fetches wholesale mandi rates for the specified commodity and district.
    Employs live data.gov.in API with automatic fallback to historical cache.
    """
    crop = state.get("crop")
    district = state.get("district") or "Jhansi"
    state_name = state.get("state") or "Uttar Pradesh"

    service = get_price_service()
    records: List[Dict[str, Any]] = []
    reporting_date: Optional[str] = None
    is_live = False

    # 1. Attempt Live API lookup
    if service.api_key:
        try:
            direct, state_wide, rep_date = service.fetch_live_prices(state_name, district, crop)
            if direct:
                records = direct
                is_live = True
                reporting_date = rep_date
            elif state_wide:
                records = state_wide
                reporting_date = rep_date
        except Exception as e:
            # Fall back safely
            pass

    # 2. Historical APMC snapshot fallback
    if not records:
        try:
            hist_records, _ = service.fetch_historical(state_name, district, crop)
            if hist_records:
                records = hist_records
                reporting_date = records[0].get("arrival_date")
        except Exception:
            pass

    return {
        "mandi_records": records,
        "reporting_date": reporting_date,
        "is_live": is_live,
        "status": "success" if records else "no_data"
    }
