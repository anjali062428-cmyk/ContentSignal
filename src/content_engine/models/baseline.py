"""
Transparent Deterministic Baseline Model.
Calculates a transparent, rule-based baseline refresh priority score
using observable search, freshness, position, and content depth metrics.
"""
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)


def compute_baseline_score(df: pd.DataFrame) -> pd.Series:
    """
    Computes transparent baseline score [0, 1] using:
    - Visibility (log impressions / 90d activity)
    - Freshness risk (days since update)
    - Position opportunity (ranking near striking distance 4-20)
    - Depth gap (thin visible page)
    """
    # 1. Visibility Component [0, 1]
    imp = df["impressions_90d"].fillna(0).values
    visibility = np.clip(np.log1p(imp) / np.log1p(100000.0), 0.0, 1.0)

    # 2. Freshness Risk [0, 1]
    days_update = df["days_since_last_update"].fillna(0).values
    freshness = np.clip(days_update / 365.0, 0.0, 1.0)

    # 3. Position Opportunity [0, 1]
    # Striking distance positions (4 - 20) offer the highest refresh ROI
    pos = df["avg_position"].fillna(0).values
    pos_opp = np.where((pos >= 4.0) & (pos <= 20.0), 1.0, 
              np.where((pos > 20.0) & (pos <= 50.0), 0.5, 0.2))

    # 4. Depth Gap [0, 1]
    wc = df["word_count"].fillna(0).values
    depth_gap = np.where((wc > 0) & (wc < 1200) & (imp >= 250), 1.0, 0.0)

    # Weighted transparent score
    raw_score = (
        0.40 * visibility +
        0.30 * freshness +
        0.20 * pos_opp +
        0.10 * depth_gap
    )
    return pd.Series(raw_score, index=df.index)


def evaluate_ranking(
    y_true: np.ndarray,
    y_scores: np.ndarray,
) -> Dict[str, Any]:
    """Calculates ROC-AUC, PR-AUC, binary metrics, and Precision@K."""
    roc_auc = float(roc_auc_score(y_true, y_scores))
    pr_auc = float(average_precision_score(y_true, y_scores))

    # Binary threshold at 0.5
    y_pred = (y_scores >= 0.5).astype(int)
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    cm = confusion_matrix(y_true, y_pred).tolist()

    # Precision@K for ranked editorial queues
    order = np.argsort(y_scores)[::-1]
    sorted_y = y_true[order]

    def precision_at_k(k: int) -> float:
        top_k = sorted_y[:k]
        return float(np.mean(top_k)) if len(top_k) > 0 else 0.0

    return {
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "confusion_matrix": cm,
        "precision_at_20": round(precision_at_k(20), 4),
        "precision_at_50": round(precision_at_k(50), 4),
        "precision_at_100": round(precision_at_k(100), 4),
    }
