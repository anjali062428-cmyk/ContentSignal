"""
Canonical Column Mapping Engine.
Maps source dataset columns to standard canonical slots with confidence scores:
>= 0.85: Auto-mapped (High confidence)
0.60 - 0.84: Mapped with notice (Medium confidence)
< 0.60: Needs Review (Low confidence)
"""
import re
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from content_engine.canonical.schema import CANONICAL_SLOTS


CANONICAL_SYNONYMS = {
    "canonical_record_id": [
        "content_id", "page_id", "post_id", "id", "article_id", "link", "url", "unnamed: 0"
    ],
    "canonical_title": [
        "title", "headline", "caption", "title_clean", "post_title", "page_title"
    ],
    "canonical_content_type": [
        "content_type", "type", "category", "data_channel", "page_type", "format"
    ],
    "canonical_date": [
        "date", "timestamp", "published_at", "publish_date", "post_date", "date_posted", "created_at"
    ],
    "canonical_visibility": [
        "impressions_90d", "lifetime post total impressions", "lifetime post total reach",
        "reach", "impressions", "views", "pageviews", "sessions", "traffic", "visits"
    ],
    "canonical_engagement": [
        "total interactions", "total_interactions", "claps", "likes", "like", "comments", "comment",
        "shares", "share", "engaged_sessions_90d", "engagement_rate", "scroll_events_90d",
        "responses", "lifetime engaged users"
    ],
    "canonical_conversion": [
        "revenue", "conversions", "paid", "pagevalues", "leads", "transactions"
    ],
    "canonical_search_visibility": [
        "clicks_90d", "clicks", "search_volume", "domain_authority", "backlinks", "kw_avg_avg"
    ],
    "canonical_position": [
        "avg_position", "position", "serp_position", "serp_position_before", "rank", "ranking"
    ],
    "canonical_ctr": [
        "ctr", "click_through_rate", "clickthroughrate"
    ],
    "canonical_freshness": [
        "days_since_last_update", "days_since_update", "content_age_days", "reading_time", "timedelta"
    ],
    "canonical_text_length": [
        "word_count", "content_length", "char_count", "title_wc", "n_tokens_content"
    ],
    "canonical_outcome": [
        "ranking_improved", "is_declining", "trend_direction", "shares", "total interactions", "claps", "revenue"
    ],
}


def map_columns(
    df: pd.DataFrame,
    explicit_target: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], pd.DataFrame]:
    """
    Identifies column mappings and transforms df into a canonical DataFrame.
    Returns:
        mappings: List of {source_column, canonical_field, method, confidence, datatype}
        df_canonical: DataFrame containing populated canonical columns
    """
    mappings = []
    mapped_sources = set()
    mapped_targets = set()
    columns = [str(c).strip() for c in df.columns]

    df_clean = df.copy()
    df_clean.columns = columns

    # 1. Target mapping priority
    if explicit_target and explicit_target in columns:
        mappings.append({
            "source_column": explicit_target,
            "canonical_field": "canonical_outcome",
            "method": "explicit_target",
            "confidence": 1.0,
            "datatype": str(df_clean[explicit_target].dtype),
        })
        mapped_sources.add(explicit_target)
        mapped_targets.add("canonical_outcome")

    # 2. Iterate canonical slots and find best candidate among source columns
    for slot, synonyms in CANONICAL_SYNONYMS.items():
        if slot in mapped_targets:
            continue

        best_match = None
        best_conf = 0.0
        best_method = ""

        for col in columns:
            if col in mapped_sources:
                continue
            norm_col = col.lower().strip()

            # Exact synonym match
            for syn in synonyms:
                if norm_col == syn:
                    conf = 0.95
                    method = "exact_synonym"
                    if conf > best_conf:
                        best_conf = conf
                        best_match = col
                        best_method = method
                        break
                elif syn in norm_col or norm_col in syn:
                    conf = 0.80
                    method = "partial_synonym"
                    if conf > best_conf:
                        best_conf = conf
                        best_match = col
                        best_method = method

        if best_match and best_conf >= 0.60:
            mappings.append({
                "source_column": best_match,
                "canonical_field": slot,
                "method": best_method,
                "confidence": best_conf,
                "datatype": str(df_clean[best_match].dtype),
            })
            mapped_sources.add(best_match)
            mapped_targets.add(slot)

    # 3. Create canonical DataFrame with standard slots
    canonical_dict = {}
    for slot in CANONICAL_SLOTS:
        canonical_dict[slot] = None

    for m in mappings:
        slot = m["canonical_field"]
        src = m["source_column"]
        canonical_dict[slot] = df_clean[src]

    df_canonical = pd.DataFrame(canonical_dict, index=df_clean.index)

    # If canonical_record_id was not mapped, use index
    if df_canonical["canonical_record_id"].isnull().all():
        df_canonical["canonical_record_id"] = [f"rec_{i+1}" for i in range(len(df_clean))]
        mappings.append({
            "source_column": "_implicit_index_",
            "canonical_field": "canonical_record_id",
            "method": "index_fallback",
            "confidence": 0.70,
            "datatype": "string",
        })

    return mappings, df_canonical


def map_dataframe_to_canonical(
    df: pd.DataFrame,
    explicit_target: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], pd.DataFrame]:
    return map_columns(df, explicit_target=explicit_target)


def map_columns_to_canonical(
    profile_or_df: Any,
    capabilities: Optional[Dict[str, Any]] = None,
    explicit_target: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Helper alias returning list of column mappings from a DataFrame or profile dictionary."""
    if isinstance(profile_or_df, pd.DataFrame):
        mappings, _ = map_columns(profile_or_df, explicit_target=explicit_target)
        return mappings
    elif isinstance(profile_or_df, dict) and "columns" in profile_or_df:
        cols = list(profile_or_df["columns"].keys()) if isinstance(profile_or_df["columns"], dict) else list(profile_or_df["columns"])
        dummy_df = pd.DataFrame(columns=cols)
        mappings, _ = map_columns(dummy_df, explicit_target=explicit_target)
        return mappings
    return []

