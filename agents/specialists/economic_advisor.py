"""
Agri_watch - Specialized Economic & Holding Strategy Sub-Agent
An isolated expert agent for deep financial, storage holding ROI,
and vehicle freight logistics optimization.

Design Pattern: Progressive Disclosure (Invoked only on explicit demand)
Preserves the lean speed of the primary conversational agent.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

from agents.tools import get_crop_price_trend, compare_mandi_arbitrage, check_msp_floor

logger = logging.getLogger("agriwatch.specialist.economic")

# Storage & Warehousing Benchmarks (WDRA / Central Warehousing Corporation)
WAREHOUSE_RENT_PER_QUINTAL_PER_MONTH = 6.0   # ₹6/quintal/month
HANDLING_FUMIGATION_PER_QUINTAL = 1.0        # ₹1/quintal
SHRINKAGE_RATE = 0.005                       # 0.5% moisture weight shrinkage

# Vehicle Capacity & Freight Benchmarks (Round trip fuel & operating rate)
VEHICLE_CONFIGS = {
    "tractor": {
        "name_hi": "ट्रैक्टर-ट्रॉली",
        "default_capacity": 50.0,
        "rate_per_km": 20.0
    },
    "pickup": {
        "name_hi": "पिकअप (बोलेरो)",
        "default_capacity": 25.0,
        "rate_per_km": 15.0
    },
    "truck": {
        "name_hi": "ट्रक",
        "default_capacity": 140.0,
        "rate_per_km": 35.0
    }
}


def evaluate_holding_strategy(
    crop: str,
    district: str,
    holding_days: int = 30,
    quantity_quintals: float = 50.0,
    state: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes deterministic storage holding ROI vs recent 30-day price trend slope.
    Returns whether the farmer should Sell Now, Hold & Store, or if it is Neutral.
    """
    # 1. Fetch 30-day historical time-series analytics
    trend_raw = get_crop_price_trend(crop=crop, district=district, timeframe=f"{holding_days}d", state=state)
    trend_data = json.loads(trend_raw) if isinstance(trend_raw, str) else trend_raw
    
    if trend_data.get("status") != "success":
        # Fallback if no historical data exists
        msg = f"किसान भाई, {district} में {crop} का पुराना रिकॉर्ड उपलब्ध नहीं है, इसलिए बाज़ार में वर्तमान भाव पर बेचना ही सुरक्षित रहेगा।"
        return {
            "status": "partial",
            "decision": "SELL_NOW",
            "companion_summary_hi": msg
        }

    latest_price = float(trend_data.get("latest_price", "0").replace("₹", "").replace(",", "") or 0)
    min_price = float(trend_data.get("min_price", 0))
    max_price = float(trend_data.get("max_price", 0))
    trend_dir = trend_data.get("trend_direction", "STABLE")
    
    raw_change = trend_data.get("price_change_rs", "₹0").replace("₹", "").replace(",", "")
    try:
        price_change_rs = float(raw_change)
    except ValueError:
        price_change_rs = 0.0

    # 2. Compute Deterministic Holding Costs
    months = max(1.0, holding_days / 30.0)
    rent_cost = (WAREHOUSE_RENT_PER_QUINTAL_PER_MONTH + HANDLING_FUMIGATION_PER_QUINTAL) * months
    shrinkage_cost = latest_price * SHRINKAGE_RATE
    total_holding_cost_per_qtl = round(rent_cost + shrinkage_cost, 2)
    total_batch_holding_cost = round(total_holding_cost_per_qtl * quantity_quintals, 2)

    # 3. Compute Net Projected Gain / Loss
    # If trend is RISING, assume price momentum continues at current velocity
    projected_price_gain_per_qtl = price_change_rs if trend_dir == "RISING" else 0.0
    net_gain_per_qtl = round(projected_price_gain_per_qtl - total_holding_cost_per_qtl, 2)
    net_total_gain = round(net_gain_per_qtl * quantity_quintals, 2)

    # 4. Formulate Actionable Verdict
    if trend_dir == "RISING" and net_gain_per_qtl > 25.0:
        decision = "HOLD"
        spoken = (
            f"किसान भाई, पिछले एक महीने में {crop} का भाव ₹{int(abs(price_change_rs))} चढ़ा है। "
            f"वेयरहाउस का खर्च लगभग ₹{int(round(total_holding_cost_per_qtl))} प्रति क्विंटल कटेगा, "
            f"इसलिए माल रोक कर बेचने पर आपको लगभग ₹{int(round(net_total_gain))} का शुद्ध मुनाफा होने की संभावना है।"
        )
    elif trend_dir == "FALLING" or net_gain_per_qtl < 0:
        decision = "SELL_NOW"
        spoken = (
            f"किसान भाई, {district} में {crop} का भाव गिर रहा है। "
            f"वेयरहाउस में रखने से ₹{int(round(total_holding_cost_per_qtl))} प्रति क्विंटल का अतिरिक्त खर्च लगेगा, "
            f"इसलिए फसल अभी मंडी में बेचना ही समझदारी होगी।"
        )
    else:
        decision = "NEUTRAL"
        spoken = (
            f"किसान भाई, {crop} का भाव पिछले महीने लगभग स्थिर रहा है। "
            f"वेयरहाउस का खर्च लगभग ₹{int(round(total_holding_cost_per_qtl))} प्रति क्विंटल आएगा, "
            f"इसलिए अभी बेचने या रोकने में विशेष फर्क नहीं पड़ेगा।"
        )

    return {
        "status": "success",
        "crop": crop,
        "district": district,
        "decision": decision,
        "latest_price": latest_price,
        "price_change_rs": price_change_rs,
        "holding_cost_per_qtl": total_holding_cost_per_qtl,
        "total_holding_cost": total_batch_holding_cost,
        "net_gain_per_qtl": net_gain_per_qtl,
        "net_total_gain": net_total_gain,
        "quantity_quintals": quantity_quintals,
        "holding_days": holding_days,
        "companion_summary_hi": spoken
    }


def evaluate_vehicle_arbitrage(
    crop: str,
    district: str,
    vehicle_type: str = "tractor",
    load_quintals: Optional[float] = None,
    state: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes exact freight transport economics based on specific vehicle type and load size.
    """
    config = VEHICLE_CONFIGS.get(vehicle_type.lower(), VEHICLE_CONFIGS["tractor"])
    load = load_quintals or config["default_capacity"]
    
    # Run standard arbitrage scan
    arb_raw = compare_mandi_arbitrage(crop=crop, district=district, state=state)
    arb = json.loads(arb_raw) if isinstance(arb_raw, str) else arb_raw
    
    if arb.get("status") != "success" or not arb.get("best_market"):
        msg = f"किसान भाई, {district} के आसपास {crop} के लिए कोई अन्य मंडी अधिक दाम नहीं दे रही है। स्थानीय मंडी में ही बेचना बेहतर है।"
        return {"status": "no_arbitrage", "companion_summary_hi": msg}

    dest_market = arb.get("best_market")
    dist_km = 45.0  # Average inter-mandi transport distance
    price_diff = float(arb.get("price_difference", 0))

    # Recalculate freight for this specific vehicle and load
    total_fuel_cost = dist_km * config["rate_per_km"]
    transport_per_qtl = round(total_fuel_cost / load, 2)
    net_profit_per_qtl = round(price_diff - transport_per_qtl, 2)
    total_net_profit = round(net_profit_per_qtl * load, 2)

    veh_name = config["name_hi"]

    if net_profit_per_qtl > 15.0:
        spoken = (
            f"किसान भाई, {veh_name} से {dest_market} मंडी जाने पर {load:.0f} क्विंटल माल में "
            f"भाड़ा काटकर लगभग ₹{int(round(total_net_profit))} का शुद्ध मुनाफा बचेगा।"
        )
    else:
        spoken = (
            f"किसान भाई, {veh_name} से {dest_market} जाने पर भाड़ा अधिक लग जाएगा "
            f"और फायदा नहीं होगा। स्थानीय मंडी में ही बेचना ठीक रहेगा।"
        )

    return {
        "status": "success",
        "crop": crop,
        "district": district,
        "target_market": dest_market,
        "vehicle_type": vehicle_type,
        "load_quintals": load,
        "distance_km": dist_km,
        "price_difference": price_diff,
        "transport_per_qtl": transport_per_qtl,
        "net_profit_per_qtl": net_profit_per_qtl,
        "total_net_profit": total_net_profit,
        "companion_summary_hi": spoken
    }


def run_economic_specialist(
    query_type: str,
    crop: str,
    district: str,
    holding_days: int = 30,
    vehicle_type: str = "tractor",
    quantity_quintals: float = 50.0,
    state: Optional[str] = None
) -> Dict[str, Any]:
    """
    Unified entry point for the Economic Specialist Sub-Agent.
    Handles 'holding_strategy' and 'vehicle_freight'.
    """
    logger.info(f"[*] Economic Specialist Sub-Agent activated: type={query_type}, crop={crop}, district={district}")
    
    if query_type in ("holding_strategy", "storage", "wait_vs_sell"):
        return evaluate_holding_strategy(
            crop=crop,
            district=district,
            holding_days=holding_days,
            quantity_quintals=quantity_quintals,
            state=state
        )
    elif query_type in ("vehicle_freight", "transport_detail"):
        return evaluate_vehicle_arbitrage(
            crop=crop,
            district=district,
            vehicle_type=vehicle_type,
            load_quintals=quantity_quintals,
            state=state
        )
    else:
        # Default to holding strategy
        return evaluate_holding_strategy(
            crop=crop,
            district=district,
            holding_days=holding_days,
            quantity_quintals=quantity_quintals,
            state=state
        )
