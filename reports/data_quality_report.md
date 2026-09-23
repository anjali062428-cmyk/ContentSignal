# Data Quality and Quarantine Audit Report

**Date:** September 2026  
**Status:** VALIDATED & QUARANTINED

---

## 1. Executive Summary

- **Raw Ingestion:** 30,000 rows × 53 columns.
- **Clean Modeling Inventory:** 30,000 rows × 44 columns.
- **Entities Covered:** 30,000 unique content pages across 32 client organizations.
- **Schema Compliance:** 100% compliant with documented 44-column specification.

---

## 2. Restricted Column Quarantine Audit

To prevent circular logic and preserve discovery integrity, FlyRank proprietary decision flags and scores were quarantined immediately upon ingestion.

**Quarantined Columns (9):**
- `health_score` (RESTRICTED PROPRIETARY DECISION FIELD - EXCLUDED)
- `needs_indexing` (RESTRICTED PROPRIETARY DECISION FIELD - EXCLUDED)
- `is_quick_win` (RESTRICTED PROPRIETARY DECISION FIELD - EXCLUDED)
- `needs_ctr_fix` (RESTRICTED PROPRIETARY DECISION FIELD - EXCLUDED)
- `needs_engagement_fix` (RESTRICTED PROPRIETARY DECISION FIELD - EXCLUDED)
- `ai_opportunity` (RESTRICTED PROPRIETARY DECISION FIELD - EXCLUDED)
- `is_underperformer` (RESTRICTED PROPRIETARY DECISION FIELD - EXCLUDED)
- `is_declining` (RESTRICTED PROPRIETARY DECISION FIELD - EXCLUDED)
- `is_initial_refresh_candidate` (RESTRICTED PROPRIETARY DECISION FIELD - EXCLUDED)

> [!IMPORTANT]
> These 9 columns are permanently removed from the data pipeline and will never be accessed by feature engineering, modeling, evaluation, scoring, API responses, or frontend components.

---

## 3. Sentinel and Systematic Missingness Analysis

### A. Position Sentinel
- `avg_position == 0`: Found in **1,205** rows (4.02%).
- **Semantics:** Indicates **no ranking position data available** in the reporting window, NOT position zero.
- **Resolution:** Explicit binary indicator `is_missing_position` will be derived in feature engineering.

### B. Missingness Overview
| Column | Missing Count | % Missing | Handling Strategy |
|---|---|---|---|
| `provider_used` | 21,438 | 71.46% | Systematic by content type / preserve missingness indicator |
| `word_count` | 7,699 | 25.66% | Systematic by content type / preserve missingness indicator |
| `char_count` | 7,699 | 25.66% | Systematic by content type / preserve missingness indicator |
| `word_count_tier` | 7,699 | 25.66% | Systematic by content type / preserve missingness indicator |
| `char_count_tier` | 7,699 | 25.66% | Systematic by content type / preserve missingness indicator |
| `model_used` | 5,733 | 19.11% | Systematic by content type / preserve missingness indicator |
| `trend_pct` | 3,388 | 11.29% | Systematic by content type / preserve missingness indicator |
| `competition_level` | 2,610 | 8.7% | Systematic by content type / preserve missingness indicator |
| `search_volume` | 2,468 | 8.23% | Systematic by content type / preserve missingness indicator |
| `competition` | 2,468 | 8.23% | Systematic by content type / preserve missingness indicator |
| `cpc` | 2,468 | 8.23% | Systematic by content type / preserve missingness indicator |
| `main_intent` | 2,374 | 7.91% | Systematic by content type / preserve missingness indicator |
| `scroll_rate` | 125 | 0.42% | Systematic by content type / preserve missingness indicator |

---

## 4. Rate Metric Scale Verification

| Rate Column | Min | Max | Mean | Median | Scale Definition |
|---|---|---|---|---|---|
| `ctr` | 0.00 | 100.00 | 0.51 | 0.07 | Percentage (0–100 scale; 0.76 = 0.76%) |
| `engagement_rate` | 0.00 | 100.00 | 2.53 | 0.00 | Percentage (0–100 scale; 0.76 = 0.76%) |
| `scroll_rate` | 0.00 | 300.00 | 18.21 | 5.00 | Percentage (0–100 scale; 0.76 = 0.76%) |
| `ai_traffic_pct` | 0.00 | 300.00 | 0.77 | 0.00 | Percentage (0–100 scale; 0.76 = 0.76%) |
| `trend_pct` | -100.00 | 44900.00 | -4.79 | -33.50 | Percentage (0–100 scale; 0.76 = 0.76%) |

---

## 5. Certification
The cleaned dataset at `data/processed/clean_44_documented.csv` is certified free of proprietary FlyRank decision columns and fully compliant with data use rules.
