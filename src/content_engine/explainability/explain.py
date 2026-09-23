"""
Model Explainability Engine.
Provides local feature contribution explanations for individual pages.
Strictly framed as 'contributed to the model prediction' — NEVER making causal claims.
"""
import joblib
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from content_engine.config import (
    BASE_DIR,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
)

_CACHED_PIPELINE = None


def get_cached_pipeline(model_path: Path = BASE_DIR / "data" / "processed" / "best_model.joblib"):
    global _CACHED_PIPELINE
    if _CACHED_PIPELINE is None:
        _CACHED_PIPELINE = joblib.load(model_path)
    return _CACHED_PIPELINE


def explain_page_prediction(
    row: Dict[str, Any],
    model_path: Path = BASE_DIR / "data" / "processed" / "best_model.joblib",
) -> Dict[str, Any]:
    """
    Computes local feature attributions for a single page.
    Explains which observable signals increased or decreased the model's opportunity estimate.
    """
    pipeline = get_cached_pipeline(model_path)
    classifier = pipeline.named_steps["classifier"]
    preprocessor = pipeline.named_steps["preprocessor"]

    imp = float(row.get("impressions_90d", 0) or 0)
    clicks = float(row.get("clicks_90d", 0) or 0)
    sess = float(row.get("sessions_90d", 0) or 0)
    eng_sess = float(row.get("engaged_sessions_90d", 0) or 0)
    pos = float(row.get("avg_position", 0) or 0)
    search_vol = float(row.get("search_volume", 0) or 0)
    wc = float(row.get("word_count", 0) or 0)

    derived = {
        "log_impressions_90d": float(np.log1p(max(0, imp))),
        "log_clicks_90d": float(np.log1p(max(0, clicks))),
        "log_sessions_90d": float(np.log1p(max(0, sess))),
        "is_missing_position": 1.0 if pos == 0 else 0.0,
        "is_missing_keyword_context": 1.0 if search_vol == 0 else 0.0,
        "is_missing_word_count": 1.0 if wc == 0 else 0.0,
        "engaged_session_ratio": float(min(1.0, max(0.0, eng_sess / max(1.0, sess)))),
        "click_to_session_ratio": float(min(10.0, max(0.0, sess / max(1.0, clicks)))),
    }

    full_row = row.copy()
    full_row.update(derived)

    features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    row_dict = {}
    for col in features:
        if col in NUMERIC_FEATURES:
            val = full_row.get(col, 0.0)
            row_dict[col] = float(val) if val is not None else 0.0
        else:
            val = full_row.get(col, "unknown")
            row_dict[col] = str(val) if val is not None else "unknown"

    df_row = pd.DataFrame([row_dict])
    prob = float(pipeline.predict_proba(df_row)[0, 1])

    X_trans = preprocessor.transform(df_row)
    cat_encoder = preprocessor.named_transformers_["cat"]
    encoded_cat_names = list(cat_encoder.get_feature_names_out(CATEGORICAL_FEATURES))
    all_feature_names = NUMERIC_FEATURES + encoded_cat_names

    contributions = []
    if hasattr(classifier, "feature_importances_"):
        importances = classifier.feature_importances_
        std_scaler = preprocessor.named_transformers_["num"]
        means = std_scaler.mean_
        scales = std_scaler.scale_

        for i, feat_name in enumerate(NUMERIC_FEATURES):
            raw_val = float(row_dict.get(feat_name, 0.0))
            z_score = (raw_val - means[i]) / (scales[i] + 1e-6)
            importance = float(importances[i])
            
            impact = z_score * importance
            direction = "increased" if impact > 0 else "decreased"
            contributions.append({
                "feature": feat_name,
                "value": raw_val,
                "importance": round(importance, 4),
                "impact_score": round(float(impact), 4),
                "direction": direction,
                "explanation": f"{feat_name.replace('_', ' ').title()} ({raw_val:,.1f}) {direction} the model's estimated review priority."
            })
    
    contributions.sort(key=lambda x: abs(x["impact_score"]), reverse=True)
    top_contributions = contributions[:6]

    return {
        "model_probability": round(prob, 3),
        "causal_disclaimer": (
            "NOTICE: Feature attributions indicate which signals contributed to the model's prediction. "
            "They do NOT demonstrate causal impact on search engine performance or traffic recovery."
        ),
        "top_contributions": top_contributions,
    }
