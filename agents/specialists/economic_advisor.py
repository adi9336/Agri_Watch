"""
Agri_watch - Hold-or-Sell Economic Advisor
Deterministic (non-LLM) analysis of whether storing a crop for N days is likely to
beat selling today. Invoked only when the farmer explicitly asks about holding,
storage or warehouse costs.

Method:
1. Build a daily price series (median modal price per date) for the farmer's mandi,
   or the whole district when the mandi has too few reports, over the last 60 days.
2. Estimate the trend with a Theil-Sen slope (median of all pairwise slopes), which
   is robust to the variety/outlier noise common in Agmarknet data. The 25th and
   75th percentile pairwise slopes give a pessimistic/optimistic band.
3. Project the price change over the holding period (never further ahead than the
   history we have) and compare it with the full cost of holding: warehouse rent,
   handling, storage loss and interest on the money tied up.
4. Recommend HOLD only if even the pessimistic projection covers the holding cost.
   Too little or stale data, or a perishable crop, never yields a HOLD.
"""

import os
import csv
import json
import logging
import statistics
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from mandi_tracker import is_commodity_match
from agents.tools import (
    CROP_NORM_MAP, _price_service, resolve_location, clean_market_name, lookup_msp
)

logger = logging.getLogger("agriwatch.specialist.economic")

# Holding cost assumptions (approximate defaults; tune per region/warehouse)
WAREHOUSE_RENT_PER_QTL_MONTH = 6.0   # ₹ per quintal per month, billed by started month
HANDLING_PER_QTL = 10.0              # ₹ per quintal, loading/unloading in and out
STORAGE_LOSS_PCT_PER_MONTH = 0.5     # % of crop value lost per month (moisture/pests)
ANNUAL_INTEREST_RATE = 0.07          # Cost of money tied up (e.g. warehouse-receipt loan)

# Analysis parameters
LOOKBACK_DAYS = 60                   # History window ending at the latest report
MIN_POINTS = 6                       # Minimum reporting dates for any forecast
MIN_SPAN_DAYS = 14                   # Minimum days covered by those dates
STALE_AFTER_DAYS = 10                # Latest report older than this lowers confidence
HOLD_MARGIN_PER_QTL = 25.0           # Pessimistic gain must beat cost by at least this

PERISHABLE_CROPS = {"onion", "potato", "tomato", "cabbage", "cauliflower", "brinjal", "banana"}
HINDI_CROP_NAMES = {"Onion": "प्याज", "Potato": "आलू", "Tomato": "टमाटर", "Peas(Dry)": "मटर"}


def _parse_date(d: str) -> Optional[datetime]:
    try:
        return datetime.strptime((d or "").strip(), "%d/%m/%Y")
    except ValueError:
        return None


def build_price_series(crop: str, district: str, state: Optional[str]) -> Dict[str, Any]:
    """Daily median modal prices for the farmer's mandi (or district) over the lookback window."""
    norm_crop = CROP_NORM_MAP.get(crop.lower().strip(), crop.strip())
    resolved_dist, resolved_market, resolved_state = resolve_location(district, state)
    market_key = clean_market_name(resolved_market).lower() if resolved_market else ""

    by_market: Dict[datetime, List[float]] = {}
    by_district: Dict[datetime, List[float]] = {}

    def _add(row: Dict[str, Any]):
        if (row.get("district") or "").strip().lower() != resolved_dist.lower():
            return
        if not is_commodity_match(norm_crop, row.get("commodity", "")):
            return
        dt = _parse_date(row.get("arrival_date", ""))
        try:
            price = float(row.get("modal_price", 0))
        except (ValueError, TypeError):
            return
        if not dt or price <= 0:
            return
        by_district.setdefault(dt, []).append(price)
        if market_key and market_key in (row.get("market") or "").lower():
            by_market.setdefault(dt, []).append(price)

    cache_file = _price_service.ensure_local_cache()
    if os.path.exists(cache_file):
        with open(cache_file, mode="r", encoding="utf-8", errors="ignore") as f:
            for row in csv.DictReader(f):
                _add(row)
    if _price_service.api_key:
        try:
            direct, _, _ = _price_service.fetch_live_prices(resolved_state, resolved_dist, norm_crop, market=resolved_market)
            for row in direct or []:
                _add(row)
        except Exception as e:
            logger.info(f"[*] Live prices unavailable for holding analysis: {e}")

    def _window(points: Dict[datetime, List[float]]) -> List[Tuple[datetime, float]]:
        if not points:
            return []
        latest = max(points)
        return sorted((d, statistics.median(p)) for d, p in points.items() if (latest - d).days <= LOOKBACK_DAYS)

    market_series = _window(by_market)
    use_market = len(market_series) >= MIN_POINTS
    return {
        "crop": norm_crop,
        "district": resolved_dist,
        "scope": clean_market_name(resolved_market) if use_market else resolved_dist,
        "scope_level": "mandi" if use_market else "district",
        "series": market_series if use_market else _window(by_district),
    }


def theil_sen(series: List[Tuple[datetime, float]]) -> Dict[str, float]:
    """Robust trend: median pairwise slope (₹/day) with 25th/75th percentile band and sign agreement."""
    slopes = []
    for i in range(len(series)):
        for j in range(i + 1, len(series)):
            days = (series[j][0] - series[i][0]).days
            if days > 0:
                slopes.append((series[j][1] - series[i][1]) / days)
    slopes.sort()
    q = statistics.quantiles(slopes, n=4) if len(slopes) >= 4 else [slopes[0], statistics.median(slopes), slopes[-1]]
    median_slope = statistics.median(slopes)
    same_sign = sum(1 for s in slopes if (s > 0) == (median_slope > 0)) / len(slopes) if median_slope else 0.0
    return {"slope": median_slope, "slope_low": q[0], "slope_high": q[2], "agreement": same_sign}


def holding_cost_per_qtl(price: float, holding_days: int) -> Dict[str, float]:
    months_billed = max(1, -(-holding_days // 30))  # Warehouses bill each started month
    cost = {
        "warehouse_rent": WAREHOUSE_RENT_PER_QTL_MONTH * months_billed,
        "handling": HANDLING_PER_QTL,
        "storage_loss": price * STORAGE_LOSS_PCT_PER_MONTH / 100 * holding_days / 30,
        "interest": price * ANNUAL_INTEREST_RATE * holding_days / 365,
    }
    cost = {k: round(v, 1) for k, v in cost.items()}
    cost["total"] = round(sum(cost.values()), 1)
    return cost


def evaluate_holding_strategy(
    crop: str,
    district: str,
    holding_days: int = 30,
    quantity_quintals: Optional[float] = None,
    state: Optional[str] = None
) -> Dict[str, Any]:
    """Decides HOLD / SELL_NOW / NEUTRAL / NO_FORECAST for storing a crop for holding_days."""
    holding_days = max(7, min(int(holding_days or 30), 180))
    data = build_price_series(crop, district, state)
    series, norm_crop = data["series"], data["crop"]
    msp_info = lookup_msp(norm_crop)
    crop_hi = (msp_info or {}).get("name_hi") or HINDI_CROP_NAMES.get(norm_crop, norm_crop)

    if not series:
        return {
            "status": "not_found", "crop": norm_crop, "district": district, "decision": "NO_FORECAST",
            "companion_summary_hi": f"किसान भाई, {district} में {crop_hi} के भाव का रिकॉर्ड नहीं मिला, इसलिए रोककर रखने की सलाह नहीं दे सकता।"
        }

    latest_date, latest_price = series[-1]
    data_age_days = (datetime.now() - latest_date).days
    span_days = (series[-1][0] - series[0][0]).days
    cost = holding_cost_per_qtl(latest_price, holding_days)
    breakeven = cost["total"]

    result: Dict[str, Any] = {
        "status": "success",
        "crop": norm_crop,
        "district": district,
        "price_scope": f"{data['scope']} ({data['scope_level']})",
        "latest_price": latest_price,
        "latest_date": latest_date.strftime("%d/%m/%Y"),
        "reporting_date": latest_date.strftime("%d/%m/%Y"),
        "is_today": data_age_days == 0,
        "data_points": len(series),
        "history_span_days": span_days,
        "data_age_days": data_age_days,
        "holding_days": holding_days,
        "holding_cost_per_qtl": cost,
        "breakeven_rise_per_qtl": breakeven,
        "assumptions": "Rent ₹6/qtl/month, handling ₹10/qtl, loss 0.5%/month, interest 7%/year (approximate).",
    }
    if msp_info:
        result["msp"] = msp_info["msp"]
        result["below_msp"] = latest_price < msp_info["msp"]

    # Guard rails: perishable crops and thin data never get a forecast-based HOLD
    if norm_crop.lower() in PERISHABLE_CROPS:
        result["decision"] = "NO_FORECAST"
        result["confidence"] = "n/a"
        result["companion_summary_hi"] = (
            f"किसान भाई, {crop_hi} जल्दी खराब होने वाली फसल है, इसे साधारण गोदाम में रोकना जोखिम भरा है। "
            f"कोल्ड स्टोरेज का खर्च अलग होता है, इसलिए उसकी दर पता करके ही रोकने का फैसला करें।"
        )
        return result
    if len(series) < MIN_POINTS or span_days < MIN_SPAN_DAYS:
        result["decision"] = "NO_FORECAST"
        result["confidence"] = "low"
        result["companion_summary_hi"] = (
            f"किसान भाई, {data['scope']} में {crop_hi} के भाव का रिकॉर्ड बहुत कम है, इसलिए भाव का अनुमान नहीं लगा सकता। "
            f"{holding_days} दिन रोकने का खर्च लगभग ₹{breakeven:.0f} प्रति क्विंटल आएगा, यानी भाव इतना बढ़े तभी रोकना फायदेमंद है।"
        )
        return result

    trend = theil_sen(series)
    horizon = min(holding_days, span_days)  # Never extrapolate further than the history we have
    expected_gain = trend["slope"] * horizon
    pessimistic_gain = trend["slope_low"] * horizon
    expected_net = expected_gain - breakeven
    pessimistic_net = pessimistic_gain - breakeven

    if len(series) >= 10 and span_days >= 21 and trend["agreement"] >= 0.7 and data_age_days <= STALE_AFTER_DAYS:
        confidence = "high"
    elif trend["agreement"] >= 0.6 and data_age_days <= STALE_AFTER_DAYS * 3:
        confidence = "medium"
    else:
        confidence = "low"

    if pessimistic_net > HOLD_MARGIN_PER_QTL and confidence != "low":
        decision = "HOLD"
    elif expected_net < 0:
        decision = "SELL_NOW"
    else:
        decision = "NEUTRAL"

    result.update({
        "decision": decision,
        "confidence": confidence,
        "trend_per_day": round(trend["slope"], 1),
        "trend_agreement": round(trend["agreement"], 2),
        "projection_days": horizon,
        "expected_change_per_qtl": round(expected_gain),
        "pessimistic_change_per_qtl": round(pessimistic_gain),
        "expected_net_per_qtl": round(expected_net),
    })
    if quantity_quintals:
        result["quantity_quintals"] = quantity_quintals
        result["expected_net_total"] = round(expected_net * quantity_quintals)

    direction = "लगभग स्थिर" if abs(trend["slope"]) < 1 else ("बढ़ रहा" if trend["slope"] > 0 else "घट रहा")
    date_note = f" (भाव {result['latest_date']} तक के रिकॉर्ड पर आधारित)" if data_age_days > STALE_AFTER_DAYS else ""
    total_note = f", {quantity_quintals:.0f} क्विंटल पर लगभग ₹{expected_net * quantity_quintals:,.0f}" if quantity_quintals else ""
    if decision == "HOLD":
        spoken = (
            f"किसान भाई, {data['scope']} में {crop_hi} का भाव रोज़ लगभग ₹{abs(trend['slope']):.0f} {direction} है{date_note}। "
            f"{holding_days} दिन रोकने का खर्च लगभग ₹{breakeven:.0f} प्रति क्विंटल है, और यही रुझान रहा तो खर्च काटकर लगभग ₹{expected_net:.0f} प्रति क्विंटल{total_note} ज़्यादा मिल सकता है, पर यह पक्का नहीं है।"
        )
    elif decision == "SELL_NOW" and trend["slope"] < 0:
        spoken = (
            f"किसान भाई, {data['scope']} में {crop_hi} का भाव रोज़ लगभग ₹{abs(trend['slope']):.0f} घट रहा है{date_note}। "
            f"रोकने पर भाव और गिर सकता है और {holding_days} दिन का खर्च भी लगभग ₹{breakeven:.0f} प्रति क्विंटल लगेगा, इसलिए अभी बेचना बेहतर रहेगा।"
        )
    elif decision == "SELL_NOW":
        spoken = (
            f"किसान भाई, {data['scope']} में {crop_hi} का भाव {direction} है{date_note}। "
            f"{holding_days} दिन रोकने का खर्च लगभग ₹{breakeven:.0f} प्रति क्विंटल है, जो अनुमानित बढ़त से ज़्यादा है, इसलिए अभी बेचना बेहतर रहेगा।"
        )
    else:
        spoken = (
            f"किसान भाई, {data['scope']} में {crop_hi} के भाव का रुझान साफ़ नहीं है{date_note}। "
            f"{holding_days} दिन रोकने का खर्च लगभग ₹{breakeven:.0f} प्रति क्विंटल है, भाव इससे ज़्यादा बढ़ने की पक्की उम्मीद नहीं, इसलिए पैसों की ज़रूरत हो तो अभी बेच दें।"
        )
    if result.get("below_msp"):
        spoken += f" अभी का भाव MSP ₹{msp_info['msp']} से कम है, सरकारी खरीद केंद्र पर बेचना भी एक विकल्प है।"
    result["companion_summary_hi"] = spoken
    return result


def run_economic_specialist(
    crop: str,
    district: str,
    holding_days: int = 30,
    quantity_quintals: Optional[float] = None,
    state: Optional[str] = None
) -> Dict[str, Any]:
    """Entry point for the hold-or-sell advisor."""
    logger.info(f"[*] Hold-or-sell advisor: crop={crop}, district={district}, days={holding_days}")
    return evaluate_holding_strategy(
        crop=crop, district=district, holding_days=holding_days,
        quantity_quintals=quantity_quintals, state=state
    )
