"""
Evidence-Based Action Recommendation Engine.
Maps deterministic reason codes, observable signals, and ML opportunity scores
to clear, actionable editorial directives:
REFRESH, OPTIMIZE, PROTECT, INVESTIGATE, MONITOR, REWRITE, MERGE.
"""
from typing import Dict, Any, List


ACTION_DEFINITIONS = {
    "REFRESH": {
        "title": "Editorial Refresh",
        "directive": "Update outdated facts, refresh statistics, add recent case studies, and expand search coverage.",
    },
    "OPTIMIZE": {
        "title": "SERP / CTR Optimization",
        "directive": "Rewrite title tags, meta description, and schema markup to improve SERP click-through rate.",
    },
    "PROTECT": {
        "title": "Protect & Defend Asset",
        "directive": "Core high-performing asset. Maintain existing URL structure, preserve internal links, and monitor closely.",
    },
    "INVESTIGATE": {
        "title": "Engagement & UX Investigation",
        "directive": "Review reader bounce, page load performance, layout readability, and mobile user experience.",
    },
    "MONITOR": {
        "title": "Passive Monitoring",
        "directive": "Insufficient activity or steady baseline. Observe over subsequent 30-day reporting windows.",
    },
    "REWRITE": {
        "title": "Comprehensive Content Overhaul",
        "directive": "Fundamental mismatch with search intent or outdated structure requiring major re-authoring.",
    },
    "MERGE": {
        "title": "Content Consolidation / Merge",
        "directive": "Consolidate duplicate or cannibalizing content into a stronger authoritative pillar page.",
    },
}


def determine_recommended_action(
    row: Dict[str, Any],
    ml_probability: float,
    opportunity_score: float,
    reason_codes: List[str],
) -> Dict[str, Any]:
    """
    Evaluates reasons and evidence to assign a deterministic recommendation.
    Distinguishes the model output from the business rule action.
    """
    imp = float(row.get("impressions_90d", 0) or 0)
    sessions = float(row.get("sessions_90d", 0) or 0)
    ctr = float(row.get("ctr", 0) or 0)
    days_update = float(row.get("days_since_last_update", 0) or 0)
    wc = float(row.get("word_count", 0) or 0)

    # 1. MONITOR if insufficient evidence or very low volume
    if "INSUFFICIENT_EVIDENCE" in reason_codes or (imp < 100 and sessions < 10):
        action = "MONITOR"
        rationale = "Search volume and session density are too low to justify active editorial intervention. Collect more data before making a refresh decision."

    # 2. OPTIMIZE if High Impressions + Weak CTR
    elif "HIGH_IMPRESSIONS_LOW_CTR" in reason_codes:
        action = "OPTIMIZE"
        rationale = (
            f"Page captures notable search exposure ({imp:,.0f} impressions) with ranking {row.get('avg_position', 0):.1f}, but CTR is only {ctr:.2f}%. "
            "Review title and meta description. Check whether the SERP snippet still matches search intent."
        )

    # 3. REFRESH if Click Drop, High Value Decline, or Stale Content with Decline Risk
    elif "CLICK_DECLINE" in reason_codes or "HIGH_VALUE_DECLINE" in reason_codes or ("CONTENT_STALE" in reason_codes and ml_probability >= 0.50):
        action = "REFRESH"
        rationale = (
            f"High opportunity score ({opportunity_score:.0f}/100) and observed search performance deterioration. "
            "Perform a content refresh and investigate search visibility changes. Update statistics, examples, references, and outdated sections."
        )

    # 4. PROTECT if Strong Momentum with High Visibility
    elif "STRONG_MOMENTUM" in reason_codes or (opportunity_score < 30 and imp >= 1500):
        action = "PROTECT"
        rationale = (
            f"Key traffic driver with healthy momentum and low decline probability ({ml_probability:.1%}). "
            "Maintain current content and continue monitoring. Protect URL structure and internal links."
        )

    # 5. INVESTIGATE if Low Engagement
    elif "LOW_ENGAGEMENT" in reason_codes:
        action = "INVESTIGATE"
        rationale = (
            "Audience arrives but bounce rate is high. Review reader engagement, layout friction, mobile speed, and above-the-fold relevance."
        )

    # 6. REWRITE / MERGE if Thin or Stagnant with High Word Count
    elif wc > 2500 and imp < 150 and days_update > 250:
        action = "MERGE"
        rationale = (
            "Extensive word count with very limited organic search traction. "
            "Consider merging valuable sections into an authoritative pillar article."
        )

    # 7. Default for elevated score
    elif opportunity_score >= 50:
        action = "REFRESH"
        rationale = "Elevated opportunity score across combined observable signals indicates editorial refresh is warranted."
    else:
        action = "MONITOR"
        rationale = "Stable metrics. Maintain current content and continue monitoring."


    return {
        "action": action,
        "title": ACTION_DEFINITIONS[action]["title"],
        "directive": ACTION_DEFINITIONS[action]["directive"],
        "rationale": rationale,
        "is_deterministic_rule": True,
        "model_probability": round(ml_probability, 3),
    }
