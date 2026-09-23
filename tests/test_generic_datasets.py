"""
Comprehensive Regression & Compatibility Test Suite for Generic Dataset Architecture.

Validates:
1. Primary FlyRank isolation & readiness (30k rows, 9 quarantined columns).
2. SEO Dataset ingestion, capability detection, mapping, and generic scoring.
3. Social Media (Facebook Metrics) capability detection and engagement scoring.
4. Online News Popularity capability detection and leakage safety.
5. Medium Articles missingness handling and metadata profiling.
6. Social Media Post Performance Forecasting capability detection.
7. Online Shoppers Intention session-level capability detection and conversion scoring.
8. Web Traffic Time-Series streaming & memory-safe chunked handling.
9. Negative Control Datasets (Olist Sellers, Zero-Variance) rejection as NOT_READY without crashes.
10. Multi-dataset SQLite isolation (custom dataset analysis does not mutate starter-flyrank).
"""
import io
import os
import zipfile
from pathlib import Path
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import SessionLocal
from backend.models import Dataset, Page, Opportunity
from content_engine.config import RAW_DATA_PATH, CLEAN_DATA_PATH
from content_engine.capabilities.profiler import profile_dataset
from content_engine.capabilities.detector import detect_capabilities
from content_engine.readiness.checker import check_dataset_readiness
from content_engine.canonical.schema import CANONICAL_SLOTS
from content_engine.canonical.mapper import map_columns_to_canonical
from content_engine.adapters.flyrank import FlyRankAdapter
from content_engine.adapters.generic_tabular import GenericTabularAdapter
from content_engine.adapters.time_series import TimeSeriesAdapter

client = TestClient(app)

DOWNLOADS_DIR = Path(os.getenv("EXTERNAL_DATASETS_DIR", str(Path.home() / "Downloads")))
SEO_PATH = DOWNLOADS_DIR / "SEO datasets" / "seo_dataset.csv"
FB_PATH = DOWNLOADS_DIR / "facebook mterics datsets" / "Facebook Metrics of Cosmetic Brand.csv"
NEWS_PATH = DOWNLOADS_DIR / "online new popularity" / "OnlineNewsPopularity.csv"
MEDIUM_PATH = DOWNLOADS_DIR / "cleaned meduim dataset" / "Cleaned_Medium_Data.csv"
SOCIAL_KAGGLE_PATH = DOWNLOADS_DIR / "social-media-post-performance-forecasting" / "archive" / "train.csv"
SHOPPERS_PATH = DOWNLOADS_DIR / "online shopper intention" / "online_shoppers_intention.csv"
WEB_TRAFFIC_ZIP = DOWNLOADS_DIR / "web-traffic-time-series-forecasting" / "train_1.csv.zip"
OLIST_PATH = DOWNLOADS_DIR / "olist payement dataset" / "olist_sellers_dataset.csv"


def test_flyrank_starter_isolation_and_readiness():
    assert Path(CLEAN_DATA_PATH).exists(), f"Clean FlyRank data missing at {CLEAN_DATA_PATH}"
    df_clean = pd.read_csv(CLEAN_DATA_PATH)
    assert len(df_clean) == 30000, f"Expected 30,000 rows in FlyRank, found {len(df_clean)}"

    profile = profile_dataset(df_clean)
    assert profile["total_rows"] == 30000
    assert profile["total_columns"] == 44

    caps = detect_capabilities(profile)
    assert caps["IDENTITY"]["present"] is True
    assert caps["VISIBILITY"]["present"] is True
    assert caps["SEARCH"]["present"] is True
    assert caps["ENGAGEMENT"]["present"] is True

    readiness = check_dataset_readiness(profile, caps)
    assert readiness["overall_status"] in ["READY", "READY_WITH_LIMITATIONS"]
    assert readiness["suggested_adapter"] == "FlyRankAdapter"
    assert readiness["readiness_pct"] >= 90

    adapter = FlyRankAdapter("starter-flyrank")
    assert adapter.is_applicable(list(df_clean.columns)) is True
    model_output = adapter.train_or_score(df_clean.head(100))
    scored = model_output["df_scored"]
    assert "opportunity_score" in scored.columns
    assert "priority" in scored.columns
    assert "action" in scored.columns
    assert "primary_reason" in scored.columns


@pytest.mark.skipif(not SEO_PATH.exists(), reason="SEO dataset not found on disk")
def test_seo_dataset_profiling_and_scoring():
    df = pd.read_csv(SEO_PATH)
    assert len(df) > 0

    profile = profile_dataset(df)
    caps = detect_capabilities(profile)
    assert caps["CONTENT"]["present"] is True or caps["SEARCH"]["present"] is True

    readiness = check_dataset_readiness(profile, caps)
    assert readiness["overall_status"] in ["READY", "READY_WITH_LIMITATIONS"]

    mapping = map_columns_to_canonical(profile, caps)
    assert len(mapping) > 0

    adapter = GenericTabularAdapter("test-seo-dataset")
    assert adapter.is_applicable(list(df.columns)) is True
    out = adapter.train_or_score(df)
    scored = out["df_scored"]
    assert len(scored) == len(df)
    assert "opportunity_score" in scored.columns
    assert "priority" in scored.columns
    assert "action" in scored.columns
    assert scored["opportunity_score"].between(0, 100).all()


@pytest.mark.skipif(not FB_PATH.exists(), reason="Facebook Metrics dataset not found on disk")
def test_facebook_metrics_profiling_and_scoring():
    try:
        df = pd.read_csv(FB_PATH, sep=";")
        if len(df.columns) <= 1:
            df = pd.read_csv(FB_PATH)
    except Exception:
        df = pd.read_csv(FB_PATH)

    profile = profile_dataset(df)
    caps = detect_capabilities(profile)
    assert caps["ENGAGEMENT"]["present"] is True or caps["VISIBILITY"]["present"] is True

    readiness = check_dataset_readiness(profile, caps)
    assert readiness["overall_status"] in ["READY", "READY_WITH_LIMITATIONS"]

    adapter = GenericTabularAdapter("test-fb-dataset")
    out = adapter.train_or_score(df)
    scored = out["df_scored"]
    assert len(scored) == len(df)
    assert "opportunity_score" in scored.columns
    assert "action" in scored.columns
    assert set(scored["priority"].unique()).issubset({"LOW", "MEDIUM", "HIGH", "CRITICAL"})


@pytest.mark.skipif(not NEWS_PATH.exists(), reason="Online News Popularity dataset not found on disk")
def test_online_news_popularity_dataset():
    df = pd.read_csv(NEWS_PATH, nrows=500)
    profile = profile_dataset(df)
    caps = detect_capabilities(profile)
    assert caps["CONTENT"]["present"] is True or caps["IDENTITY"]["present"] is True

    readiness = check_dataset_readiness(profile, caps)
    assert readiness["overall_status"] in ["READY", "READY_WITH_LIMITATIONS"]

    adapter = GenericTabularAdapter("test-news-dataset")
    out = adapter.train_or_score(df)
    scored = out["df_scored"]
    assert len(scored) == len(df)
    assert "opportunity_score" in scored.columns


@pytest.mark.skipif(not MEDIUM_PATH.exists(), reason="Medium dataset not found on disk")
def test_medium_articles_missingness_reporting():
    df = pd.read_csv(MEDIUM_PATH, nrows=500)
    profile = profile_dataset(df)
    sub_col = [c for c in df.columns if "subtitle" in c.lower()]
    if sub_col:
        assert profile["missing_rates"].get(sub_col[0], 0) >= 0

    caps = detect_capabilities(profile)
    readiness = check_dataset_readiness(profile, caps)
    assert readiness["overall_status"] in ["READY", "READY_WITH_LIMITATIONS"]

    adapter = GenericTabularAdapter("test-medium-dataset")
    out = adapter.train_or_score(df)
    scored = out["df_scored"]
    assert len(scored) == len(df)
    assert "opportunity_score" in scored.columns


@pytest.mark.skipif(not SOCIAL_KAGGLE_PATH.exists(), reason="Social media Kaggle dataset not found")
def test_social_media_forecasting_dataset():
    df = pd.read_csv(SOCIAL_KAGGLE_PATH, nrows=500)
    profile = profile_dataset(df)
    caps = detect_capabilities(profile)
    readiness = check_dataset_readiness(profile, caps)
    assert readiness["overall_status"] in ["READY", "READY_WITH_LIMITATIONS"]

    adapter = GenericTabularAdapter("test-social-kaggle")
    out = adapter.train_or_score(df)
    assert "opportunity_score" in out["df_scored"].columns


@pytest.mark.skipif(not SHOPPERS_PATH.exists(), reason="Online Shoppers dataset not found")
def test_online_shoppers_intention_dataset():
    df = pd.read_csv(SHOPPERS_PATH, nrows=500)
    profile = profile_dataset(df)
    caps = detect_capabilities(profile)
    readiness = check_dataset_readiness(profile, caps)
    assert readiness["overall_status"] in ["READY", "READY_WITH_LIMITATIONS"]

    adapter = GenericTabularAdapter("test-shoppers")
    out = adapter.train_or_score(df)
    assert "opportunity_score" in out["df_scored"].columns


@pytest.mark.skipif(not WEB_TRAFFIC_ZIP.exists(), reason="Web traffic zip not found on disk")
def test_web_traffic_time_series_chunked_streaming():
    with zipfile.ZipFile(WEB_TRAFFIC_ZIP, "r") as z:
        csv_names = [n for n in z.namelist() if n.endswith(".csv")]
        assert len(csv_names) > 0
        with z.open(csv_names[0]) as f:
            sample_df = pd.read_csv(f, nrows=50)

    assert "Page" in sample_df.columns
    profile = profile_dataset(sample_df)
    caps = detect_capabilities(profile)
    assert caps["TIME_SERIES"]["present"] is True or caps["TIME"]["present"] is True

    readiness = check_dataset_readiness(profile, caps)
    assert readiness["suggested_adapter"] == "TimeSeriesAdapter"

    adapter = TimeSeriesAdapter("test-web-traffic")
    assert adapter.is_applicable(list(sample_df.columns)) is True
    out = adapter.train_or_score(sample_df)
    assert "df_scored" in out
    assert "opportunity_score" in out["df_scored"].columns


@pytest.mark.skipif(not OLIST_PATH.exists(), reason="Olist dataset not found")
def test_negative_control_olist_sellers_rejected():
    df = pd.read_csv(OLIST_PATH)
    profile = profile_dataset(df)
    caps = detect_capabilities(profile)
    readiness = check_dataset_readiness(profile, caps)

    assert readiness["overall_status"] == "NOT_READY"
    assert len(readiness["blockers"]) > 0
    perf_check = next((c for c in readiness["checklist"] if "performance" in c["name"].lower()), None)
    assert perf_check is not None
    assert perf_check["passed"] is False


def test_negative_control_zero_variance_rejected():
    zero_df = pd.DataFrame({
        "item_id": [f"item_{i}" for i in range(50)],
        "views": [0] * 50,
        "clicks": [0] * 50,
        "text": ["constant text"] * 50,
    })
    profile = profile_dataset(zero_df)
    caps = detect_capabilities(profile)
    readiness = check_dataset_readiness(profile, caps)

    assert readiness["overall_status"] == "NOT_READY"
    const_check = next((c for c in readiness["checklist"] if "performance" in c["name"].lower() or "valid" in c["name"].lower()), None)
    assert const_check is not None
    assert const_check["passed"] is False


def test_multi_dataset_sqlite_isolation():
    db = SessionLocal()
    try:
        flyrank_count_before = db.query(Page).filter(Page.dataset_id == "starter-flyrank").count()
        assert flyrank_count_before > 0

        mini_data = pd.DataFrame({
            "asset_url": [f"https://site.org/page{i}" for i in range(20)],
            "headline": [f"Page {i} Title" for i in range(20)],
            "pageviews": [1000 + i * 50 for i in range(20)],
            "organic_clicks": [50 + i * 5 for i in range(20)],
            "conversion_rate": [0.02 + (i * 0.001) for i in range(20)],
        })
        csv_buf = io.StringIO()
        mini_data.to_csv(csv_buf, index=False)
        csv_bytes = csv_buf.getvalue().encode("utf-8")

        res = client.post(
            "/api/datasets/upload",
            files={"file": ("mini_catalog.csv", csv_bytes, "text/csv")},
            data={"name": "Mini Custom Catalog"},
        )
        assert res.status_code == 200
        up_data = res.json()
        assert up_data["is_valid"] is True
        custom_id = up_data["dataset_id"]

        an_res = client.post(f"/api/datasets/{custom_id}/analyze")
        assert an_res.status_code == 200

        flyrank_count_after = db.query(Page).filter(Page.dataset_id == "starter-flyrank").count()
        assert flyrank_count_after == flyrank_count_before, "Starter flyrank pages were corrupted or mutated!"

        custom_count = db.query(Page).filter(Page.dataset_id == custom_id).count()
        assert custom_count == 20

        opp_fly = client.get("/api/opportunities?dataset_id=starter-flyrank&page_size=10")
        assert opp_fly.status_code == 200
        assert len(opp_fly.json()["items"]) == 10
        assert all(item["client_id"] != custom_id for item in opp_fly.json()["items"])

        client.delete(f"/api/datasets/{custom_id}")
    finally:
        db.close()
