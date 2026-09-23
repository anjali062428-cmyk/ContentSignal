"""
Central Configuration for Content Intelligence Engine.
Defines documented columns, quarantined columns, target construction columns,
candidate feature sets, and operational thresholds.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_PATH = DATA_DIR / "raw" / "content_refresh_anonymized.csv"
CLEAN_DATA_PATH = DATA_DIR / "processed" / "clean_44_documented.csv"
FEATURE_VECTOR_PATH = DATA_DIR / "processed" / "feature_vector.csv"
OPPORTUNITIES_PATH = DATA_DIR / "processed" / "opportunities.csv"
REPORTS_DIR = BASE_DIR / "reports"

DOCUMENTED_44_COLUMNS = [
    "content_id", "client_id", "search_volume", "competition", "competition_level",
    "cpc", "content_type", "main_intent", "word_count", "char_count",
    "provider_used", "model_used", "content_age_days", "days_since_last_update",
    "impressions_90d", "clicks_90d", "pageviews_90d", "sessions_90d", "users_90d",
    "engaged_sessions_90d", "ai_sessions_90d", "scroll_events_90d",
    "days_with_impressions", "days_with_sessions", "impressions_last_30d",
    "clicks_last_30d", "sessions_last_30d", "impressions_prev_30d",
    "clicks_prev_30d", "sessions_prev_30d", "ctr", "avg_position",
    "engagement_rate", "scroll_rate", "ai_traffic_pct", "trend_pct",
    "age_tier", "age_tier_order", "freshness_tier", "word_count_tier",
    "char_count_tier", "impression_tier", "position_tier", "trend_direction"
]

RESTRICTED_FLYRANK_COLUMNS = [
    "health_score", "needs_indexing", "is_quick_win", "needs_ctr_fix",
    "needs_engagement_fix", "ai_opportunity", "is_underperformer",
    "is_declining", "is_initial_refresh_candidate"
]

OPTIONAL_PAGE_INTELLIGENCE_COLUMNS = [
    "domain", "url", "page_title", "page_type", "page_type_source"
]

IDENTIFIER_COLUMNS = ["content_id", "client_id"]
TARGET_COLUMN = "is_declining_label"

FORBIDDEN_LEAKAGE_COLUMNS = [
    "impressions_last_30d", "impressions_prev_30d", "impressions_change_30d",
    "trend_direction", "trend_pct", "is_declining_label"
]

METADATA_EXCLUDED_COLUMNS = ["provider_used", "model_used"]

NUMERIC_FEATURES = [
    "search_volume", "competition", "cpc", "word_count", "char_count",
    "content_age_days", "days_since_last_update", "impressions_90d", "clicks_90d",
    "pageviews_90d", "sessions_90d", "users_90d", "engaged_sessions_90d",
    "ai_sessions_90d", "scroll_events_90d", "days_with_impressions",
    "days_with_sessions", "ctr", "avg_position", "engagement_rate",
    "scroll_rate", "ai_traffic_pct", "age_tier_order",
    "log_impressions_90d", "log_clicks_90d", "log_sessions_90d",
    "is_missing_position", "is_missing_keyword_context", "is_missing_word_count",
    "engaged_session_ratio", "click_to_session_ratio"
]

CATEGORICAL_FEATURES = [
    "competition_level", "content_type", "main_intent", "age_tier",
    "freshness_tier", "word_count_tier", "char_count_tier",
    "impression_tier", "position_tier"
]

PRIORITY_THRESHOLDS = {
    "LOW": (0, 30),
    "MEDIUM": (31, 60),
    "HIGH": (61, 80),
    "CRITICAL": (81, 100),
}

RANDOM_SEED = 42
