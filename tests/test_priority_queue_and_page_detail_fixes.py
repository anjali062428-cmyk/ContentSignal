"""
Regression and Verification Tests for Priority Queue and Page Detail Fixes.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_mark_action_taken_custom_dataset_raw_and_prefixed():
    # Test 1: Raw page ID P174
    res1 = client.post("/api/impact/mark", json={
        "page_id": "P174",
        "dataset_id": "ds_57c9285d26",
        "action_type": "REFRESH",
        "notes": "Test manual refresh for raw P174"
    })
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["page_id"] == "ds_57c9285d26_P174"
    assert data1["dataset_id"] == "ds_57c9285d26"
    assert data1["action_type"] == "REFRESH"
    assert data1["status"] == "COMPLETED"
    assert "impressions_90d" in data1["before_metrics"]
    assert data1["before_metrics"]["impressions_90d"] > 0

    # Test 2: Prefixed page ID ds_57c9285d26_P174
    res2 = client.post("/api/impact/mark", json={
        "page_id": "ds_57c9285d26_P174",
        "dataset_id": "ds_57c9285d26",
        "action_type": "OPTIMIZE",
        "notes": "Test manual optimize for prefixed ID"
    })
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["page_id"] == "ds_57c9285d26_P174"
    assert data2["action_type"] == "OPTIMIZE"

    # Test 3: GET impact actions by raw ID
    get_res1 = client.get("/api/impact/P174?dataset_id=ds_57c9285d26")
    assert get_res1.status_code == 200
    actions1 = get_res1.json()
    assert len(actions1) >= 2

    # Test 4: GET impact actions by prefixed ID
    get_res2 = client.get("/api/impact/ds_57c9285d26_P174?dataset_id=ds_57c9285d26")
    assert get_res2.status_code == 200
    actions2 = get_res2.json()
    assert len(actions2) >= 2


def test_mark_action_taken_invalid_page_returns_404():
    res = client.post("/api/impact/mark", json={
        "page_id": "NON_EXISTENT_PAGE_XYZ_999",
        "dataset_id": "ds_57c9285d26",
        "action_type": "REFRESH"
    })
    assert res.status_code == 404
    data = res.json()
    assert "detail" in data
    assert "was not found in dataset" in data["detail"]


def test_mark_action_taken_flyrank_starter_backward_compatible():
    # Fetch first FlyRank page ID
    opp_res = client.get("/api/opportunities?dataset_id=starter-flyrank&page=1&page_size=1")
    assert opp_res.status_code == 200
    items = opp_res.json()["items"]
    assert len(items) > 0
    flyrank_page_id = items[0]["page_id"]

    res = client.post("/api/impact/mark", json={
        "page_id": flyrank_page_id,
        "dataset_id": "starter-flyrank",
        "action_type": "REFRESH",
        "notes": "Starter regression verification"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["page_id"] == flyrank_page_id
    assert data["dataset_id"] == "starter-flyrank"
    assert "before_metrics" in data
    assert data["before_metrics"]["impressions_90d"] >= 0


def test_page_intelligence_comparison_30d_shapes():
    # Test custom dataset page ds_57c9285d26_P149
    res = client.get("/api/opportunities/ds_57c9285d26_P149")
    assert res.status_code == 200
    data = res.json()
    assert data["page_id"] == "ds_57c9285d26_P149"
    assert data["dataset_id"] == "ds_57c9285d26"
    assert "comparison_30d" in data
    c30 = data["comparison_30d"]
    assert "recent_clicks" in c30
    assert "prev_clicks" in c30
    assert "clicks_delta_pct" in c30
    assert "recent_impressions" in c30
    assert "prev_impressions" in c30
    assert "recent_ctr" in c30
    assert "prev_ctr" in c30
    assert "has_comparison_data" in c30
    assert "data_sufficiency" in c30

    # Test raw P149 resolution
    res_raw = client.get("/api/opportunities/P149")
    assert res_raw.status_code == 200
    data_raw = res_raw.json()
    assert data_raw["page_id"] == "ds_57c9285d26_P149"


def test_priority_queue_filters_status_and_confidence():
    # Filter by status REVIEW on custom dataset
    res_status = client.get("/api/opportunities?dataset_id=ds_57c9285d26&status=REVIEW")
    assert res_status.status_code == 200
    data_status = res_status.json()
    assert len(data_status["items"]) > 0
    for item in data_status["items"]:
        assert item["content_status"] == "REVIEW"

    # Filter by status REFRESH NOW on starter-flyrank
    res_fly_status = client.get("/api/opportunities?dataset_id=starter-flyrank&status=REFRESH+NOW")
    assert res_fly_status.status_code == 200
    data_fly_status = res_fly_status.json()
    assert len(data_fly_status["items"]) > 0
    for item in data_fly_status["items"]:
        assert item["content_status"] == "REFRESH NOW"

    # Filter by confidence HIGH
    res_conf = client.get("/api/opportunities?dataset_id=ds_57c9285d26&confidence=HIGH")
    assert res_conf.status_code == 200
    data_conf = res_conf.json()
    assert len(data_conf["items"]) > 0
    for item in data_conf["items"]:
        assert item["confidence_tier"] == "HIGH"

    # Filter by priority CRITICAL
    res_prio = client.get("/api/opportunities?dataset_id=ds_57c9285d26&priority=CRITICAL")
    assert res_prio.status_code == 200
    data_prio = res_prio.json()
    assert len(data_prio["items"]) > 0
    for item in data_prio["items"]:
        assert item["priority"] == "CRITICAL"

    # Search for P174
    res_search = client.get("/api/opportunities?dataset_id=ds_57c9285d26&search=P174")
    assert res_search.status_code == 200
    data_search = res_search.json()
    assert len(data_search["items"]) >= 1
    assert "P174" in data_search["items"][0]["page_id"]

