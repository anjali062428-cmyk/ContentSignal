"""
Dataset Validator Module.
Provides dual-mode schema validation and readiness checks:
1. Isolated FlyRank Safety Mode: enforces strict 44-column contract, 9-column quarantine,
   trend leakage blocking, percentage scales, and duplicate ID detection.
2. Generic Dataset-Agnostic Mode: executes chunked profiling, semantic capability detection,
   readiness checklist evaluation, and canonical column mapping.
"""
from typing import Dict, Any, Tuple, Optional, List
import pandas as pd
import numpy as np

from content_engine.config import (
    DOCUMENTED_44_COLUMNS,
    RESTRICTED_FLYRANK_COLUMNS,
    OPTIONAL_PAGE_INTELLIGENCE_COLUMNS,
)
from content_engine.capabilities.profiler import profile_dataset
from content_engine.capabilities.detector import detect_dataset_capabilities
from content_engine.readiness.checker import evaluate_dataset_readiness
from content_engine.canonical.mapper import map_dataframe_to_canonical
from content_engine.classification.page_classifier import extract_and_normalize_domain


def is_flyrank_schema_candidate(raw_cols: List[str]) -> bool:
    """Detects if incoming dataset is formatted as a FlyRank schema candidate."""
    cols_set = set(c.strip() for c in raw_cols)
    # If it contains core FlyRank specific columns
    flyrank_markers = {"content_id", "client_id", "impressions_90d", "clicks_90d", "sessions_90d", "avg_position", "ctr"}
    intersection = cols_set.intersection(flyrank_markers)
    # Also if it contains quarantined FlyRank columns
    has_quarantine = any(c in cols_set for c in RESTRICTED_FLYRANK_COLUMNS)
    return len(intersection) >= 3 or has_quarantine


def validate_dataset(
    df_raw: pd.DataFrame,
    explicit_target: Optional[str] = None,
) -> Tuple[bool, Dict[str, Any], Optional[pd.DataFrame]]:
    """
    Validates an incoming dataset against schema and capability requirements.
    Supports both FlyRank reference format and generic tabular/content formats.
    """
    total_rows, total_cols = df_raw.shape
    if total_rows == 0:
        return False, {
            "is_valid": False,
            "row_count": 0,
            "column_count": total_cols,
            "valid_status": "INVALID",
            "missing_required_fields": [],
            "quarantined_fields": [],
            "unexpected_fields": [],
            "has_domain_data": False,
            "duplicate_ids_count": 0,
            "warnings": [],
            "errors": ["Uploaded dataset contains 0 rows."],
            "readiness": {"status": "NOT_READY", "score": 0, "checks": []},
            "capabilities": {},
            "mapping": [],
        }, None

    raw_cols = list(df_raw.columns)
    cols_clean = [str(c).strip() for c in raw_cols]
    df_clean = df_raw.copy()
    df_clean.columns = cols_clean

    # Run generic profiler and capability detector
    profile = profile_dataset(df_clean)
    capabilities = detect_dataset_capabilities(
        columns=cols_clean,
        dtypes=profile.get("dtypes", {}),
        is_wide_time_series=profile.get("is_wide_time_series", False),
    )
    readiness = evaluate_dataset_readiness(profile, capabilities, user_selected_target=explicit_target)
    mappings, df_canonical = map_dataframe_to_canonical(df_clean, explicit_target=explicit_target)

    # Domain intelligence check
    distinct_domains = []
    distinct_page_types = []
    has_domain_data = False

    if "domain" in cols_clean or "url" in cols_clean:
        dom_series = pd.Series(index=df_clean.index, dtype="object")
        if "domain" in cols_clean:
            dom_series = df_clean["domain"].fillna("").astype(str).str.strip().str.lower()
        if "url" in cols_clean:
            extracted = df_clean["url"].apply(extract_and_normalize_domain).fillna("")
            dom_series = dom_series.replace("", np.nan).fillna(extracted)
        
        dom_series = dom_series.apply(lambda d: d[4:] if isinstance(d, str) and d.startswith("www.") else d)
        distinct_domains = sorted([str(d) for d in dom_series.unique() if d and pd.notna(d) and str(d) != "nan" and str(d) != ""])
        has_domain_data = len(distinct_domains) > 0

    if "page_type" in cols_clean:
        distinct_page_types = sorted([str(p) for p in df_clean["page_type"].dropna().unique() if str(p)])

    errors = []
    warnings = readiness.get("warnings", []).copy()
    quarantined = []
    unexpected = []
    missing_required = []

    # 1. FlyRank-Specific Schema Verification (if dataset is FlyRank or claims FlyRank schema)
    if is_flyrank_schema_candidate(cols_clean):
        # Identify and quarantine restricted FlyRank decision columns
        found_restricted = [c for c in RESTRICTED_FLYRANK_COLUMNS if c in cols_clean]
        if found_restricted:
            quarantined = found_restricted
            warnings.append(
                f"Detected and quarantined {len(found_restricted)} proprietary FlyRank columns: {found_restricted}. "
                "These have been safely excluded from analysis and will not be used in features."
            )
            df_clean = df_clean.drop(columns=found_restricted).copy()
            cols_clean = list(df_clean.columns)

        # Check for unexpected columns against FlyRank contract
        allowed_columns = set(DOCUMENTED_44_COLUMNS) | set(OPTIONAL_PAGE_INTELLIGENCE_COLUMNS)
        unexpected = [c for c in cols_clean if c not in allowed_columns]
        if unexpected:
            errors.append(
                f"Dataset contains {len(unexpected)} unexpected / undocumented columns: {unexpected}. "
                "Only documented 44-column schema columns and optional domain/URL fields are accepted."
            )

        # Check for missing documented columns
        missing_required = [c for c in DOCUMENTED_44_COLUMNS if c not in cols_clean]
        if missing_required:
            errors.append(
                f"Dataset is missing {len(missing_required)} required documented columns: {missing_required}."
            )

        # Duplicate IDs
        if "content_id" in cols_clean:
            dup_count = int(df_clean["content_id"].duplicated().sum())
            if dup_count > 0:
                errors.append(f"Found {dup_count} duplicate content_id records. Primary identifiers must be strictly unique.")

        # Rate validations (e.g. CTR > 100%)
        for rate_col in ("ctr", "engagement_rate", "scroll_rate"):
            if rate_col in cols_clean:
                s = df_clean[rate_col].dropna()
                if (s > 100.0).any() or (s < 0.0).any():
                    errors.append(f"Column '{rate_col}' contains invalid percentage values outside 0-100% range.")

        is_valid = len(errors) == 0
        valid_status = "VALID" if is_valid else "INVALID"

        summary = {
            "is_valid": is_valid,
            "row_count": total_rows,
            "column_count": total_cols,
            "valid_status": valid_status,
            "missing_required_fields": missing_required,
            "quarantined_fields": quarantined,
            "unexpected_fields": unexpected,
            "has_domain_data": has_domain_data,
            "distinct_domains_count": len(distinct_domains),
            "distinct_domains": distinct_domains,
            "distinct_page_types": distinct_page_types,
            "duplicate_ids_count": int(df_clean["content_id"].duplicated().sum()) if "content_id" in df_clean.columns else profile.get("duplicate_count", 0),
            "warnings": warnings,
            "errors": errors,
            "readiness": readiness,
            "capabilities": capabilities,
            "mapping": mappings,
            "adapter_type": "FlyRankAdapter",
        }
        return is_valid, summary, df_clean if is_valid else None

    # 2. Generic Dataset-Agnostic Mode (SEO, Social, Medium, News, Negative datasets, etc.)
    is_valid = readiness.get("is_ready", False)
    valid_status = "VALID" if is_valid else "INVALID"

    if not is_valid:
        errors.extend(readiness.get("reasons", []))
        if readiness.get("rejection_reason"):
            errors.append(f"Readiness check failed: {readiness['rejection_reason']}")

    summary = {
        "is_valid": is_valid,
        "row_count": total_rows,
        "column_count": total_cols,
        "valid_status": valid_status,
        "missing_required_fields": capabilities.get("missing_capabilities", []),
        "quarantined_fields": readiness.get("potential_leakage_columns", []),
        "unexpected_fields": [],
        "has_domain_data": has_domain_data,
        "distinct_domains_count": len(distinct_domains),
        "distinct_domains": distinct_domains,
        "distinct_page_types": distinct_page_types,
        "duplicate_ids_count": int(df_clean["content_id"].duplicated().sum()) if "content_id" in df_clean.columns else profile.get("duplicate_count", 0),
        "warnings": warnings,
        "errors": errors,
        "readiness": readiness,
        "capabilities": capabilities,
        "mapping": mappings,
        "adapter_type": "TimeSeriesAdapter" if readiness["status"] == "TIME_SERIES" else "GenericTabularAdapter",
    }
    return is_valid, summary, df_clean if is_valid else None
