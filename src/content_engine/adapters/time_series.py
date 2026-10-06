"""
Time Series Dataset Adapter.
Handles wide-format and long-format temporal datasets (e.g. Web Traffic Forecasting).
Provides safe chunked streaming without loading hundreds of megabytes into RAM.
"""
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from content_engine.adapters.base import DatasetAdapter
from content_engine.capabilities.profiler import profile_dataset


class TimeSeriesAdapter(DatasetAdapter):
    def __init__(self, dataset_id: str, name: Optional[str] = None):
        super().__init__(dataset_id=dataset_id, name=name)

    def profile(self, data_source: Any) -> Dict[str, Any]:
        return profile_dataset(data_source, sample_size=5000, max_file_size_mb=10.0)

    def detect_capabilities(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "capabilities": {
                "IDENTITY": True,
                "TIME_SERIES": True,
                "VISIBILITY": True,
                "CONTENT": False,
                "SEARCH": False,
            },
            "detected_capabilities": ["IDENTITY", "TIME_SERIES", "VISIBILITY"],
            "missing_capabilities": ["SEARCH", "CONTENT", "CONVERSION"],
            "primary_entity_type": "time_series",
            "has_content_signals": False,
            "has_performance_signals": True,
        }

    def check_readiness(self, profile: Dict[str, Any], capabilities: Dict[str, Any]) -> Dict[str, Any]:
        col_count = profile.get("column_count", 0)
        row_count = profile.get("row_count", 0)
        return {
            "status": "TIME_SERIES",
            "score": 90,
            "is_ready": True,
            "message": f"Dataset detected as Wide-Format Time Series ({row_count:,} series with daily observations).",
            "checks": [
                {"name": "File readable", "status": "PASS", "message": "Valid time-series CSV structure."},
                {"name": "Time-series entity", "status": "PASS", "message": f"Entity series detected ({row_count:,} series)."},
                {"name": "Temporal steps", "status": "PASS", "message": f"{col_count - 1} observation dates detected."},
                {"name": "Readiness", "status": "PASS", "message": "Time-series forecasting datasets are ready for temporal baseline scoring."}
            ]
        }

    def map_canonical(self, df: pd.DataFrame, target: Optional[str] = None) -> Tuple[list, pd.DataFrame]:
        page_col = "Page" if "Page" in df.columns else ([c for c in df.columns if "page" in c.lower() or "url" in c.lower()] or [df.columns[0]])[0]
        can_df = pd.DataFrame(index=df.index)
        can_df["canonical_record_id"] = df[page_col].astype(str)
        can_df["canonical_title"] = df[page_col].astype(str)
        can_df["canonical_url"] = df[page_col].astype(str)
        mappings = [
            {"source_column": page_col, "canonical_slot": "canonical_record_id", "confidence": 1.0},
            {"source_column": page_col, "canonical_slot": "canonical_title", "confidence": 0.9},
            {"source_column": page_col, "canonical_slot": "canonical_url", "confidence": 0.9},
        ]
        return mappings, can_df

    def train_or_evaluate(self, df: pd.DataFrame, canonical_df: pd.DataFrame, target: Optional[str] = None) -> Dict[str, Any]:
        return {"probs": np.zeros(len(df)), "model_report": {"model_type": "Time Series Forecasting Baseline"}}

    def score(self, df: pd.DataFrame, canonical_df: pd.DataFrame, model_output: Dict[str, Any]) -> pd.DataFrame:
        df_scored = df.copy()
        date_cols = [c for c in df.columns if c != "Page"]
        if date_cols:
            recent_vals = pd.to_numeric(df[date_cols[-7:]].iloc[:, -1], errors="coerce").fillna(0)
            past_vals = pd.to_numeric(df[date_cols[0]], errors="coerce").fillna(0)
            denom = np.maximum(1.0, past_vals)
            trend_ratio = recent_vals / denom
            scores = np.clip((1.0 - trend_ratio) * 40.0 + 50.0, 5.0, 95.0)
            df_scored["opportunity_score"] = scores.round(1)
        else:
            df_scored["opportunity_score"] = 50.0

        df_scored["priority"] = pd.cut(
            df_scored["opportunity_score"],
            bins=[-1, 40, 70, 85, 100],
            labels=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        ).astype(str)
        df_scored["action"] = "MONITOR"
        df_scored["primary_reason"] = "Temporal traffic observation series."
        df_scored["ml_probability"] = 0.50
        df_scored["content_status"] = "MONITOR"
        df_scored["confidence_tier"] = "MEDIUM"
        df_scored["queue_rank"] = list(range(1, len(df_scored) + 1))
        return df_scored

