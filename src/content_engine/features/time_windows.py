"""
Time-Window Comparative Analysis and Trend Classification.
Calculates meaningful period-over-period deltas:
- Last 30 days vs Previous 30 days
- Click change %, Impression change %, CTR change %, Session change %
- Classifies trends (accelerating_decline, persistent_decline, recovering, stable, growing, temporary_drop)
- Evaluates data sufficiency and confidence ratings (HIGH, MEDIUM, LOW)
- Assigns formal Content Status (REFRESH NOW, REVIEW, MONITOR, STABLE, INSUFFICIENT DATA)
"""
from typing import Dict, Any, Tuple
import math


def calculate_percentage_change(current: float, previous: float) -> float:
    """
    Computes percentage change safely without division by zero.
    Bounded between -100.0% and +500.0% to prevent infinite/extreme outliers.
    """
    if previous <= 0:
        if current > 0:
            return 100.0
        return 0.0
    change = ((current - previous) / previous) * 100.0
    return round(max(-100.0, min(500.0, change)), 1)


def classify_trend(
    click_change_pct: float,
    impression_change_pct: float,
    current_clicks: float,
    current_impressions: float,
) -> str:
    """
    Detects whether performance movement is:
    - accelerating_decline
    - persistent_decline
    - recovering
    - stable
    - growing
    - temporary_drop
    """
    # Insufficient volume to establish persistent direction
    if current_impressions < 30 and current_clicks < 3:
        return "stable"

    # Accelerating decline: heavy drop in both clicks and search demand
    if click_change_pct <= -35.0 and impression_change_pct <= -25.0:
        return "accelerating_decline"

    # Persistent decline: steady downward slide
    if click_change_pct <= -15.0 or impression_change_pct <= -20.0:
        return "persistent_decline"

    # Growing: substantial positive momentum
    if click_change_pct >= 25.0 or impression_change_pct >= 30.0:
        return "growing"

    # Recovering: recent bounce back from previous lows
    if click_change_pct >= 10.0 and impression_change_pct >= 5.0:
        return "recovering"

    # Temporary drop: minor click dip while impressions are stable
    if click_change_pct < -5.0 and impression_change_pct >= -5.0:
        return "temporary_drop"

    return "stable"


def evaluate_confidence(
    impressions_90d: float,
    sessions_90d: float,
    days_with_impressions: float = 0,
    has_comparison_data: bool = True,
) -> str:
    """
    Evaluates confidence: HIGH, MEDIUM, LOW.
    Depends on sample volume, observation frequency, and presence of comparative history.
    """
    if not has_comparison_data or impressions_90d < 100 or sessions_90d < 10:
        return "LOW"
    if impressions_90d >= 500 and sessions_90d >= 30:
        return "HIGH"
    return "MEDIUM"


def determine_content_status(
    opportunity_score: float,
    confidence: str,
    trend_classification: str,
    impressions_90d: float,
    sessions_90d: float,
    ctr: float,
    avg_position: float,
) -> str:
    """
    Determines Content Status from:
    - REFRESH NOW: Strong evidence of sustained deterioration
    - REVIEW: Evidence exists but requires human editorial evaluation
    - MONITOR: Early/small movement or modest opportunity
    - STABLE: Healthy, growing, or protected baseline
    - INSUFFICIENT DATA: Not enough evidence to draw conclusions
    """
    # 1. Check data sufficiency
    if impressions_90d < 50 and sessions_90d < 5:
        return "INSUFFICIENT DATA"

    # 2. REFRESH NOW: High score, non-low confidence, and active decline
    if opportunity_score >= 70.0 and confidence in ("HIGH", "MEDIUM") and trend_classification in ("accelerating_decline", "persistent_decline"):
        return "REFRESH NOW"

    # 3. REVIEW: Elevated score or prominent CTR opportunity on Page 1/2
    if opportunity_score >= 55.0:
        return "REVIEW"
    if 0 < avg_position <= 20 and ctr < 0.8 and impressions_90d >= 300:
        return "REVIEW"

    # 4. MONITOR: Moderate score or early drift
    if opportunity_score >= 30.0 or trend_classification in ("persistent_decline", "temporary_drop"):
        return "MONITOR"

    # 5. STABLE: Low score, healthy momentum, or recovering
    return "STABLE"


def extract_time_window_features(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts and computes all period-over-period time-window features for a row.
    Works with either explicit 30d columns (from FlyRank) or derives approximations.
    """
    c_last = float(row.get("clicks_last_30d", 0) or 0)
    c_prev = float(row.get("clicks_prev_30d", 0) or 0)
    i_last = float(row.get("impressions_last_30d", 0) or 0)
    i_prev = float(row.get("impressions_prev_30d", 0) or 0)
    s_last = float(row.get("sessions_last_30d", 0) or 0)
    s_prev = float(row.get("sessions_prev_30d", 0) or 0)

    # 90-day totals for baseline
    imp_90 = float(row.get("impressions_90d", 0) or row.get("impressions", 0) or 0)
    clk_90 = float(row.get("clicks_90d", 0) or row.get("clicks", 0) or 0)
    ses_90 = float(row.get("sessions_90d", 0) or row.get("sessions", 0) or 0)
    ctr_total = float(row.get("ctr", 0) or 0)
    pos = float(row.get("avg_position", 0) or 0)

    # If 30d columns are missing, estimate from 90d totals or trend_pct if available
    has_30d = (i_last > 0 or i_prev > 0 or c_last > 0 or c_prev > 0)
    if not has_30d and imp_90 > 0:
        trend_val = float(row.get("trend_pct", 0) or 0)
        # Allocate roughly 1/3 to last 30d modified by trend_pct
        i_last = round(max(0.0, (imp_90 / 3.0) * (1.0 + trend_val / 200.0)), 1)
        i_prev = round(max(0.0, (imp_90 / 3.0) * (1.0 - trend_val / 200.0)), 1)
        c_last = round(max(0.0, (clk_90 / 3.0) * (1.0 + trend_val / 200.0)), 1)
        c_prev = round(max(0.0, (clk_90 / 3.0) * (1.0 - trend_val / 200.0)), 1)
        s_last = round(max(0.0, (ses_90 / 3.0) * (1.0 + trend_val / 200.0)), 1)
        s_prev = round(max(0.0, (ses_90 / 3.0) * (1.0 - trend_val / 200.0)), 1)

    click_delta = calculate_percentage_change(c_last, c_prev)
    imp_delta = calculate_percentage_change(i_last, i_prev)
    ses_delta = calculate_percentage_change(s_last, s_prev)

    ctr_last = round((c_last / max(1.0, i_last)) * 100.0, 2)
    ctr_prev = round((c_prev / max(1.0, i_prev)) * 100.0, 2)
    ctr_delta = round(ctr_last - ctr_prev, 2)

    trend_class = classify_trend(click_delta, imp_delta, c_last, i_last)
    conf = evaluate_confidence(imp_90, ses_90, float(row.get("days_with_impressions", 0) or 0), has_comparison_data=True)

    return {
        "clicks_last_30d": c_last,
        "clicks_prev_30d": c_prev,
        "clicks_change_pct": click_delta,
        "impressions_last_30d": i_last,
        "impressions_prev_30d": i_prev,
        "impressions_change_pct": imp_delta,
        "sessions_last_30d": s_last,
        "sessions_prev_30d": s_prev,
        "sessions_change_pct": ses_delta,
        "ctr_last_30d": ctr_last,
        "ctr_prev_30d": ctr_prev,
        "ctr_change_pct": ctr_delta,
        "trend_classification": trend_class,
        "confidence_tier": conf,
    }
