# Week 5 — Capstone Modeling

## 1. Objective

This submission runs a leakage-controlled benchmark for the Content Intelligence Engine's Starter proxy model. The notebook loads the local dataset, verifies its contract, uses the repository's approved features and client-group split, trains the existing baseline and three candidate classifiers, and reports holdout metrics calculated by the repository evaluator.

The target is a current-window proxy for observed decline. This run does not predict a future decline, an algorithm change, or the effect of an editorial intervention.

Evidence: reports/LABEL_AND_TARGET.md, reports/model_report.md, docs/data-dictionary.md, src/content_engine/models/train.py, and the executed notebook.

## 2. Dataset

The source CSV is data/raw/content_refresh_anonymized.csv. Direct inspection and execution found 30,000 rows and 53 raw columns. The nine restricted decision fields were dropped before feature construction, leaving exactly 30,000 rows and the documented 44 columns. There are 30,000 distinct content IDs and 32 client groups.

The existing processed clean file was 30,000 × 44 and feature_vector.csv was 30,000 × 53. Its target matched the fresh transformation, and all 40 selected feature columns matched (numeric values checked with floating-point tolerance; categorical values exactly). The notebook itself builds features in memory from the raw file rather than trusting a generated artifact.

The 44 documented columns are grouped as follows:

| Group | Columns |
|---|---|
| Identifiers | content_id, client_id |
| Keyword context and taxonomy | search_volume, competition, competition_level, cpc, content_type, main_intent |
| Content properties | word_count, char_count, provider_used, model_used, content_age_days, days_since_last_update |
| Trailing 90-day activity | impressions_90d, clicks_90d, pageviews_90d, sessions_90d, users_90d, engaged_sessions_90d, ai_sessions_90d, scroll_events_90d, days_with_impressions, days_with_sessions |
| 30-day comparison windows | impressions_last_30d, clicks_last_30d, sessions_last_30d, impressions_prev_30d, clicks_prev_30d, sessions_prev_30d |
| Derived rates and position | ctr, avg_position, engagement_rate, scroll_rate, ai_traffic_pct, trend_pct |
| Buckets and target source | age_tier, age_tier_order, freshness_tier, word_count_tier, char_count_tier, impression_tier, position_tier, trend_direction |

All rate fields use the repository's 0–100 percentage scale. The starter slice contains trailing 90-day aggregates and comparison-window fields; it does not contain the warehouse daily report_date history needed for the future-window extension.

Evidence: reports/data_quality_report.md, reports/eda_report.md, docs/data-dictionary.md, and direct CSV schema checks in the notebook.

## 3. Target / Label

The binary target column is is_declining_label. It is added by src/content_engine/features/builder.py and is defined as:

    is_declining_label = (trend_direction == "down").astype(int)

The label source trend_direction is a categorical field in the input data. The data dictionary defines down as a greater than 20% decrease in impressions from the previous 30-day comparison window to the latest 30-day comparison window. Thus, target and label-source are related but distinct: is_declining_label is the binary estimator target; trend_direction is the observed category used to construct it.

Positive class 1 means the page has trend_direction equal to down in this export. It does not mean a future decline. The executed raw-data count is 16,262 positives and 13,738 negatives (54.2067% positive).

The computed count agrees with reports/eda_report.md and docs/data-dictionary.md. reports/capstone_report.md states 16,263 positives and 13,737 negatives; that historical passage differs by one row from the raw-data calculation and is not used here.

## 4. Data Contract

### Allowed estimator features

Feature selection reuses NUMERIC_FEATURES and CATEGORICAL_FEATURES in src/content_engine/config.py. The 40 candidate inputs are:

**Numeric (31):** search_volume, competition, cpc, word_count, char_count, content_age_days, days_since_last_update, impressions_90d, clicks_90d, pageviews_90d, sessions_90d, users_90d, engaged_sessions_90d, ai_sessions_90d, scroll_events_90d, days_with_impressions, days_with_sessions, ctr, avg_position, engagement_rate, scroll_rate, ai_traffic_pct, age_tier_order, log_impressions_90d, log_clicks_90d, log_sessions_90d, is_missing_position, is_missing_keyword_context, is_missing_word_count, engaged_session_ratio, click_to_session_ratio.

**Categorical (9):** competition_level, content_type, main_intent, age_tier, freshness_tier, word_count_tier, char_count_tier, impression_tier, position_tier.

provider_used and model_used are documented metadata but are not estimator features. content_id and client_id are identifiers, not features; client_id is retained only for group splitting.

### Restricted and quarantined fields

The nine restricted proprietary decision fields are health_score, needs_indexing, is_quick_win, needs_ctr_fix, needs_engagement_fix, ai_opportunity, is_underperformer, is_declining, and is_initial_refresh_candidate. They are quarantined because they are FlyRank decision outputs or composites that would contaminate discovery and could reveal existing product decisions.

The target and direct target-construction fields are excluded from estimator inputs: is_declining_label, impressions_last_30d, impressions_prev_30d, impressions_change_30d, trend_direction, and trend_pct. The feature-name audit also rejects last_30d, prev_30d, trend_pct, and trend_dir tokens, which keeps the other last/previous-window comparison fields out of the candidate set. The three future fields described in reports/leakage_audit.md are warehouse-only and absent from this starter slice.

### Missing values and preprocessing

The existing feature builder converts missing numeric candidate values to 0, except avg_position==0, which it treats as missing position and replaces with the median of positive avg_position values. It creates is_missing_position, is_missing_keyword_context, and is_missing_word_count indicators; it creates log1p traffic totals and derived ratios; categorical candidate nulls become the string unknown. The executed estimator matrix has no nulls.

The estimator ColumnTransformer applies StandardScaler to numeric features and OneHotEncoder(handle_unknown="ignore") to categorical features. The encoded design has 70 columns in the executed run.

### Evidence discrepancies preserved

- The raw CSV contains all nine restricted fields, while docs/DATA_USE.md says the product decision flags are not included. The executed notebook follows the raw data and quarantine code: it removes all nine fields before feature construction.
- reports/capstone_report.md describes 28 numeric and 12 categorical inputs plus median imputation. The active config selects 31 numeric and 9 categorical inputs; the feature builder fills numeric nulls with 0 except for the avg_position sentinel described above.
- reports/capstone_report.md describes the transparent baseline as the rule avg_position > 15 and content_age_days > 180. The active src/content_engine/models/baseline.py instead computes a weighted score: 0.40 visibility, 0.30 freshness, 0.20 position opportunity, and 0.10 content depth. docs/ml-intern-dataset-and-lane-guide.md documents different 0.25 / 0.05 weights for the last two components. This submission runs the active executable source utility.
- The feature builder computes click_to_session_ratio as sessions divided by clicks, clipped to 0–10. The capstone prose describes clicks divided by sessions. This submission preserves the source implementation for reproducibility and flags the name/definition mismatch as a limitation.

## 5. Leakage Controls

The model uses none of the nine restricted product-decision fields, identifiers, target column, direct target-construction fields, or future observations. The raw-file quarantine is checked against the exact documented 44-column schema after dropping the nine restricted fields.

Before modeling, the notebook calls the existing audit_feature_names utility on the actual 40 estimator input names. The audit passed with zero forbidden fields. The audit implementation checks restricted fields, identifiers, the target, target-construction columns, and forbidden name tokens. The same repository includes tests that assert these violations fail the audit.

The historical leakage report records a passed audit and zero violations. The Week 5 notebook independently reran the audit against the active feature lists and passed.

## 6. Validation Strategy

The existing client_aware_split utility shuffles unique client_id groups with random seed 42 and holds out 20% of clients. The execution reproduced the documented split:

- Training: 26 client groups, 26,619 rows, 14,487 positive rows.
- Holdout: 6 unseen client groups, 3,381 rows, 1,775 positive rows.
- Client-group overlap: 0.

Training client groups:

client_02d20bbd7e, client_434c9b5ae5, client_4ec9599fc2, client_f369cb89fc, client_3fdba35f04, client_d029fa3a95, client_8722616204, client_d59eced1de, client_e629fa6598, client_b4944c6ff0, client_4e07408562, client_7f2253d7e2, client_0b918943df, client_19581e27de, client_e29c9c180c, client_1a6562590e, client_25fc0e7096, client_98a3ab7c34, client_4fc82b26ae, client_624b60c58c, client_d4735e3a26, client_349c41201b, client_2c624232cd, client_bdd2d3af3a, client_f74efabef1, client_6208ef0f77.

Holdout client groups:

client_8b940be7fb, client_bbb965ab0c, client_9400f1b21c, client_a88a7902cb, client_8527a891e2, client_9f14025af0.

This split tests generalization to client groups absent from training and prevents within-client page overlap. It is not temporal validation. The forward 30-day target requires warehouse access and is documented as not yet run.

## 7. Models Evaluated

Four scorers were evaluated on the same holdout:

1. Transparent Baseline: the repository's weighted, deterministic ranking score.
2. Logistic Regression: max_iter=1000, random_state=42.
3. Random Forest: 100 trees, max_depth=12, random_state=42, n_jobs=-1.
4. Gradient Boosting: 100 estimators, max_depth=5, random_state=42.

The estimator definitions and evaluation utilities come from src/content_engine/models/train.py and src/content_engine/models/baseline.py. No separate Week 5 or ML-08 assignment brief was present in the repository; docs/GUIDE.md and docs/ml-intern-dataset-and-lane-guide.md say weekly assignment details live on the portal board. The results below are a fresh execution for this submission, not an assumption that the historical CHAMPION label was itself the Week 5 result.

The internship guide also documents a separate starter-pipeline experiment, including a Decision Tree. Its reference scripts, outputs, and work/ notebook skeletons are absent from this workspace, so those results are preserved below as guide-reported historical values and are not claimed as rerun results.

## 8. Results

All values below were calculated by executing the notebook against the local dataset and the documented holdout. They reproduce the values in reports/model_report.json and reports/model_report.md.

| Model | ROC-AUC | PR-AUC | Precision | Recall | F1 | P@20 | P@50 | P@100 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Transparent Baseline | 0.5938 | 0.5669 | 0.4600 | 0.0777 | 0.1330 | 0.3500 | 0.3600 | 0.3300 |
| Logistic Regression | 0.6510 | 0.6428 | 0.6109 | 0.7324 | 0.6662 | 0.7500 | 0.7000 | 0.7000 |
| Random Forest | 0.6617 | 0.6287 | 0.6095 | 0.7915 | 0.6887 | 0.4500 | 0.4400 | 0.4800 |
| Gradient Boosting | 0.6945 | 0.6791 | 0.6400 | 0.7470 | 0.6894 | 0.6000 | 0.6800 | 0.7200 |

Precision, Recall, and F1 use the existing evaluator's score threshold of 0.5. P@K is the share of positive labels among the top K holdout scores.

### Separate historical results documented in the internship guide

These figures are transcribed from docs/ml-intern-dataset-and-lane-guide.md. The guide calls the second column Average precision; it is kept under that name here. This is a different starter-pipeline benchmark and was not reproduced by the current executable code in this workspace.

| Historical method | ROC AUC | Average precision | P@50 |
|---|---:|---:|---:|
| Baseline rules | 0.627 | 0.468 | 0.240 |
| Logistic Regression | 0.700 | 0.522 | 0.400 |
| Decision Tree | 0.742 | 0.575 | 0.540 |
| Random Forest | 0.750 | 0.618 | 0.740 |

The current source benchmark above evaluates a different model set: transparent baseline, Logistic Regression, Random Forest, and Gradient Boosting. The guide's historical Decision Tree result is evidence of a past evaluation, not a model trained in this Week 5 notebook.

## 9. Interpretation

Gradient Boosting has the highest ROC-AUC, PR-AUC, and P@100. Logistic Regression has the highest P@20 and P@50. Therefore, the preferred model depends on the editorial queue size and the metric being optimized.

The repository trainer labels Gradient Boosting as its project-level champion by comparing its P@50 with Random Forest, then using PR-AUC as a tie-break. That selection logic does not compare Logistic Regression, which is higher at both P@20 and P@50. The existing CHAMPION label is historical/project-level and should not be presented as a Week 5-specific result or as a universal winner.

The notebook calculated these Gradient Boosting impurity importances from the fitted holdout run: days_with_impressions 0.3187, content_age_days 0.1791, avg_position 0.0871, ctr 0.0469, and scroll_rate 0.0411. These are model associations, not causal effects. The existing model and capstone reports label their feature-importance tables differently; the notebook reports the feature importances directly from the fitted estimator.

## 10. Limitations

- This is a current-window proxy: the label is built from observed comparison windows in the same export. It is not a future forecast.
- The holdout covers six of 32 client groups from one starter slice. It does not establish future-period or all-client performance.
- No independent Week 5/ML-08 portal rubric was present in the repository, so the notebook/report follow the user-provided requested deliverables and repository modeling contract.
- Source prose and code differ on restricted fields, preprocessing, the baseline description, a ratio definition, and one historical positive-class count. The executed notebook uses the active data and code paths and records those differences above.
- Feature importances and predicted scores do not prove causality or the impact of refreshing a page.

## 11. Reproducibility

Run notebooks/w05_model.ipynb from a Jupyter kernel opened within this repository. It uses the local data/raw/content_refresh_anonymized.csv, reads the feature lists and model utilities under src/content_engine, uses seed 42, and does not write model artifacts or generated reports. The notebook was run end-to-end locally; all nine code cells completed.

Environment used: Python 3.13.13, pandas 3.0.5, scikit-learn 1.9.1, matching the versions pinned in requirements.txt. No external downloads, credentials, URLs, or row-level page outputs were used by the notebook.

## 12. Files Created / Modified

Created for this assignment:

- notebooks/w05_model.ipynb — executed notebook, including verified outputs.
- submission/week5_capstone_modeling_report.md — this evidence-based report.

No existing dataset, source, report, backend, frontend, deployment, environment, or paper_url.txt file was modified for the assignment.

## 13. Final Submission Checklist

### DONE

- [x] Verified the raw schema and quarantined the nine restricted decision fields before feature construction.
- [x] Confirmed the target formula and positive-class counts directly from the data.
- [x] Reused the repository feature lists, preprocessing, client-group split, leakage audit, baseline, and metrics utilities.
- [x] Trained all three candidate models and evaluated the transparent baseline on the documented holdout.
- [x] Executed all notebook code cells and confirmed the report matches the calculated metrics.
- [x] Preserved historical results and documented source/report discrepancies.

### MISSING

- [ ] A Week 5 or ML-08 portal assignment brief/rubric. The repository points to the portal for weekly assignment details.
- [ ] The generic internship guides refer to work/notebooks/ and say not to create separate report files, while the supplied task requests notebooks/w05_model.ipynb and submission/week5_capstone_modeling_report.md. No work/ skeleton exists in this workspace, so the explicit paths in the supplied task were followed.

### NEEDS IMPLEMENTATION

- [x] Create the Week 5 notebook and submission report at the requested paths.
- [x] Execute the notebook and verify the report against its calculated results.

### DO NOT CHANGE

- Existing reports and historical results, starter datasets, feature/model source, APIs, frontend, deployment configuration, environment files, and the existing submission/paper_url.txt.

### Portal handoff

The repository guide says weekly assignments are submitted by providing the repository URL on the matching portal assignment card; it does not instruct students to upload the notebook or report separately. Push these two assignment files to the assigned repository, then submit that repository URL on the Week 5 card. The existing paper_url.txt is for the deployed capstone paper and was not changed.
