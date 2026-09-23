# Target Formulation & Validation Methodology: Starter Proxy vs. Future-Window

This document defines the dual target architecture of the Content Intelligence Engine.

---

## 1. Formulation A: Starter Proxy Model (Current Implementation)

### Definition
$$\text{is\_declining\_label} = (\text{trend\_direction} == \text{"down"})$$

### Operational Meaning
A page is labeled positive if its observed Google Search Console impressions dropped by >20% between days 31–60 and days 1–30 within the 90-day export window:
$$\text{trend\_pct} = \frac{\text{impressions\_last\_30d} - \text{impressions\_prev\_30d}}{\text{impressions\_prev\_30d}} \times 100 < -20.0$$

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
$$\text{Prior 90-Day Observable Features } [t - 90, t] \longrightarrow \text{Observed Forward Outcome } [t, t + 30]$$

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
