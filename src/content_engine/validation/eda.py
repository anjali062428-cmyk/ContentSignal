"""
Exploratory Data Analysis (EDA) and Target Definition Module.
Analyzes traffic, search signals, content metadata distributions,
and formalizes the distinction between Starter Proxy Model vs Future-Window Extension.
Outputs reports/eda_report.json, reports/eda_report.md, and reports/LABEL_AND_TARGET.md.
"""
import json
from pathlib import Path
from typing import Dict, Any
import pandas as pd
import numpy as np

from content_engine.config import (
    CLEAN_DATA_PATH,
    REPORTS_DIR,
    TARGET_COLUMN,
)


def run_eda_and_target_analysis(
    data_path: Path = CLEAN_DATA_PATH,
    reports_dir: Path = REPORTS_DIR,
) -> Dict[str, Any]:
    """Runs comprehensive EDA on the clean 44-column dataset."""
    df = pd.read_csv(data_path)
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 1. Dataset Shape and Entity Counts
    n_rows = len(df)
    n_clients = int(df["client_id"].nunique())
    pages_per_client = df["client_id"].value_counts()

    # 2. Starter Target Distribution (is_declining_label = trend_direction == 'down')
    trend_counts = df["trend_direction"].value_counts().to_dict()
    is_declining_count = int((df["trend_direction"] == "down").sum())
    is_declining_pct = round(is_declining_count / n_rows * 100, 2)

    target_stats = {
        "definition": "trend_direction == 'down'",
        "framing": "Starter Proxy Model / Current-Window Baseline",
        "is_future_forecast": False,
        "total_positive_cases": is_declining_count,
        "positive_rate_pct": is_declining_pct,
        "trend_direction_breakdown": {str(k): int(v) for k, v in trend_counts.items()},
    }

    # 3. Content Types and Intent Distributions
    content_type_dist = df["content_type"].value_counts().to_dict()
    intent_dist = df["main_intent"].value_counts(dropna=False).to_dict()
    intent_dist = {str(k): int(v) for k, v in intent_dist.items()}

    # 4. Traffic & Engagement Summary
    traffic_metrics = [
        "impressions_90d", "clicks_90d", "sessions_90d", "pageviews_90d",
        "engaged_sessions_90d", "ai_sessions_90d", "ctr", "avg_position",
        "engagement_rate", "scroll_rate"
    ]
    numeric_summary = {}
    for col in traffic_metrics:
        if col in df.columns:
            s = df[col].dropna()
            numeric_summary[col] = {
                "mean": round(float(s.mean()), 2),
                "std": round(float(s.std()), 2),
                "median": round(float(s.median()), 2),
                "p25": round(float(s.quantile(0.25)), 2),
                "p75": round(float(s.quantile(0.75)), 2),
                "p95": round(float(s.quantile(0.95)), 2),
                "max": round(float(s.max()), 2),
            }

    # 5. AI Referral Density Check
    ai_sessions_total = int(df["ai_sessions_90d"].sum())
    pages_with_ai = int((df["ai_sessions_90d"] > 0).sum())
    ai_analysis = {
        "total_ai_sessions": ai_sessions_total,
        "pages_with_ai_traffic": pages_with_ai,
        "pct_pages_with_ai": round(pages_with_ai / n_rows * 100, 2),
        "sparsity_guidance": "AI referral traffic is extremely sparse (~6% of pages). It serves as an auxiliary signal, never as the standalone core classification target."
    }

    eda_report = {
        "inventory": {
            "total_pages": n_rows,
            "total_clients": n_clients,
            "min_pages_per_client": int(pages_per_client.min()),
            "max_pages_per_client": int(pages_per_client.max()),
            "median_pages_per_client": float(pages_per_client.median()),
        },
        "target_analysis": target_stats,
        "content_archetype_distribution": {
            "content_type": {str(k): int(v) for k, v in content_type_dist.items()},
            "main_intent": intent_dist,
        },
        "numeric_distributions": numeric_summary,
        "ai_referral_analysis": ai_analysis,
    }

    # Save JSON report
    with open(reports_dir / "eda_report.json", "w", encoding="utf-8") as f:
        json.dump(eda_report, f, indent=2)

    # Save Markdown reports
    _generate_eda_markdown(eda_report, reports_dir / "eda_report.md")
    _generate_label_and_target_markdown(reports_dir / "LABEL_AND_TARGET.md")

    return eda_report


def _generate_eda_markdown(report: Dict[str, Any], output_path: Path) -> None:
    inv = report["inventory"]
    target = report["target_analysis"]
    ai = report["ai_referral_analysis"]
    num = report["numeric_distributions"]

    md = f"""# Exploratory Data Analysis Report — Content Intelligence Engine

**Dataset:** Clean 44-column documented FlyRank slice ({inv['total_pages']:,} rows, {inv['total_clients']} clients)  
**Target Framing:** Starter Proxy Model (Current-Window Baseline)

---

## 1. Inventory & Client Cohort Overview

- **Total Analyzed Pages:** {inv['total_pages']:,}
- **Client Organizations:** {inv['total_clients']}
- **Pages per Client:** Median {inv['median_pages_per_client']} (Range: {inv['min_pages_per_client']} – {inv['max_pages_per_client']})
- **Holdout Validation Requirement:** Grouped client split is mandatory to prevent intra-client domain memorization.

---

## 2. Target Variable Analysis: Starter Proxy

The starter target is defined as:
$$\\text{{is\\_declining\\_label}} = (\\text{{trend\\_direction}} == \\text{{"down"}})$$

- **Positive Class (Declining):** {target['total_positive_cases']:,} ({target['positive_rate_pct']}%)
- **Distribution of Trend Directions:**
"""
    for t_dir, count in target["trend_direction_breakdown"].items():
        pct = round(count / inv['total_pages'] * 100, 1)
        md += f"  - `{t_dir}`: {count:,} ({pct}%)\n"

    md += f"""
> [!NOTE]
> **Starter Proxy Caveat:** This target is a *current-window proxy* derived from comparing impressions in the last 30 days versus the previous 30 days within the same observation snapshot. It is NOT a forward-looking future forecast.

---

## 3. Search & Traffic Distribution Summary

| Metric | Median | Mean | 75th %ile | 95th %ile | Max |
|---|---|---|---|---|---|
"""
    for metric, s in num.items():
        md += f"| `{metric}` | {s['median']:,} | {s['mean']:,} | {s['p75']:,} | {s['p95']:,} | {s['max']:,} |\n"

    md += f"""
---

## 4. AI Referral Signal Density

- **Pages with AI Referrals:** {ai['pages_with_ai_traffic']:,} of {inv['total_pages']:,} ({ai['pct_pages_with_ai']}%)
- **Total AI Referral Sessions:** {ai['total_ai_sessions']:,}
- **Engineering Principle:** {ai['sparsity_guidance']}
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)


def _generate_label_and_target_markdown(output_path: Path) -> None:
    content = """# Target Formulation & Validation Methodology: Starter Proxy vs. Future-Window

This document defines the dual target architecture of the Content Intelligence Engine.

---

## 1. Formulation A: Starter Proxy Model (Current Implementation)

### Definition
$$\\text{is\\_declining\\_label} = (\\text{trend\\_direction} == \\text{"down"})$$

### Operational Meaning
A page is labeled positive if its observed Google Search Console impressions dropped by >20% between days 31–60 and days 1–30 within the 90-day export window:
$$\\text{trend\\_pct} = \\frac{\\text{impressions\\_last\\_30d} - \\text{impressions\\_prev\\_30d}}{\\text{impressions\\_prev\\_30d}} \\times 100 < -20.0$$

### Critical Framing & Language Rules
- **Canonical Terminology:** "Starter proxy model" or "current-window baseline".
- **Forbidden Claims:** NEVER describe this model as a "future forecast", "future decline prediction", or "predicting Google algorithm shifts".
- **Product Role:** Decision-support ranking to identify which pages are currently deteriorating in demand and visibility.

### Target-Construction Leakage Quarantine
Because the label is mathematically derived from `impressions_last_30d` and `impressions_prev_30d`, the following features are **strictly banned** from reaching any model estimator:
1. `impressions_last_30d`
2. `impressions_prev_30d`
3. `impressions_change_30d`
4. `trend_direction`
5. `trend_pct`
6. Any direct ratio between last 30d and prev 30d impressions.

---

## 2. Formulation B: Future-Window Extension (Warehouse Scale)

### Definition
$$\\text{Prior 90-Day Observable Features } [t - 90, t] \\longrightarrow \\text{Observed Forward Outcome } [t, t + 30]$$

### Required Enterprise Data Warehouse Sources
1. `fact_content_daily_performance`: Daily report dates, client hash, content hash, daily impressions, clicks, position, sessions.
2. `fact_content_query_90d`: Query level diversity, top queries, query impressions share.
3. `dim_clients`: Client start dates, GA4/GSC access status, domain lifecycle.
4. `dim_content`: Content metadata, canonical URL hashes, authoring timeline.

### Temporal Discipline & Leakage Safeguards
1. **Feature Cutoff:** Strictly at timestamp $t$. No daily records where `report_date > t` may enter the feature matrix.
2. **Prediction Window:** Forward 30-day window $[t, t + 30]$.
3. **Temporal Holdout Validation:** Train on historical cohort $[t - 180, t - 30]$, validate on forward period $[t - 30, t]$.
4. **Client-Aware Split:** Ensure newly onboarded clients or distinct clients are partitioned cleanly.

### Current Status
**"Not yet run — requires warehouse access."**
The codebase is architected with clear abstractions so that daily fact table extractors can plug into the existing feature and evaluation pipelines seamlessly.
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    print("Running EDA and Target Analysis...")
    report = run_eda_and_target_analysis()
    print("EDA Complete! Positive rate:", report["target_analysis"]["positive_rate_pct"], "%")
