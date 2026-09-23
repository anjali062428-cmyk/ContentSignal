"""
Deterministic Reason Engine for Content Intelligence.
Evaluates observed metrics and ML probability to generate structured,
explainable reason codes with supporting evidence and confidence scores.
"""
from typing import Dict, Any, List


REASON_DEFINITIONS = {
    "DECLINING_TRAFFIC": {
        "title": "Observed Traffic Decline Risk",
        "description": "High ML probability of search visibility decline alongside notable audience exposure.",
    },
    "HIGH_IMPRESSIONS_LOW_CTR": {
        "title": "High Visibility with Weak Click-Through",
        "description": "Substantial Google impressions but CTR is significantly below average for page ranking position.",
    },
    "CONTENT_STALE": {
        "title": "Stale Content Asset",
        "description": "Content has not been refreshed in over 180 days while retaining consistent search demand.",
    },
    "LOW_ENGAGEMENT": {
        "title": "Sub-optimal On-Page Engagement",
        "description": "Visitors demonstrate low scroll depth or engagement rates below benchmark (<30%).",
    },
    "RANKING_DETERIORATION": {
        "title": "Striking Zone Position Opportunity",
        "description": "Page ranks on Page 1 or 2 (positions 4–20) where targeted updates could yield significant traffic gains.",
    },
    "HIGH_VALUE_DECLINE": {
        "title": "High-Value Asset Under Pressure",
        "description": "Top-tier traffic generator exhibiting high probability of deterioration.",
    },
    "STRONG_MOMENTUM": {
        "title": "Healthy Traffic Driver",
        "description": "Strong recent engagement and visibility with minimal risk of decline.",
    },
    "INSUFFICIENT_EVIDENCE": {
        "title": "Low Search Volume / Thin Data",
        "description": "Insufficient 90-day impressions or sessions to draw high-confidence conclusions.",
    },
}


def evaluate_page_reasons(
    row: Dict[str, Any],
    ml_probability: float,
) -> List[Dict[str, Any]]:
    """
    Evaluates observed metrics, time-window comparison deltas, and ML probability.
    Returns a list of structured reason objects with supporting evidence and change percentages.
    """
    reasons = []
    
    imp = float(row.get("impressions_90d", 0) or 0)
    clicks = float(row.get("clicks_90d", 0) or 0)
    sessions = float(row.get("sessions_90d", 0) or 0)
    ctr = float(row.get("ctr", 0) or 0)
    pos = float(row.get("avg_position", 0) or 0)
    eng_rate = float(row.get("engagement_rate", 0) or 0)
    scroll_rate = float(row.get("scroll_rate", 0) or 0)
    days_update = float(row.get("days_since_last_update", 0) or 0)

    # 30-day comparative metrics
    c_last = float(row.get("clicks_last_30d", 0) or 0)
    c_prev = float(row.get("clicks_prev_30d", 0) or 0)
    i_last = float(row.get("impressions_last_30d", 0) or 0)
    i_prev = float(row.get("impressions_prev_30d", 0) or 0)

    # 1. Check for Insufficient Evidence
    if imp < 50 and sessions < 5:
        reasons.append({
            "code": "INSUFFICIENT_EVIDENCE",
            "reason_code": "INSUFFICIENT_EVIDENCE",
            "title": REASON_DEFINITIONS["INSUFFICIENT_EVIDENCE"]["title"],
            "message": "Page has under 50 impressions and fewer than 5 sessions in 90 days.",
            "explanation": "Insufficient search exposure to draw statistically reliable opportunity conclusions.",
            "metric": "impressions_90d",
            "change_percent": None,
            "supporting_metric": {"impressions_90d": imp, "sessions_90d": sessions},
            "severity": "low",
            "confidence": 0.40,
        })
        return reasons

    # 2. Time-Window Click Decline (if 30d window history is present)
    if c_prev >= 5 and c_last < c_prev:
        c_pct = round(((c_last - c_prev) / c_prev) * 100.0, 1)
        if c_pct <= -20.0:
            reasons.append({
                "code": "CLICK_DECLINE",
                "reason_code": "CLICK_DECLINE",
                "title": "Recent Click Drop",
                "message": f"Clicks dropped {abs(c_pct):.1f}% in the last 30 days ({c_last:,.0f} vs {c_prev:,.0f} previous).",
                "explanation": f"Observed click volume decreased by {abs(c_pct):.1f}% between consecutive 30-day windows.",
                "metric": "clicks",
                "change_percent": c_pct,
                "severity": "critical" if c_pct <= -40.0 else "high",
                "confidence": 0.92,
                "supporting_metric": {"clicks_last_30d": c_last, "clicks_prev_30d": c_prev, "change_percent": c_pct},
            })

    # 3. Time-Window Impression Contraction
    if i_prev >= 100 and i_last < i_prev:
        i_pct = round(((i_last - i_prev) / i_prev) * 100.0, 1)
        if i_pct <= -20.0:
            reasons.append({
                "code": "IMPRESSION_DECLINE",
                "reason_code": "IMPRESSION_DECLINE",
                "title": "Search Visibility Contraction",
                "message": f"Search impressions decreased {abs(i_pct):.1f}% in the last 30 days ({i_last:,.0f} vs {i_prev:,.0f} previous).",
                "explanation": f"Google impressions declined by {abs(i_pct):.1f}% compared with the previous 30 days.",
                "metric": "impressions",
                "change_percent": i_pct,
                "severity": "high",
                "confidence": 0.90,
                "supporting_metric": {"impressions_last_30d": i_last, "impressions_prev_30d": i_prev, "change_percent": i_pct},
            })

    # 4. High Value Decline
    if imp >= 2500 and ml_probability >= 0.65:
        reasons.append({
            "code": "HIGH_VALUE_DECLINE",
            "reason_code": "HIGH_VALUE_DECLINE",
            "title": REASON_DEFINITIONS["HIGH_VALUE_DECLINE"]["title"],
            "message": f"High-traffic asset ({imp:,.0f} impressions) exhibits strong decline probability ({ml_probability:.1%}).",
            "explanation": f"Page is in the top tier of search visibility ({imp:,.0f} impressions) and exhibits strong decline probability ({ml_probability:.1%}).",
            "metric": "impressions_90d",
            "change_percent": None,
            "supporting_metric": {"impressions_90d": imp, "ml_probability": round(ml_probability, 3)},
            "severity": "critical",
            "confidence": round(min(0.95, 0.70 + (ml_probability - 0.5) * 0.5), 2),
        })

    # 5. Observed Traffic Decline Risk
    elif ml_probability >= 0.60 and imp >= 200:
        reasons.append({
            "code": "DECLINING_TRAFFIC",
            "reason_code": "DECLINING_TRAFFIC",
            "title": REASON_DEFINITIONS["DECLINING_TRAFFIC"]["title"],
            "message": f"Model estimated a {ml_probability:.1%} opportunity probability indicating declining audience momentum.",
            "explanation": f"Model estimated a {ml_probability:.1%} opportunity probability indicating declining audience momentum.",
            "metric": "ml_probability",
            "change_percent": None,
            "supporting_metric": {"ml_probability": round(ml_probability, 3), "impressions_90d": imp},
            "severity": "high",
            "confidence": round(min(0.90, 0.65 + (ml_probability - 0.5) * 0.4), 2),
        })

    # 6. High Impressions Low CTR
    if imp >= 300 and 0 < pos <= 20 and ctr < 0.6:
        reasons.append({
            "code": "HIGH_IMPRESSIONS_LOW_CTR",
            "reason_code": "HIGH_IMPRESSIONS_LOW_CTR",
            "title": REASON_DEFINITIONS["HIGH_IMPRESSIONS_LOW_CTR"]["title"],
            "message": f"High search impressions ({imp:,.0f}) with position {pos:.1f}, but CTR is only {ctr:.2f}%.",
            "explanation": f"Page receives strong search impressions ({imp:,.0f}) with position {pos:.1f}, but CTR is only {ctr:.2f}%.",
            "metric": "ctr",
            "change_percent": None,
            "supporting_metric": {"impressions_90d": imp, "avg_position": pos, "ctr": ctr},
            "severity": "high",
            "confidence": 0.88,
        })

    # 7. Content Stale
    if days_update >= 180 and imp >= 200:
        reasons.append({
            "code": "CONTENT_STALE",
            "reason_code": "CONTENT_STALE",
            "title": REASON_DEFINITIONS["CONTENT_STALE"]["title"],
            "message": f"Content was last updated {days_update:.0f} days ago despite active organic search demand.",
            "explanation": f"Page has not been updated in {days_update:.0f} days while receiving ongoing organic search demand.",
            "metric": "days_since_last_update",
            "change_percent": None,
            "supporting_metric": {"days_since_last_update": days_update, "impressions_90d": imp},
            "severity": "medium",
            "confidence": 0.85,
        })

    # 8. Low Engagement
    if sessions >= 25 and (eng_rate < 35 or scroll_rate < 30):
        reasons.append({
            "code": "LOW_ENGAGEMENT",
            "reason_code": "LOW_ENGAGEMENT",
            "title": REASON_DEFINITIONS["LOW_ENGAGEMENT"]["title"],
            "message": f"On-page engagement is weak (Engagement Rate: {eng_rate:.1f}%, Scroll Rate: {scroll_rate:.1f}% across {sessions:,.0f} sessions).",
            "explanation": f"On-page engagement is weak (Engagement Rate: {eng_rate:.1f}%, Scroll Rate: {scroll_rate:.1f}% across {sessions:,.0f} sessions).",
            "metric": "engagement_rate",
            "change_percent": None,
            "supporting_metric": {"sessions_90d": sessions, "engagement_rate": eng_rate, "scroll_rate": scroll_rate},
            "severity": "medium",
            "confidence": 0.80,
        })

    # 9. Striking Zone Position Opportunity
    if 4.0 <= pos <= 15.0 and imp >= 200:
        reasons.append({
            "code": "RANKING_DETERIORATION",
            "reason_code": "RANKING_DETERIORATION",
            "title": REASON_DEFINITIONS["RANKING_DETERIORATION"]["title"],
            "message": f"Striking distance ranking (position {pos:.1f}) where optimization could push into top 3.",
            "explanation": f"Average position is {pos:.1f} (striking zone). Minor optimization could push it into top 3.",
            "metric": "avg_position",
            "change_percent": None,
            "supporting_metric": {"avg_position": pos, "impressions_90d": imp},
            "severity": "medium",
            "confidence": 0.78,
        })

    # 10. Strong Momentum (Protect Candidate)
    if ml_probability < 0.35 and imp >= 1000 and (eng_rate >= 50 or ctr >= 1.5):
        reasons.append({
            "code": "STRONG_MOMENTUM",
            "reason_code": "STRONG_MOMENTUM",
            "title": REASON_DEFINITIONS["STRONG_MOMENTUM"]["title"],
            "message": f"High search volume ({imp:,.0f} impressions) with healthy engagement and low decline probability ({ml_probability:.1%}).",
            "explanation": f"High search volume ({imp:,.0f} impressions) with healthy engagement and low decline probability ({ml_probability:.1%}).",
            "metric": "ml_probability",
            "change_percent": None,
            "supporting_metric": {"impressions_90d": imp, "ml_probability": round(ml_probability, 3)},
            "severity": "low",
            "confidence": 0.85,
        })

    return reasons

