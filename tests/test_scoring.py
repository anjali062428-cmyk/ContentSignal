"""
Unit tests for Opportunity Scoring, Reason Engine, Action Engine, and Explainability.
"""
import pytest
import pandas as pd
import numpy as np

from content_engine.config import OPPORTUNITIES_PATH
from content_engine.scoring.engine import (
    calculate_opportunity_score,
    get_priority_tier,
)
from content_engine.scoring.reason_engine import evaluate_page_reasons
from content_engine.scoring.action_engine import determine_recommended_action
from content_engine.explainability.explain import explain_page_prediction


def test_opportunity_score_bounds():
    # Extreme cases
    score_low = calculate_opportunity_score(0.0, 0, 0, 5.0, 50.0, 80.0)
    assert 0.0 <= score_low <= 30.0
    assert get_priority_tier(score_low) == "LOW"

    score_high = calculate_opportunity_score(0.95, 10000, 365, 0.2, 5.0, 10.0)
    assert 70.0 <= score_high <= 100.0
    assert get_priority_tier(score_high) in ["HIGH", "CRITICAL"]


def test_reason_engine_logic():
    # Stale page with high impressions
    row = {
        "impressions_90d": 1500,
        "days_since_last_update": 200,
        "ctr": 0.4,
        "avg_position": 8.0,
        "engagement_rate": 20.0,
        "scroll_rate": 25.0,
        "sessions_90d": 50,
    }
    reasons = evaluate_page_reasons(row, ml_probability=0.75)
    codes = [r["code"] for r in reasons]
    
    assert "CONTENT_STALE" in codes
    assert "HIGH_IMPRESSIONS_LOW_CTR" in codes
    assert "LOW_ENGAGEMENT" in codes


def test_action_engine_mapping():
    row = {"impressions_90d": 1200, "ctr": 0.3, "avg_position": 5.0}
    action_info = determine_recommended_action(
        row, ml_probability=0.5, opportunity_score=65.0, reason_codes=["HIGH_IMPRESSIONS_LOW_CTR"]
    )
    assert action_info["action"] == "OPTIMIZE"
    assert action_info["is_deterministic_rule"] is True


def test_explain_page_prediction():
    df = pd.read_csv(OPPORTUNITIES_PATH, nrows=1)
    row = df.iloc[0].to_dict()
    exp = explain_page_prediction(row)

    assert "model_probability" in exp
    assert "top_contributions" in exp
    assert len(exp["top_contributions"]) > 0
    assert "causal_disclaimer" in exp
