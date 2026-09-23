"""
Master Scoring Engine.
Computes deterministic 0-100 Opportunity Score combining ML probability and observable evidence.
Applies reason codes, assigns evidence-based recommended actions, assigns priority tiers,
and generates data/processed/opportunities.csv.
"""
import joblib
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd

from content_engine.config import (
    FEATURE_VECTOR_PATH,
    OPPORTUNITIES_PATH,
    BASE_DIR,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    PRIORITY_THRESHOLDS,
)
from content_engine.scoring.reason_engine import evaluate_page_reasons
from content_engine.scoring.action_engine import determine_recommended_action


def calculate_opportunity_score(
    ml_prob: float,
    impressions_90d: float,
    days_since_update: float,
    ctr: float,
    avg_position: float,
    engagement_rate: float,
    click_change_pct: float = 0.0,
    impression_change_pct: float = 0.0,
    sessions_90d: float = 20.0,
) -> float:
    """
    Computes deterministic 0–100 Content Opportunity Score:
    - ML opportunity probability (40%)
    - Visibility demand baseline (20%)
    - Time-window decline signal (15%)
    - Freshness decay risk (15%)
    - CTR gap opportunity (5%)
    - Engagement opportunity (5%)
    - Less uncertainty penalty when evidence is insufficient
    """
    # 1. ML Component [0, 1]
    ml_comp = np.clip(ml_prob, 0.0, 1.0)

    # 2. Visibility Component [0, 1] (log scale to bound high-volume outliers)
    vis_comp = np.clip(np.log1p(max(0, impressions_90d)) / np.log1p(50000.0), 0.0, 1.0)

    # 3. Time-window decline signal [0, 1]
    # If clicks or impressions dropped over comparison periods, add decline weight
    decline_score = 0.0
    if click_change_pct < 0:
        decline_score += min(1.0, abs(click_change_pct) / 50.0) * 0.6
    if impression_change_pct < 0:
        decline_score += min(1.0, abs(impression_change_pct) / 50.0) * 0.4
    decline_comp = np.clip(decline_score, 0.0, 1.0)

    # 4. Freshness Risk [0, 1] (scales linearly up to 1 year)
    fresh_comp = np.clip(max(0, days_since_update) / 365.0, 0.0, 1.0)

    # 5. CTR Opportunity [0, 1]
    # If ranking on page 1 or 2 (<= 20) with CTR < 1.0%, opportunity is high
    if 0 < avg_position <= 20:
        ctr_comp = np.clip((1.5 - ctr) / 1.5, 0.0, 1.0)
    else:
        ctr_comp = 0.2

    # 6. Engagement Gap [0, 1]
    eng_comp = np.clip((50.0 - engagement_rate) / 50.0, 0.0, 1.0)

    # When time-window metrics are present, balance with decline signal; else fallback to original weights
    if click_change_pct != 0.0 or impression_change_pct != 0.0:
        raw_score = (
            0.35 * ml_comp +
            0.20 * vis_comp +
            0.15 * decline_comp +
            0.15 * fresh_comp +
            0.10 * ctr_comp +
            0.05 * eng_comp
        )
    else:
        raw_score = (
            0.45 * ml_comp +
            0.25 * vis_comp +
            0.15 * fresh_comp +
            0.10 * ctr_comp +
            0.05 * eng_comp
        )

    # Uncertainty penalty for thin datasets
    uncertainty_penalty = 12.0 if (impressions_90d < 50 and sessions_90d < 5) else 0.0

    score_100 = float(np.clip(raw_score * 100.0 - uncertainty_penalty, 0.0, 100.0))
    return round(score_100, 1)


def get_priority_tier(score: float) -> str:
    """Maps 0-100 score to priority tier."""
    if score >= 81.0:
        return "CRITICAL"
    elif score >= 61.0:
        return "HIGH"
    elif score >= 31.0:
        return "MEDIUM"
    return "LOW"


def get_content_status(
    score: float,
    confidence_tier: str,
    trend_class: str,
    impressions_90d: float,
    sessions_90d: float,
    ctr: float,
    avg_position: float,
) -> str:
    """
    Standard Content Status:
    - REFRESH NOW
    - REVIEW
    - MONITOR
    - STABLE
    - INSUFFICIENT DATA
    """
    if impressions_90d < 50 and sessions_90d < 5:
        return "INSUFFICIENT DATA"
    if score >= 70.0 and confidence_tier in ("HIGH", "MEDIUM") and trend_class in ("accelerating_decline", "persistent_decline"):
        return "REFRESH NOW"
    if score >= 55.0 or (0 < avg_position <= 20 and ctr < 0.8 and impressions_90d >= 300):
        return "REVIEW"
    if score >= 30.0 or trend_class in ("persistent_decline", "temporary_drop"):
        return "MONITOR"
    return "STABLE"


def get_confidence_tier(impressions_90d: float, sessions_90d: float) -> str:
    """Confidence tier based on observation volume."""
    if impressions_90d >= 500 and sessions_90d >= 30:
        return "HIGH"
    if impressions_90d >= 100 and sessions_90d >= 10:
        return "MEDIUM"
    return "LOW"


def score_entire_catalog(
    feature_csv: Path = FEATURE_VECTOR_PATH,
    model_path: Path = BASE_DIR / "data" / "processed" / "best_model.joblib",
    output_csv: Path = OPPORTUNITIES_PATH,
) -> pd.DataFrame:
    """
    Generates scored and ranked opportunities catalog for all pages.
    """
    import json
    df = pd.read_csv(feature_csv)
    pipeline = joblib.load(model_path)

    # Predict ML probabilities
    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    X = df[feature_cols]
    ml_probs = pipeline.predict_proba(X)[:, 1]
    df["ml_opportunity_probability"] = np.round(ml_probs, 4)

    # Calculate scores, priorities, reasons, and actions
    scores = []
    priorities = []
    actions = []
    primary_reasons = []
    confidences = []
    content_statuses = []
    confidence_tiers = []
    reasons_jsons = []

    for idx, row in df.iterrows():
        prob = float(row["ml_opportunity_probability"])
        imp = float(row.get("impressions_90d", 0))
        sessions_val = float(row.get("sessions_90d", 0))
        update_days = float(row.get("days_since_last_update", 0))
        ctr_val = float(row.get("ctr", 0))
        pos_val = float(row.get("avg_position", 0))
        eng_val = float(row.get("engagement_rate", 0))

        c_last = float(row.get("clicks_last_30d", 0) or 0)
        c_prev = float(row.get("clicks_prev_30d", 0) or 0)
        i_last = float(row.get("impressions_last_30d", 0) or 0)
        i_prev = float(row.get("impressions_prev_30d", 0) or 0)

        c_change = round(((c_last - c_prev) / max(1.0, c_prev)) * 100.0, 1) if c_prev > 0 else 0.0
        i_change = round(((i_last - i_prev) / max(1.0, i_prev)) * 100.0, 1) if i_prev > 0 else 0.0

        score = calculate_opportunity_score(
            prob, imp, update_days, ctr_val, pos_val, eng_val,
            click_change_pct=c_change, impression_change_pct=i_change, sessions_90d=sessions_val
        )
        priority = get_priority_tier(score)
        
        reasons = evaluate_page_reasons(row.to_dict(), prob)
        reason_codes = [r["code"] for r in reasons]
        primary_reason = reasons[0]["title"] if reasons else "Routine Operational Monitoring"
        confidence = reasons[0]["confidence"] if reasons else 0.70

        action_dict = determine_recommended_action(row.to_dict(), prob, score, reason_codes)

        conf_tier = get_confidence_tier(imp, sessions_val)
        trend_class = "persistent_decline" if (c_change <= -20 or i_change <= -20) else "stable"
        status_val = get_content_status(score, conf_tier, trend_class, imp, sessions_val, ctr_val, pos_val)

        scores.append(score)
        priorities.append(priority)
        actions.append(action_dict["action"])
        primary_reasons.append(primary_reason)
        confidences.append(confidence)
        content_statuses.append(status_val)
        confidence_tiers.append(conf_tier)
        reasons_jsons.append(json.dumps(reasons))

    df["opportunity_score"] = scores
    df["priority"] = priorities
    df["action"] = actions
    df["primary_reason"] = primary_reasons
    df["confidence"] = confidences
    df["content_status"] = content_statuses
    df["confidence_tier"] = confidence_tiers
    df["reasons_json"] = reasons_jsons

    # Sort descending by opportunity score for ranked editorial review queue
    df = df.sort_values(by="opportunity_score", ascending=False).reset_index(drop=True)
    df["queue_rank"] = np.arange(1, len(df) + 1)

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_csv, index=False)
    print(f"Scored {len(df):,} pages. Saved opportunities catalog to {output_csv}")
    return df


if __name__ == "__main__":
    score_entire_catalog()
