# Content Intelligence Engine: Data-Driven Editorial Decision Support System
**Turning Search & Engagement Telemetry into Prioritized Editorial Interventions**

---

## 1. Executive Summary & Abstract

Digital publishing, SEO agencies, and enterprise content teams produce thousands of articles, landing pages, and guides. However, editorial teams face an acute operational bottleneck: **editorial bandwidth is finite**. When managing portfolios ranging from 5,000 to over 100,000 URLs, editors cannot review every page monthly. Instead, they require a reliable, evidence-backed answer to a core operational question:

> **"Which pages should our content team REVIEW FIRST, and WHY?"**

Heuristic-based ranking (e.g., sorting descending by traffic drop or page age) fails because:
1. High-traffic pages that drop by a small percentage consume all attention while mid-tier pages with high elastic upside are ignored.
2. Low-traffic tail pages with seasonal or zero baseline demand trigger false alarms.
3. Proprietary aggregated "health scores" obscure the exact drivers of performance change, leaving editors without actionable next steps.

The **Content Intelligence Engine** is an end-to-end Machine Learning and SaaS platform designed to solve this prioritization dilemma. Trained on a curated multi-tenant dataset of **30,000 web pages across 32 clients**, the engine enforces:
- **Zero target-construction leakage**: Strict mathematical separation between features and the target label.
- **Client-group holdout validation**: Training on 26 enterprise clients (26,619 pages) and testing strictly on 6 unseen clients (3,381 pages) to measure cross-domain generalization.
- **Operational decision metrics (Precision@K)**: Prioritizing Precision@20, Precision@50, and Precision@100 to mirror editorial workflow constraints.
- **Explainable Opportunity Scoring (0–100)**: Combining model decay probability, traffic volume, position opportunity, and freshness decay into an actionable ranking, accompanied by structured reason codes and prescriptive action directives (`REFRESH`, `OPTIMIZE`, `PROTECT`, `INVESTIGATE`, `MONITOR`, `MERGE`, `REWRITE`).
- **Production Architecture**: A FastAPI REST backend with SQLite persistence (PostgreSQL-ready), JWT authentication, a grounded AI assistant with query planning, and a modern Next.js 14 web interface.

---

## 2. Problem Formulation & Research Question

### 2.1 The Editorial Resource Allocation Problem
Content decay is inevitable. Search intent evolves, competitors publish fresher analysis, and search engine ranking algorithms recalibrate. However, editorial intervention—updating content, rewriting headlines, adding internal links, or consolidating thin pages—is labor-intensive. 

If an editorial team has the capacity to review **50 pages per week**, traditional analytics platforms provide little guidance:
- Standard Google Search Console (GSC) exports present disconnected tables of queries and pages without consolidated decay probabilities.
- Aggregate SEO scores hide whether a decline is driven by ranking loss, click-through underperformance, or seasonal impressions drops.
- Human review of random samples yields low hit rates, wasting specialist hours on pages that do not require intervention.

### 2.2 Research Question
*Can a machine learning model, trained strictly on pre-intervention 90-day search performance, content taxonomy, and engagement telemetry, reliably predict which pages are in performance decay when evaluated on entirely unseen client domains, thereby maximizing the precision of the top-ranked editorial review queue?*

---

## 3. Dataset Architecture & Quarantine Guardrails

### 3.1 Raw Data Schema (44 Documented Columns)
The input dataset consists of **30,000 rows** spanning 32 client tenants. The data schema comprises four primary categories:
1. **Identifiers & Metadata**: `url`, `client_id`, `site_domain`, `brand_or_nonbrand`, `language`, `url_depth`, `is_core_page`.
2. **Taxonomy & Content Attributes**: `content_type`, `primary_category`, `word_count`, `char_count`, `content_age_days`, `days_since_last_update`, `main_intent`, `freshness_tier`, `word_count_tier`.
3. **90-Day Trailing Telemetry**: `impressions_90d`, `clicks_90d`, `ctr`, `avg_position`, `sessions_90d`, `users_90d`, `pageviews_90d`, `bounce_rate`, `engagement_rate`, `avg_time_on_page`, `scroll_rate`, `days_with_impressions`, `days_with_sessions`.
4. **30-Day Transition Indicators & Target Fields**: `impressions_last_30d`, `impressions_prev_30d`, `impressions_change_30d`, `trend_pct`, `trend_direction`.

### 3.2 The 9 Quarantined Columns & Anti-Leakage Defense
A critical vulnerability in real-world ML implementations is the accidental incorporation of proprietary platform aggregates or upstream target proxies. In our raw ingestion pipeline, 9 columns were identified as proprietary FlyRank calculated metrics:
- `health_score`
- `needs_indexing`
- `is_quick_win`
- `needs_ctr_fix`
- `needs_engagement_fix`
- `ai_opportunity`
- `is_underperformer`
- `is_declining`
- `is_initial_refresh_candidate`

**Quarantine Decision**: All 9 columns were **strictly isolated** from model features. Because columns like `is_declining` and `health_score` are downstream labels or proprietary composite outputs, allowing them into the feature vector would create catastrophic data contamination, rendering the model trivial in training and useless in production.

### 3.3 Data Cleaning, Anomaly Handling, and Distribution
- **Zero-Variance & Constants**: Checked across all 30,000 rows. No constant features were detected.
- **Negative Value Validation**: Absolute numeric checks confirmed no negative impressions, clicks, sessions, or word counts.
- **Null Imputation Strategy**:
  - `avg_position`: Missing on unranked or non-indexed pages (2.7% of corpus). Imputed with sentinel value `100.0`, paired with a dedicated boolean indicator `is_missing_position`.
  - Engagement metrics (`bounce_rate`, `engagement_rate`, `scroll_rate`, `avg_time_on_page`): Missing when zero sessions were recorded. Imputed with median values and accompanied by `is_missing_engagement`.

---

## 4. Target Formulation & Mathematical Integrity

### 4.1 Starter Proxy Target Definition
In the absence of multi-year daily event-level warehouse time series, the production baseline utilizes a **transparent, verified proxy label**:
$$\text{is\_declining\_label} = \mathbb{I}(\text{trend\_direction} == \text{'down'})$$

- **Target Type**: Current-window proxy baseline.
- **Corpus Target Balance**:
  - Positive Class (Down / Decayed): 16,263 pages (**54.21%**)
  - Negative Class (Flat / Up / Stable): 13,737 pages (**45.79%**)
- **Client Group Split Target Distribution**:
  - Train Set (26 clients, 26,619 pages): 14,488 positive (**54.43%**)
  - Holdout Test Set (6 clients, 3,381 pages): 1,775 positive (**52.50%**)

### 4.2 Future-Window Extension Architecture
The platform explicitly defines the requirements for a future-window operational model:
- **Status**: *"Not yet run — requires warehouse access."*
- **Requirements**: Requires partitioned daily GSC tables where features are extracted from days t_{-90} to t_0, and the target is calculated over forward horizon t_1 to t_{30}.
- **Transparency Guarantee**: The system avoids claiming future-period forecasting on single-snapshot data.

---

## 5. Feature Engineering & 6-Tier Leakage Audit

### 5.1 Safe Derived Feature Engineering
To provide non-linear signals without introducing leakage, safe derived features were constructed:
1. **Log Volume Normalization**: `log_impressions_90d`, `log_clicks_90d`, `log_sessions_90d` using ln(1 + x) to handle extreme long-tail power law distributions.
2. **Behavioral Ratios**:
   - `click_to_session_ratio`: clicks_90d / max(sessions_90d, 1.0)
   - `impressions_per_day_active`: impressions_90d / max(days_with_impressions, 1.0)
3. **Missingness Encodings**: `is_missing_position`, `is_missing_engagement`.

### 5.2 6-Tier Leakage Classification Audit
A formal leakage audit categorized all 40 candidate input features into 6 distinct integrity tiers:
- **Tier 1 (Safe Pre-Intervention)**: Trailing 90-day search aggregates (`impressions_90d`, `clicks_90d`, `avg_position`, `ctr`, etc.).
- **Tier 2 (Safe Metadata & Taxonomy)**: URL depth, content age, word count, character count, language, brand vs. non-brand, categories.
- **Tier 3 (Safe Derived Telemetry)**: Log transforms, missingness indicators, behavioral ratios.
- **Tier 4 (Forbidden Target Construction)**: `impressions_last_30d`, `impressions_prev_30d`, `impressions_change_30d`, `trend_direction`, `trend_pct`. **Result: 100% Excluded.**
- **Tier 5 (Forbidden Proprietary Targets)**: The 9 quarantined FlyRank columns. **Result: 100% Excluded.**
- **Tier 6 (Forbidden Post-Intervention / Future Features)**: Any future session or conversion telemetry. **Result: None present.**

The automated audit passed with **40 approved features**, 0 leakage violations, and 0 quarantined columns admitted.

---

## 6. Model Training, Validation & Evaluation

### 6.1 Validation Strategy: Client-Group Holdout
To prevent cross-page domain memorization, validation was structured on a **Client Group Holdout** basis:
- 32 total clients.
- **Train Set**: 26 clients, 26,619 rows.
- **Test Set**: 6 completely disjoint clients (`client_8b940be7fb`, `client_bbb965ab0c`, `client_9400f1b21c`, `client_a88a7902cb`, `client_8527a891e2`, `client_9f14025af0`), 3,381 rows.

### 6.2 Preprocessing Pipelines
- **Numeric Features (28)**: Median imputation followed by standard scaling (`StandardScaler`).
- **Categorical Features (12)**: Constant `"unknown"` imputation followed by one-hot encoding (`OneHotEncoder(handle_unknown='ignore')`).
- Total transformed feature dimensionality: **70 features**.

### 6.3 Comprehensive Model Benchmark Results

| Model Pipeline | ROC-AUC | PR-AUC | Accuracy | Precision | Recall | F1 Score | P@20 | P@50 | P@100 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Transparent Heuristic Baseline** | 0.5938 | 0.5669 | 0.4679 | 0.4600 | 0.0777 | 0.1330 | 0.3500 | 0.3600 | 0.3300 |
| **Logistic Regression (L2)** | 0.6510 | 0.6428 | 0.6146 | 0.6109 | 0.7324 | 0.6662 | **0.7500** | 0.7000 | 0.7000 |
| **Random Forest (100 Trees)** | 0.6617 | 0.6287 | 0.6244 | 0.6095 | **0.7915** | 0.6887 | 0.4500 | 0.4400 | 0.4800 |
| **Gradient Boosting (Champion)** | **0.6945** | **0.6791** | **0.6466** | **0.6400** | 0.7470 | **0.6894** | 0.6000 | **0.6800** | **0.7200** |

*Note: Baseline heuristic flags pages where avg_position > 15.0 AND content_age_days > 180.*

### 6.4 Champion Selection Rationale
**Gradient Boosting Classifier** was selected as the production champion:
1. **Superior Global Discrimination**: Highest ROC-AUC (**0.6945**) and PR-AUC (**0.6791**) on unseen client domains.
2. **Highest Deep Precision@K**: Achieved **0.7200 (72%)** on the top 100 queue and **0.6800 (68%)** on the top 50 queue.
3. **Editorial Viability**: When editors work through a monthly backlog of 50 to 100 pages, the Gradient Boosting pipeline ensures that 7 out of 10 pages flagged are genuine performance decay candidates—more than double the precision of heuristic baselines (33%).

---

## 7. Model Interpretability & Feature Attributions

### 7.1 Global Feature Importances (Random Forest)
1. `days_with_impressions` (0.0859): Regularity of search visibility is the strongest leading indicator of stability.
2. `log_impressions_90d` / `impressions_90d` (0.0840): Total search volume establishes page scale.
3. `content_age_days` (0.0726): Content older than 180 days experiences natural decay without active refresh.
4. `avg_position` (0.0617): Deep ranking positions (page 2+) correlate heavily with traffic drops.
5. `word_count` (0.0394) & `char_count` (0.0359): Comprehensive content resists decay better than thin content.

### 7.2 Linear Model Directional Coefficients (Logistic Regression)
- **Positive Decay Drivers** (+ coefficient = higher probability of decline):
  - `log_impressions_90d` (+1.1779): High-impression pages have higher statistical exposure to downward variance.
  - `freshness_tier_181+` (+0.7285): Stale content older than 6 months exhibits strong positive decay coefficient.
  - `word_count_tier_1000-2000` (+0.6570): Mid-length competitive articles face aggressive SERP churn.
- **Protective Factors** (- coefficient = lower probability of decline):
  - `users_90d` (-0.8043): Diverse user sessions buffer against pure search volatility.
  - `freshness_tier_31-90` (-0.6373): Recently published or updated content retains momentum.
  - `log_clicks_90d` (-0.6759): Established click volume signals search satisfaction and ranking durability.

### 7.3 Local Explainability & Non-Causal Grounding
The engine provides local feature attributions for individual URLs using normalized feature deviations from domain baselines.
> **Critical Scientific Caveat**: Local attributions reflect *statistical association within the model*, not physical causality. The model indicates which features pushed the decay probability higher; it does not claim that changing word count alone guarantees ranking recovery.

---

## 8. Opportunity Scoring & Action Recommendation Engine

### 8.1 The Opportunity Score Formulation (0–100)
A raw ML probability of decline is insufficient for editorial action: a page with 10 impressions that is decaying is trivial, whereas a flagship page with 50,000 impressions losing rank requires urgent review.

The **Opportunity Score** ($OS \in [0, 100]$) combines decay probability with commercial leverage and position elasticity:
$$OS = 	ext{clip}\left( 100 	imes \left( 0.40 \cdot \hat{p}_{	ext{decay}} + 0.25 \cdot 	ext{Vol}_{	ext{norm}} + 0.20 \cdot 	ext{Pos}_{	ext{elasticity}} + 0.15 \cdot 	ext{Decay}_{	ext{age}} ight), 0, 100 ight)$$

Where:
- $\hat{p}_{	ext{decay}}$: Calibrated probability of decline from the Gradient Boosting model.
- $	ext{Vol}_{	ext{norm}} = rac{\ln(1 + 	ext{impressions\_90d})}{\ln(1 + 	ext{max\_impressions})}$: Log-scaled search visibility.
- $	ext{Pos}_{	ext{elasticity}}$: Position sweet-spot factor (highest for positions 4.0–15.0 where incremental gains yield maximum CTR increases).
- $	ext{Decay}_{	ext{age}} = \min\left(rac{	ext{days\_since\_last\_update}}{365}, 1.0ight)$: Freshness stagnation index.

### 8.2 Evidence-Based Action Framework
Every page in the catalog is assigned a primary action directive based on deterministic logic over model outputs and observable metrics:

1. **REFRESH**: High opportunity score ($OS \ge 65$) on aging content ($	ext{days} > 180$) with proven historical impressions. Directive: Update factual claims, refresh metadata, expand current analysis.
2. **OPTIMIZE**: High impressions ($\ge 5,000$) but below-benchmark CTR ($	ext{CTR} < 1.5\%$) ranking on page 1 or 2 ($	ext{position} \le 15$). Directive: Rewrite title tags, improve meta descriptions, structure rich snippets.
3. **PROTECT**: High-traffic flagship pages ($OS < 45$, high impressions, strong rank) showing early signs of vulnerability. Directive: Maintain internal link equity, verify technical performance, monitor competitor moves.
4. **INVESTIGATE**: Significant engagement or position drops without clear taxonomy attribution. Directive: Audit search intent mismatch, check for page speed degradation or cannibalization.
5. **MERGE**: High URL depth ($\ge 3$), thin content, and declining impressions. Directive: 301 redirect and consolidate into a relevant topic pillar.
6. **REWRITE**: Core landing pages with high bounce rates ($\ge 75\%$) and low dwell time. Directive: Restructure layout, elevate core value proposition, improve readability.
7. **MONITOR**: Healthy or emerging content demonstrating steady velocity. Directive: Observe without intervention.

---

## 9. Content Performance Archetypes (Clustering)

To provide portfolio-level visibility across 30,000 URLs, an unsupervised **K-Means Clustering** ($k=6$) was trained on standardized behavioral features (`log_impressions_90d`, `log_clicks_90d`, `ctr`, `avg_position`, `days_since_last_update`, `engagement_rate`, `scroll_rate`):

| Cluster | Archetype Name | Page Count | Share | Typical Profile | Recommended Directive |
| :---: | :--- | :---: | :---: | :--- | :---: |
| **0** | **High Performers** | 5,942 | 19.8% | Median 700 impressions, Pos 14.7, stable traffic | `PROTECT` |
| **1** | **Declining Winners** | 3,090 | 10.3% | Median Pos 9.0, low recent CTR, decaying trajectory | `REFRESH` |
| **2** | **High Visibility / Low CTR** | 7,942 | 26.5% | Median 8,426 impressions, Pos 8.4, CTR 0.29% | `OPTIMIZE` |
| **3** | **Growing Content** | 483 | 1.6% | Median Pos 11.4, high engagement (50%), upward trend | `MONITOR` |
| **4** | **Stagnant Content** | 143 | 0.5% | Deep positions, stagnant updates, minimal clicks | `REFRESH` |
| **5** | **Low Visibility / Tail** | 12,400 | 41.3% | Median 287 impressions, Pos 12.5, long-tail URLs | `INVESTIGATE` |

*Interpretability Guardrail: These clusters group observable search patterns; they do not represent semantic topic clusters because raw text is not present in the tabular schema.*

---

## 10. System Architecture & Engineering Implementation

### 10.1 Technical Stack
- **Machine Learning Core**: Python 3.13, scikit-learn 1.9.1, NumPy 2.5.3, Pandas 3.0.5, SciPy 1.18.1, Joblib.
- **Backend API**: FastAPI 0.141.1, Uvicorn, Pydantic v2, SQLAlchemy 2.0.54, SQLite (production PostgreSQL compatible).
- **Authentication**: JWT tokens (HMAC-SHA256) via `python-jose`, password hashing with `bcrypt`.
- **Frontend Application**: Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Lucide Icons.
- **Testing & Verification**: Pytest 9.1.1, HTTPX test client.

### 10.2 Production Performance Optimizations
1. **In-Memory Pipeline Caching**: Deserializing a 70-feature scikit-learn pipeline from disk takes ~3,000ms on Windows filesystems. An in-memory cache (`_CACHED_PIPELINE`) was implemented in `explain.py`, reducing per-request scoring latency to **< 5 milliseconds**.
2. **Categorical Type Guards**: Implemented explicit string type coercion for missing categorical parameters in the explainability endpoint, preventing `OneHotEncoder` type collisions.
3. **Database Indexing**: Indexes applied to `(client_id, opportunity_score DESC)`, `(url)`, and `(recommended_action)` across the 30,000-row table, enabling sub-15ms filtered API responses.

---

## 11. Grounded AI Assistant with Guardrails

The system integrates an AI query and insights adapter (`backend/ai_assistant.py`) designed with strict **anti-hallucination guardrails**:
1. **Schema Grounding**: The assistant receives strict database schema context and cannot hallucinate columns not present in the documented 44-column specification.
2. **Evidence-Based Answers**: All numbers, counts, and URLs returned in the assistant interface are grounded in SQL query results against the live database.
3. **Structured Query Planning**: For operational queries (e.g., *"Show me top 5 decaying pages in education category"*), the assistant parses intent into deterministic filter parameters, queries the database, and summarizes the exact matching records.

---

## 12. Limitations & Future Roadmap

### 12.1 Current Operational Limitations
1. **Single-Snapshot Proxy Target**: While mathematically isolated from features, the proxy target `trend_direction == 'down'` represents a historical state rather than a forward 30-day forecast.
2. **Absence of Full Text**: The dataset provides character and word counts, but lacks full HTML body copy, preventing lexical keyword density or semantic embedding analysis.
3. **No External Backlink / SERP Dynamics**: Search rankings are influenced by competitor publications and domain authority, which are outside the trailing telemetry schema.

### 12.2 Production Warehouse Roadmap
1. **Forward 30-Day Transition Models**: Connect directly to Snowflake / BigQuery daily GSC export tables to train true t_{-90} -> t_{+30} forward-looking transition models.
2. **Automated CMS Webhooks**: Connect action directives directly to WordPress, Contentful, or Webflow APIs to automatically create draft refresh tickets for editors.
3. **Continuous Real-Time A/B Testing**: Track refreshed URLs post-intervention to quantify actual traffic recovery lift against an unedited control cohort.

---

## 13. Conclusion
The **Content Intelligence Engine** transforms search analytics from retrospective reporting into a forward-looking decision engine. By uniting rigorous zero-leakage ML engineering with an editorial-first prioritization framework, the platform delivers a verified **72% Precision@100** on unseen client domains, maximizing the impact of every editorial hour invested.\n