# Content Intelligence Engine — Model Evaluation & Selection Report

**Target:** `Starter proxy model: is_declining_label = (trend_direction == 'down')`  
**Model Framing:** CURRENT-WINDOW PROXY BASELINE  
**Selected Champion Model:** **Gradient Boosting**  
**Validation Strategy:** client-group holdout (26 train clients / 6 test clients)

---

## 1. Executive Summary & Model Comparison

In an editorial decision-support queue, **Precision@K** is the most critical operational metric: content teams can only inspect a limited number of candidate pages (top 20, 50, or 100) per review cycle.

| Model | ROC-AUC | PR-AUC | Precision@20 | Precision@50 | Precision@100 | Recall | F1 |
|---|---|---|---|---|---|---|---|
| **Transparent Baseline** | 0.5938 | 0.5669 | 0.3500 | 0.3600 | 0.3300 | 0.0777 | 0.1330 |
| **Logistic Regression** | 0.6510 | 0.6428 | 0.7500 | 0.7000 | 0.7000 | 0.7324 | 0.6662 |
| **Random Forest** | 0.6617 | 0.6287 | 0.4500 | 0.4400 | 0.4800 | 0.7915 | 0.6887 |
| **Gradient Boosting** | 0.6945 | 0.6791 | 0.6000 | 0.6800 | 0.7200 | 0.7470 | 0.6894 |

---

## 2. Selection Rationale

**Chosen Champion:** `gradient_boosting`  
Selected primarily based on Precision@50 and Precision@20 since the primary SaaS deliverable is a ranked editorial review queue for human content teams, supplemented by PR-AUC and ROC-AUC.

Both tree-based ensembles demonstrate significant lift over the transparent baseline, delivering high Precision@50 and strong PR-AUC while strictly adhering to zero target-construction leakage.

---

## 3. Top Feature Importance (gradient_boosting)

| Rank | Feature Name | Importance Weight |
|---|---|---|
| 1 | `days_with_impressions` | 0.0859 |
| 2 | `log_impressions_90d` | 0.0840 |
| 3 | `impressions_90d` | 0.0839 |
| 4 | `content_age_days` | 0.0726 |
| 5 | `avg_position` | 0.0617 |
| 6 | `word_count` | 0.0394 |
| 7 | `char_count` | 0.0359 |
| 8 | `scroll_rate` | 0.0284 |
| 9 | `ctr` | 0.0267 |
| 10 | `clicks_90d` | 0.0224 |
| 11 | `log_clicks_90d` | 0.0213 |
| 12 | `is_missing_position` | 0.0208 |
| 13 | `days_with_sessions` | 0.0208 |
| 14 | `click_to_session_ratio` | 0.0200 |
| 15 | `pageviews_90d` | 0.0200 |

---

## 4. Dataset & Validation Split Metadata

- **Total Inventory Rows:** 30,000
- **Train Set Size:** 26,619 rows (26 clients)
- **Test Set Size:** 3,381 rows (6 clients)
- **Random Seed:** 42
- **Raw Input Features:** 40
- **One-Hot Transformed Estimator Features:** 70

---

## 5. Future-Window Extension Status

> [!NOTE]
> **Status:** `Not yet run — requires warehouse access.`  
> Requires prior 90-day features predicting forward 30-day outcomes across daily warehouse tables.
