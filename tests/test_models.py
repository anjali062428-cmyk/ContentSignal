"""
Unit tests for model training, evaluation, and pipeline inference.
"""
import pytest
import joblib
import json
import numpy as np
import pandas as pd
from pathlib import Path

from content_engine.config import (
    FEATURE_VECTOR_PATH,
    REPORTS_DIR,
    BASE_DIR,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
)


def test_model_report_validity():
    report_json_path = REPORTS_DIR / "model_report.json"
    report_md_path = REPORTS_DIR / "model_report.md"

    assert report_json_path.exists(), "model_report.json must exist"
    assert report_md_path.exists(), "model_report.md must exist"

    with open(report_json_path, "r", encoding="utf-8") as f:
        rep = json.load(f)

    assert "metrics" in rep
    assert "gradient_boosting" in rep["metrics"]
    assert "transparent_baseline" in rep["metrics"]
    assert rep["leakage_audit_summary"]["passed"] is True

    # Check precision@k values are bounded
    for m_name in ["transparent_baseline", "logistic_regression", "random_forest", "gradient_boosting"]:
        p50 = rep["metrics"][m_name]["precision_at_50"]
        assert 0.0 <= p50 <= 1.0, f"Precision@50 for {m_name} must be in [0, 1]"


def test_saved_model_inference():
    model_path = BASE_DIR / "data" / "processed" / "best_model.joblib"
    assert model_path.exists(), "best_model.joblib must exist"

    pipeline = joblib.load(model_path)
    df = pd.read_csv(FEATURE_VECTOR_PATH, nrows=10)
    
    features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    X_sample = df[features]

    probs = pipeline.predict_proba(X_sample)
    assert probs.shape == (10, 2)
    assert np.all((probs >= 0.0) & (probs <= 1.0))
    # Sum of probabilities is 1.0
    assert np.allclose(probs.sum(axis=1), 1.0)
