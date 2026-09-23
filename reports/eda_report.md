# Exploratory Data Analysis Report — Content Intelligence Engine

**Dataset:** Clean 44-column documented FlyRank slice (30,000 rows, 32 clients)  
**Target Framing:** Starter Proxy Model (Current-Window Baseline)

---

## 1. Inventory & Client Cohort Overview

- **Total Analyzed Pages:** 30,000
- **Client Organizations:** 32
- **Pages per Client:** Median 567.0 (Range: 3 – 7008)
- **Holdout Validation Requirement:** Grouped client split is mandatory to prevent intra-client domain memorization.

---

## 2. Target Variable Analysis: Starter Proxy

The starter target is defined as:
$$\text{is\_declining\_label} = (\text{trend\_direction} == \text{"down"})$$

- **Positive Class (Declining):** 16,262 (54.21%)
- **Distribution of Trend Directions:**
  - `down`: 16,262 (54.2%)
  - `stable`: 5,962 (19.9%)
  - `up`: 4,388 (14.6%)
  - `new`: 2,236 (7.5%)
  - `flat`: 1,152 (3.8%)

> [!NOTE]
> **Starter Proxy Caveat:** This target is a *current-window proxy* derived from comparing impressions in the last 30 days versus the previous 30 days within the same observation snapshot. It is NOT a forward-looking future forecast.

---

## 3. Search & Traffic Distribution Summary

| Metric | Median | Mean | 75th %ile | 95th %ile | Max |
|---|---|---|---|---|---|
| `impressions_90d` | 731.0 | 5,200.37 | 3,615.25 | 22,996.5 | 517,715.0 |
| `clicks_90d` | 1.0 | 16.1 | 7.0 | 69.05 | 4,178.0 |
| `sessions_90d` | 7.0 | 37.07 | 27.0 | 166.0 | 4,345.0 |
| `pageviews_90d` | 8.0 | 49.94 | 33.0 | 231.05 | 5,998.0 |
| `engaged_sessions_90d` | 0.0 | 0.99 | 1.0 | 5.0 | 290.0 |
| `ai_sessions_90d` | 0.0 | 0.2 | 0.0 | 1.0 | 64.0 |
| `ctr` | 0.07 | 0.51 | 0.29 | 1.09 | 100.0 |
| `avg_position` | 10.8 | 16.34 | 22.3 | 48.2 | 245.0 |
| `engagement_rate` | 0.0 | 2.53 | 1.35 | 12.5 | 100.0 |
| `scroll_rate` | 5.0 | 18.21 | 23.53 | 100.0 | 300.0 |

---

## 4. AI Referral Signal Density

- **Pages with AI Referrals:** 1,930 of 30,000 (6.43%)
- **Total AI Referral Sessions:** 6,135
- **Engineering Principle:** AI referral traffic is extremely sparse (~6% of pages). It serves as an auxiliary signal, never as the standalone core classification target.
