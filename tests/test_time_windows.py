"""
Unit Tests for Time-Window Analysis, Trend Classification, and Content Status.
"""
import pytest
from content_engine.features.time_windows import (
    calculate_percentage_change,
    classify_trend,
    evaluate_confidence,
    determine_content_status,
    extract_time_window_features,
)
from content_engine.scoring.reason_engine import evaluate_page_reasons
from content_engine.scoring.engine import get_content_status, get_confidence_tier, calculate_opportunity_score


def test_percentage_change_safety():
    # Normal case
    assert calculate_percentage_change(50, 100) == -50.0
    assert calculate_percentage_change(120, 100) == 20.0

    # Zero previous handling (prevents division by zero)
    assert calculate_percentage_change(10, 0) == 100.0
    assert calculate_percentage_change(0, 0) == 0.0

    # Bounds clipping
    assert calculate_percentage_change(10000, 1) == 500.0


def test_trend_classification():
    # Accelerating decline
    assert classify_trend(-40.0, -30.0, 10, 500) == "accelerating_decline"

    # Persistent decline
    assert classify_trend(-20.0, -10.0, 20, 1000) == "persistent_decline"

    # Growing
    assert classify_trend(35.0, 15.0, 50, 2000) == "growing"

    # Recovering
    assert classify_trend(12.0, 8.0, 30, 800) == "recovering"

    # Stable (low volume)
    assert classify_trend(-50.0, -50.0, 1, 10) == "stable"


def test_confidence_evaluation():
    assert evaluate_confidence(impressions_90d=1000, sessions_90d=50) == "HIGH"
    assert evaluate_confidence(impressions_90d=250, sessions_90d=15) == "MEDIUM"
    assert evaluate_confidence(impressions_90d=40, sessions_90d=3) == "LOW"
    assert evaluate_confidence(impressions_90d=1000, sessions_90d=50, has_comparison_data=False) == "LOW"


def test_content_status_mapping():
    # REFRESH NOW
    status = determine_content_status(
        opportunity_score=82.0,
        confidence="HIGH",
        trend_classification="accelerating_decline",
        impressions_90d=2000,
        sessions_90d=80,
        ctr=0.8,
        avg_position=6.5,
    )
    assert status == "REFRESH NOW"

    # REVIEW (high visibility + CTR gap)
    status_review = determine_content_status(
        opportunity_score=58.0,
        confidence="HIGH",
        trend_classification="stable",
        impressions_90d=3500,
        sessions_90d=120,
        ctr=0.35,
        avg_position=5.0,
    )
    assert status_review == "REVIEW"

    # MONITOR
    status_monitor = determine_content_status(
        opportunity_score=35.0,
        confidence="MEDIUM",
        trend_classification="persistent_decline",
        impressions_90d=400,
        sessions_90d=20,
        ctr=1.2,
        avg_position=12.0,
    )
    assert status_monitor == "MONITOR"

    # STABLE
    status_stable = determine_content_status(
        opportunity_score=20.0,
        confidence="HIGH",
        trend_classification="growing",
        impressions_90d=5000,
        sessions_90d=300,
        ctr=2.5,
        avg_position=3.0,
    )
    assert status_stable == "STABLE"

    # INSUFFICIENT DATA
    status_insufficient = determine_content_status(
        opportunity_score=60.0,
        confidence="LOW",
        trend_classification="stable",
        impressions_90d=20,
        sessions_90d=2,
        ctr=0.0,
        avg_position=0.0,
    )
    assert status_insufficient == "INSUFFICIENT DATA"


def test_time_window_feature_extraction():
    row = {
        "clicks_last_30d": 15,
        "clicks_prev_30d": 25,
        "impressions_last_30d": 800,
        "impressions_prev_30d": 1200,
        "sessions_last_30d": 12,
        "sessions_prev_30d": 20,
        "impressions_90d": 2500,
        "clicks_90d": 50,
        "sessions_90d": 40,
    }
    feats = extract_time_window_features(row)
    assert feats["clicks_change_pct"] == -40.0
    assert feats["impressions_change_pct"] == -33.3
    assert feats["trend_classification"] == "accelerating_decline"
    assert feats["confidence_tier"] == "HIGH"


def test_structured_reasons_output():
    row = {
        "clicks_last_30d": 10,
        "clicks_prev_30d": 30,
        "impressions_last_30d": 1000,
        "impressions_prev_30d": 1800,
        "impressions_90d": 3000,
        "sessions_90d": 60,
        "ctr": 0.4,
        "avg_position": 8.0,
        "days_since_last_update": 210,
    }
    reasons = evaluate_page_reasons(row, ml_probability=0.72)
    assert len(reasons) > 0
    for r in reasons:
        assert "reason_code" in r
        assert "message" in r
        assert "metric" in r
        assert "severity" in r
        assert "confidence" in r
        assert "supporting_metric" in r

    reason_codes = [r["reason_code"] for r in reasons]
    assert "CLICK_DECLINE" in reason_codes
    assert "IMPRESSION_DECLINE" in reason_codes
