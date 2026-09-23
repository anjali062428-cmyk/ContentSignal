"""
Semantic Capability Detection Module.
Inspects column names, data types, and value patterns to detect semantic capabilities:
IDENTITY, CONTENT, TIME, TIME_SERIES, VISIBILITY, ENGAGEMENT, SEARCH, CONVERSION,
TEXT, METADATA, and OUTCOME.
"""
import re
from typing import Dict, Any, List, Optional, Tuple, Set
import numpy as np
import pandas as pd

# Semantic keywords and regex patterns for capability mapping
CAPABILITY_PATTERNS = {
    "IDENTITY": [
        r"^(content|page|post|article|item|record|seller|user)?_?id$",
        r"^slug$", r"^url$", r"^link$", r"^guid$", r"^key$",
    ],
    "CONTENT": [
        r"^(post_)?type$", r"^(page_)?type$", r"^category$", r"^channel$",
        r"^content_type$", r"^main_intent$", r"^topic$", r"^format$",
        r"^content_length$", r"^word_count$", r"^char_count$",
        r"^n_tokens_.*$", r"^num_.*_links$", r"^has_.*$"
    ],
    "TIME": [
        r"^(publish(ed)?|post(ed)?|record(ed)?)_?(at|date|time)?$",
        r"^date$", r"^timestamp$", r"^post_?(month|weekday|hour|day)$",
        r"^weekday_.*$", r"^is_weekend$", r"^timedelta$",
        r"^days_since_.*$", r"^content_age_.*$", r"^month$"
    ],
    "VISIBILITY": [
        r"^.*impressions.*$", r"^.*reach.*$", r"^.*views.*$",
        r"^.*sessions.*$", r"^.*visits.*$", r"^.*traffic.*$",
        r"^page_?views.*$", r"^pageviews_?90d$"
    ],
    "ENGAGEMENT": [
        r"^.*like(s)?.*$", r"^.*comment(s)?.*$", r"^.*share(s)?.*$",
        r"^.*clap(s)?.*$", r"^.*response(s)?.*$", r"^.*reaction(s)?.*$",
        r"^.*engagement.*$", r"^.*interaction(s)?.*$",
        r"^.*consumer(s)?.*$", r"^.*consumption(s)?.*$",
        r"^.*scroll.*$", r"^.*bounce.*$", r"^.*time_on_page.*$",
        r"^avg_time_on_page_sec$", r"^scroll_depth_percent$", r"^exitrates$"
    ],
    "SEARCH": [
        r"^.*(serp_)?position.*$", r"^.*rank(ing)?.*$",
        r"^.*ctr.*$", r"^.*click(s)?.*$", r"^.*search_volume.*$",
        r"^.*domain_authority.*$", r"^.*page_authority.*$", r"^.*backlink.*$",
        r"^.*competition.*$", r"^.*cpc.*$", r"^kw_.*$"
    ],
    "CONVERSION": [
        r"^.*conversion(s)?.*$", r"^.*revenue.*$", r"^.*paid.*$",
        r"^.*pagevalues.*$", r"^.*transaction(s)?.*$", r"^.*lead(s)?.*$"
    ],
    "TEXT": [
        r"^title$", r"^subtitle$", r"^caption$", r"^body$", r"^text$",
        r"^summary$", r"^description$", r"^title_clean$", r"^headline$"
    ],
    "METADATA": [
        r"^domain$", r"^platform$", r"^author$", r"^publication$",
        r"^region$", r"^browser$", r"^operatingsystem(s)?$", r"^visitortype$"
    ],
    "OUTCOME": [
        r"^ranking_improved$", r"^is_declining$", r"^trend_direction$",
        r"^shares$", r"^total_interactions$", r"^revenue$", r"^claps$"
    ]
}


def _match_pattern(column_name: str, patterns: List[str]) -> bool:
    norm = column_name.strip().lower()
    for pat in patterns:
        if re.search(pat, norm, re.IGNORECASE):
            return True
    return False


def detect_dataset_capabilities(
    columns: List[str],
    dtypes: Optional[Dict[str, str]] = None,
    is_wide_time_series: bool = False,
    profile_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Analyzes columns and types to detect available semantic capabilities.
    Returns:
        capabilities: Dict[str, bool] (flag for each capability)
        capability_columns: Dict[str, List[str]] (matching columns per capability)
        target_candidates: List[Dict[str, Any]] (identified potential targets)
        primary_entity_type: str ("content", "seller", "user", "time_series", "unknown")
    """
    dtypes = dtypes or {}
    matched_columns: Dict[str, List[str]] = {cap: [] for cap in CAPABILITY_PATTERNS}
    matched_columns["TIME_SERIES"] = []

    clean_cols = [str(c).strip() for c in columns]

    # Detect per-column capability matches
    for col in clean_cols:
        norm_col = col.lower()
        for cap, patterns in CAPABILITY_PATTERNS.items():
            if _match_pattern(norm_col, patterns):
                matched_columns[cap].append(col)

    # Time series detection
    if is_wide_time_series:
        matched_columns["TIME_SERIES"].extend(clean_cols[1:])
    elif matched_columns["IDENTITY"] and matched_columns["TIME"] and (matched_columns["VISIBILITY"] or matched_columns["ENGAGEMENT"]):
        # Check if multiple dates per identity could exist
        matched_columns["TIME_SERIES"].extend(matched_columns["TIME"])

    # Boolean flags for available capabilities
    capabilities = {
        cap: len(cols) > 0 for cap, cols in matched_columns.items()
    }
    if is_wide_time_series:
        capabilities["TIME_SERIES"] = True
        capabilities["VISIBILITY"] = True

    # Identify Target Candidates
    target_candidates = []

    # Priority 1: Explicit known outcome columns
    for col in clean_cols:
        norm = col.lower()
        if norm == "ranking_improved":
            target_candidates.append({
                "column": col,
                "type": "binary_classification",
                "confidence": 0.99,
                "description": "Explicit search ranking improvement indicator (0/1)"
            })
        elif norm in ("total interactions", "total_interactions"):
            target_candidates.append({
                "column": col,
                "type": "regression_or_percentile",
                "confidence": 0.95,
                "description": "Total social post interactions sum (likes + comments + shares)"
            })
        elif norm == "shares":
            target_candidates.append({
                "column": col,
                "type": "regression_or_binary",
                "confidence": 0.95,
                "description": "Social/virality share count"
            })
        elif norm == "claps":
            target_candidates.append({
                "column": col,
                "type": "regression_or_percentile",
                "confidence": 0.90,
                "description": "Reader claps/applause outcome"
            })
        elif norm == "revenue":
            target_candidates.append({
                "column": col,
                "type": "binary_classification",
                "confidence": 0.90,
                "description": "E-commerce transaction outcome (True/False)"
            })
        elif norm in ("trend_direction", "is_declining"):
            target_candidates.append({
                "column": col,
                "type": "binary_classification",
                "confidence": 0.85,
                "description": "Audience decay direction flag"
            })

    # Priority 2: In the absence of explicit targets, check for high-engagement continuous signals
    if not target_candidates:
        for col in matched_columns.get("ENGAGEMENT", []):
            dtype = dtypes.get(col, "")
            if dtype in ("int", "float"):
                target_candidates.append({
                    "column": col,
                    "type": "empirical_percentile",
                    "confidence": 0.70,
                    "description": f"Audience engagement metric '{col}' suitable for empirical opportunity ranking"
                })

    # Entity classification (Content vs Seller vs System)
    has_content = bool(capabilities.get("CONTENT") or capabilities.get("TEXT") or capabilities.get("SEARCH"))
    has_perf = bool(capabilities.get("VISIBILITY") or capabilities.get("ENGAGEMENT") or capabilities.get("CONVERSION"))

    primary_entity_type = "unknown"
    if is_wide_time_series:
        primary_entity_type = "time_series"
    elif any("seller" in c.lower() for c in clean_cols):
        primary_entity_type = "seller_directory"
    elif has_content and has_perf:
        primary_entity_type = "content_asset"
    elif has_perf and not has_content:
        primary_entity_type = "performance_log"
    elif has_content and not has_perf:
        primary_entity_type = "content_metadata"
    elif capabilities.get("TIME_SERIES"):
        primary_entity_type = "time_series"

    detected_list = [k for k, v in capabilities.items() if v]
    missing_list = [k for k, v in capabilities.items() if not v]

    res = {
        "capabilities": capabilities,
        "capability_columns": matched_columns,
        "detected_capabilities": detected_list,
        "missing_capabilities": missing_list,
        "target_candidates": target_candidates,
        "has_content_signals": has_content,
        "has_performance_signals": has_perf,
        "primary_entity_type": primary_entity_type,
    }
    for cap, is_present in capabilities.items():
        res[cap] = {
            "present": is_present,
            "columns": matched_columns.get(cap, []),
        }
    return res


def detect_capabilities(
    columns_or_profile: Any,
    dtypes: Optional[Dict[str, str]] = None,
    is_wide_time_series: bool = False,
    profile_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Helper alias accepting either a column list or a dataset profile dictionary."""
    if isinstance(columns_or_profile, dict) and "columns" in columns_or_profile:
        col_data = columns_or_profile["columns"]
        cols = list(col_data.keys()) if isinstance(col_data, dict) else list(col_data)
        if not dtypes and isinstance(col_data, dict):
            dtypes = {c: m.get("dtype", "") if isinstance(m, dict) else "" for c, m in col_data.items()}
        is_wide = columns_or_profile.get("is_wide_time_series", False)
        return detect_dataset_capabilities(cols, dtypes=dtypes, is_wide_time_series=is_wide, profile_data=columns_or_profile)
    return detect_dataset_capabilities(columns_or_profile, dtypes=dtypes, is_wide_time_series=is_wide_time_series, profile_data=profile_data)

