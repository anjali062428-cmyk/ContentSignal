# Target-Construction Leakage Audit Report

**Status:** PASSED (Zero Leakage Detected)  
**Audited Feature Count:** 40 legitimate features reaching estimator.

---

## 1. Executive Summary
This audit inspects the **actual feature names** reaching scikit-learn estimators prior to training. It enforces strict separation between observable prior features and target construction artifacts.

---

## 2. Six-Tier Column Classification

### Tier 1: Restricted Proprietary Columns (9)
*Quarantined upon raw ingestion. Forbidden across the entire codebase.*
- `ai_opportunity` (STATUS: QUARANTINED)
- `health_score` (STATUS: QUARANTINED)
- `is_declining` (STATUS: QUARANTINED)
- `is_initial_refresh_candidate` (STATUS: QUARANTINED)
- `is_quick_win` (STATUS: QUARANTINED)
- `is_underperformer` (STATUS: QUARANTINED)
- `needs_ctr_fix` (STATUS: QUARANTINED)
- `needs_engagement_fix` (STATUS: QUARANTINED)
- `needs_indexing` (STATUS: QUARANTINED)

### Tier 2: Identifiers (2)
*Hashed pseudonyms reserved strictly for grouping and client-aware splits.*
- `client_id` (STATUS: EXCLUDED FROM FEATURES)
- `content_id` (STATUS: EXCLUDED FROM FEATURES)

### Tier 3: Target Columns (1)
*The supervised ground truth label.*
- `is_declining_label` (STATUS: TARGET ONLY)

### Tier 4: Direct Target-Construction Variables (5)
*Input components of the target label. Banned from candidate features to prevent trivial target reconstruction.*
- `impressions_last_30d` (STATUS: STRICTLY BANNED)
- `impressions_prev_30d` (STATUS: STRICTLY BANNED)
- `impressions_change_30d` (STATUS: STRICTLY BANNED)
- `trend_direction` (STATUS: STRICTLY BANNED)
- `trend_pct` (STATUS: STRICTLY BANNED)

### Tier 5: Future Variables (3)
*Forward-looking observations requiring enterprise warehouse daily tables.*
- `next_30d_impressions (warehouse only)` (STATUS: NOT PRESENT IN STARTER SLICE)
- `next_30d_clicks (warehouse only)` (STATUS: NOT PRESENT IN STARTER SLICE)
- `next_30d_recovery_status (warehouse only)` (STATUS: NOT PRESENT IN STARTER SLICE)

### Tier 6: Legitimate Predictive Features (40)
*Clean, observable, leakage-safe features approved for model training.*
- `age_tier`
- `age_tier_order`
- `ai_sessions_90d`
- `ai_traffic_pct`
- `avg_position`
- `char_count`
- `char_count_tier`
- `click_to_session_ratio`
- `clicks_90d`
- `competition`
- `competition_level`
- `content_age_days`
- `content_type`
- `cpc`
- `ctr`
- `days_since_last_update`
- `days_with_impressions`
- `days_with_sessions`
- `engaged_session_ratio`
- `engaged_sessions_90d`
- `engagement_rate`
- `freshness_tier`
- `impression_tier`
- `impressions_90d`
- `is_missing_keyword_context`
- `is_missing_position`
- `is_missing_word_count`
- `log_clicks_90d`
- `log_impressions_90d`
- `log_sessions_90d`
- `main_intent`
- `pageviews_90d`
- `position_tier`
- `scroll_events_90d`
- `scroll_rate`
- `search_volume`
- `sessions_90d`
- `users_90d`
- `word_count`
- `word_count_tier`

---

## 3. Dynamic Pipeline Enforcement
The model training pipeline executes `audit_feature_names()` dynamically before fitting any estimator. If any banned column or token is detected, a `SecurityLeakageError` halts execution immediately.
