"""
Feature Engineering Pipeline for Content Intelligence Engine.
Builds leakage-safe numeric and categorical features, handles missingness,
calculates robust ratios and log transforms, and constructs target labels.
"""
from pathlib import Path
from typing import Tuple, List, Dict, Any
import numpy as np
import pandas as pd

from content_engine.config import (
    CLEAN_DATA_PATH,
    FEATURE_VECTOR_PATH,
    TARGET_COLUMN,
    IDENTIFIER_COLUMNS,
    FORBIDDEN_LEAKAGE_COLUMNS,
    METADATA_EXCLUDED_COLUMNS,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
)


def transform_dataframe_to_features(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms clean 44-column DataFrame into modeling feature vector.
    Adds safe derived features, handles missingness, and attaches target label.
    """
    df = df_input.copy()

    # 1. Construct Starter Proxy Target (if trend_direction is available)
    if "trend_direction" in df.columns:
        df[TARGET_COLUMN] = (df["trend_direction"] == "down").astype(int)
    else:
        df[TARGET_COLUMN] = 0

    # 2. Missingness Indicators
    df["is_missing_position"] = (df["avg_position"] == 0).astype(int)
    df["is_missing_keyword_context"] = (
        df["search_volume"].isnull() | (df["search_volume"] == 0)
    ).astype(int)
    df["is_missing_word_count"] = (
        df["word_count"].isnull() | (df["word_count"] == 0)
    ).astype(int)

    # 3. Log Transforms for Heavy-Tailed Visibility and Traffic
    df["log_impressions_90d"] = np.log1p(np.clip(df["impressions_90d"].fillna(0), 0, None))
    df["log_clicks_90d"] = np.log1p(np.clip(df["clicks_90d"].fillna(0), 0, None))
    df["log_sessions_90d"] = np.log1p(np.clip(df["sessions_90d"].fillna(0), 0, None))

    # 4. Safe Efficiency Ratios (preventing division by zero)
    sessions_safe = np.maximum(df["sessions_90d"].fillna(0).values, 1.0)
    engaged_safe = np.clip(df["engaged_sessions_90d"].fillna(0).values, 0, None)
    df["engaged_session_ratio"] = np.clip(engaged_safe / sessions_safe, 0.0, 1.0)

    clicks_safe = np.maximum(df["clicks_90d"].fillna(0).values, 1.0)
    df["click_to_session_ratio"] = np.clip(sessions_safe / clicks_safe, 0.0, 10.0)

    # 5. Clean / Impute Features
    for col in NUMERIC_FEATURES:
        if col in df.columns:
            df[col] = df[col].replace([np.inf, -np.inf], np.nan)
            if col == "avg_position":
                pos_median = df.loc[df["avg_position"] > 0, "avg_position"].median()
                if pd.isna(pos_median) or pos_median == 0:
                    pos_median = 28.0
                df.loc[df["avg_position"] == 0, "avg_position"] = pos_median
            else:
                df[col] = df[col].fillna(0.0)

    for col in CATEGORICAL_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna("unknown").astype(str)

    return df


def build_feature_vector(
    clean_csv_path: Path = CLEAN_DATA_PATH,
    output_path: Path = FEATURE_VECTOR_PATH,
) -> pd.DataFrame:
    """
    Reads clean CSV, builds feature vector, saves to disk, and returns DataFrame.
    """
    df_clean = pd.read_csv(clean_csv_path)
    df = transform_dataframe_to_features(df_clean)

    # Ensure output directory exists and save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def get_feature_and_target_columns() -> Tuple[List[str], List[str], str]:
    """Returns valid numeric features, categorical features, and target column."""
    return NUMERIC_FEATURES.copy(), CATEGORICAL_FEATURES.copy(), TARGET_COLUMN


if __name__ == "__main__":
    print("Building feature vector...")
    df_feat = build_feature_vector()
    print(f"Feature vector created with shape: {df_feat.shape}")
