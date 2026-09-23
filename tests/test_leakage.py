"""
Unit tests for leakage prevention and audit verification.
"""
import pytest
from content_engine.config import (
    RESTRICTED_FLYRANK_COLUMNS,
    FORBIDDEN_LEAKAGE_COLUMNS,
    IDENTIFIER_COLUMNS,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
)
from content_engine.features.leakage_audit import (
    audit_feature_names,
    SecurityLeakageError,
)


def test_clean_features_pass_audit():
    clean_features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    audit = audit_feature_names(clean_features)
    assert audit["audit_passed"] is True
    assert audit["total_features_evaluated"] == len(clean_features)


def test_leakage_audit_fails_on_restricted_columns():
    for restricted in RESTRICTED_FLYRANK_COLUMNS:
        with pytest.raises(SecurityLeakageError, match="Proprietary FlyRank decision columns found"):
            audit_feature_names(["impressions_90d", restricted])


def test_leakage_audit_fails_on_target_construction():
    for forbidden in FORBIDDEN_LEAKAGE_COLUMNS:
        with pytest.raises(SecurityLeakageError):
            audit_feature_names(["impressions_90d", forbidden])


def test_leakage_audit_fails_on_identifiers():
    for id_col in IDENTIFIER_COLUMNS:
        with pytest.raises(SecurityLeakageError, match="Identifier columns found"):
            audit_feature_names(["impressions_90d", id_col])


def test_leakage_audit_fails_on_subtoken():
    with pytest.raises(SecurityLeakageError, match="Forbidden target-construction token detected"):
        audit_feature_names(["impressions_90d", "derived_last_30d_metric"])
