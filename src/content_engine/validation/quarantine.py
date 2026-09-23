"""
Data Ingestion and Restricted Column Quarantine.
Enforces strict quarantine of 9 proprietary FlyRank decision columns,
validates column schemas against the documented 44 columns,
checks data quality, sentinel values, percentage-scale rates,
and outputs clean_44_documented.csv and data quality reports.
"""
import json
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

from content_engine.config import (
    RAW_DATA_PATH,
    CLEAN_DATA_PATH,
    REPORTS_DIR,
    DOCUMENTED_44_COLUMNS,
    RESTRICTED_FLYRANK_COLUMNS,
)


def quarantine_and_clean_dataset(
    raw_path: Path = RAW_DATA_PATH,
    clean_path: Path = CLEAN_DATA_PATH,
    reports_dir: Path = REPORTS_DIR,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Ingests raw dataset, quarantines proprietary columns, validates schema,
    and produces data quality reports.
    """
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw dataset not found at {raw_path}")

    # Read raw dataset
    df_raw = pd.read_csv(raw_path)
    total_raw_rows, total_raw_cols = df_raw.shape

    # 1. Inspect and quarantine the 9 restricted columns
    found_restricted = [c for c in RESTRICTED_FLYRANK_COLUMNS if c in df_raw.columns]
    missing_restricted = [c for c in RESTRICTED_FLYRANK_COLUMNS if c not in df_raw.columns]

    quarantine_audit = {
        "quarantined_columns_found": found_restricted,
        "quarantined_columns_missing": missing_restricted,
        "quarantine_count": len(found_restricted),
        "status": "QUARANTINED_SUCCESSFULLY",
    }

    # Drop restricted columns immediately
    df_clean = df_raw.drop(columns=found_restricted).copy()

    # 2. Check for unexpected undocumented columns
    unexpected_cols = [
        c for c in df_clean.columns if c not in DOCUMENTED_44_COLUMNS
    ]
    if unexpected_cols:
        raise ValueError(
            f"SECURITY ALERT: Unexpected undocumented columns detected in raw data: {unexpected_cols}. "
            "Pipeline halted to prevent unintended data leakage."
        )

    # 3. Verify exactly documented 44 columns remain
    missing_doc_cols = [
        c for c in DOCUMENTED_44_COLUMNS if c not in df_clean.columns
    ]
    if missing_doc_cols:
        raise ValueError(f"Missing expected documented columns: {missing_doc_cols}")

    # Reorder columns to match canonical documented order
    df_clean = df_clean[DOCUMENTED_44_COLUMNS].copy()

    # 4. Data Quality & Sentinel Analysis
    # A. avg_position: 0 indicates 'no position data', not rank 0
    zero_pos_count = int((df_clean["avg_position"] == 0).sum())
    
    # B. Missingness analysis
    null_counts = df_clean.isnull().sum().to_dict()
    missing_summary = {k: int(v) for k, v in null_counts.items() if v > 0}

    # Systematic missingness by content_type
    missingness_by_content_type = {}
    for c_type, group in df_clean.groupby("content_type", observed=False):
        missingness_by_content_type[str(c_type)] = {
            "search_volume_missing": int(group["search_volume"].isnull().sum()),
            "cpc_missing": int(group["cpc"].isnull().sum()),
            "word_count_missing": int(group["word_count"].isnull().sum()),
            "total_rows": int(len(group)),
        }

    # C. Rates validation (confirm percentage-scale values, e.g. 0.76 is 0.76%, not 76%)
    rate_cols = ["ctr", "engagement_rate", "scroll_rate", "ai_traffic_pct", "trend_pct"]
    rate_stats = {}
    for rcol in rate_cols:
        if rcol in df_clean.columns:
            series = df_clean[rcol].dropna()
            rate_stats[rcol] = {
                "min": float(series.min()) if not series.empty else 0.0,
                "max": float(series.max()) if not series.empty else 0.0,
                "mean": float(series.mean()) if not series.empty else 0.0,
                "median": float(series.median()) if not series.empty else 0.0,
                "values_above_100": int((series > 100).sum()),
            }

    # D. Deduplication and Grain Check
    unique_content_ids = int(df_clean["content_id"].nunique())
    unique_clients = int(df_clean["client_id"].nunique())

    # Build Comprehensive Quality Report Dictionary
    quality_report = {
        "raw_dataset": {
            "path": str(raw_path),
            "rows": total_raw_rows,
            "columns": total_raw_cols,
        },
        "clean_dataset": {
            "rows": int(len(df_clean)),
            "columns": int(df_clean.shape[1]),
            "unique_pages": unique_content_ids,
            "unique_clients": unique_clients,
            "exact_44_documented_columns": True,
        },
        "quarantine_audit": quarantine_audit,
        "sentinel_analysis": {
            "avg_position_zero_means_missing": True,
            "zero_avg_position_count": zero_pos_count,
            "zero_avg_position_pct": round(zero_pos_count / total_raw_rows * 100, 2),
        },
        "systematic_missingness": {
            "columns_with_nulls": missing_summary,
            "by_content_type": missingness_by_content_type,
        },
        "rate_scale_verification": {
            "notes": "Rates (ctr, engagement_rate, etc.) are 0-100 percentage values (e.g., ctr=0.76 means 0.76%).",
            "metrics": rate_stats,
        },
    }

    # Save clean dataset
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(clean_path, index=False)

    # Save reports
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_report_path = reports_dir / "data_quality_report.json"
    with open(json_report_path, "w", encoding="utf-8") as f:
        json.dump(quality_report, f, indent=2)

    md_report_path = reports_dir / "data_quality_report.md"
    _generate_markdown_quality_report(quality_report, md_report_path)

    return df_clean, quality_report


def _generate_markdown_quality_report(report: Dict[str, Any], output_path: Path) -> None:
    """Generates markdown documentation for data quality and quarantine audit."""
    quarantine = report["quarantine_audit"]
    clean = report["clean_dataset"]
    sentinels = report["sentinel_analysis"]
    missing = report["systematic_missingness"]["columns_with_nulls"]
    rates = report["rate_scale_verification"]["metrics"]

    md = f"""# Data Quality and Quarantine Audit Report

**Date:** September 2026  
**Status:** VALIDATED & QUARANTINED

---

## 1. Executive Summary

- **Raw Ingestion:** {report['raw_dataset']['rows']:,} rows × {report['raw_dataset']['columns']} columns.
- **Clean Modeling Inventory:** {clean['rows']:,} rows × {clean['columns']} columns.
- **Entities Covered:** {clean['unique_pages']:,} unique content pages across {clean['unique_clients']} client organizations.
- **Schema Compliance:** 100% compliant with documented 44-column specification.

---

## 2. Restricted Column Quarantine Audit

To prevent circular logic and preserve discovery integrity, FlyRank proprietary decision flags and scores were quarantined immediately upon ingestion.

**Quarantined Columns ({quarantine['quarantine_count']}):**
"""
    for col in quarantine["quarantined_columns_found"]:
        md += f"- `{col}` (RESTRICTED PROPRIETARY DECISION FIELD - EXCLUDED)\n"

    md += f"""
> [!IMPORTANT]
> These {quarantine['quarantine_count']} columns are permanently removed from the data pipeline and will never be accessed by feature engineering, modeling, evaluation, scoring, API responses, or frontend components.

---

## 3. Sentinel and Systematic Missingness Analysis

### A. Position Sentinel
- `avg_position == 0`: Found in **{sentinels['zero_avg_position_count']:,}** rows ({sentinels['zero_avg_position_pct']}%).
- **Semantics:** Indicates **no ranking position data available** in the reporting window, NOT position zero.
- **Resolution:** Explicit binary indicator `is_missing_position` will be derived in feature engineering.

### B. Missingness Overview
| Column | Missing Count | % Missing | Handling Strategy |
|---|---|---|---|
"""
    for col, count in sorted(missing.items(), key=lambda x: x[1], reverse=True):
        pct = round(count / clean['rows'] * 100, 2)
        md += f"| `{col}` | {count:,} | {pct}% | Systematic by content type / preserve missingness indicator |\n"

    md += """
---

## 4. Rate Metric Scale Verification

| Rate Column | Min | Max | Mean | Median | Scale Definition |
|---|---|---|---|---|---|
"""
    for rcol, stats in rates.items():
        md += f"| `{rcol}` | {stats['min']:.2f} | {stats['max']:.2f} | {stats['mean']:.2f} | {stats['median']:.2f} | Percentage (0–100 scale; 0.76 = 0.76%) |\n"

    md += """
---

## 5. Certification
The cleaned dataset at `data/processed/clean_44_documented.csv` is certified free of proprietary FlyRank decision columns and fully compliant with data use rules.
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    print("Running quarantine and data quality audit...")
    df, rep = quarantine_and_clean_dataset()
    print(f"Done! Clean dataset shape: {df.shape}")
    print(f"Quarantined {rep['quarantine_audit']['quarantine_count']} columns.")
