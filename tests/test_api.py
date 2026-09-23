"""
Integration Tests for FastAPI Backend Endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Page

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "tagline" in data


def test_overview_endpoint():
    res = client.get("/api/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["total_pages_analyzed"] >= 30000
    assert "action_distribution" in data
    assert "priority_distribution" in data
    assert data["high_priority_opportunities"] > 0


def test_opportunities_pagination_and_filter():
    res = client.get("/api/opportunities?page=1&page_size=10&priority=HIGH")
    assert res.status_code == 200
    data = res.json()
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["items"]) <= 10
    for item in data["items"]:
        assert item["priority"] == "HIGH"


def test_page_intelligence_endpoint():
    # Fetch first page ID from opportunities
    opp_res = client.get("/api/opportunities?page=1&page_size=1")
    items = opp_res.json()["items"]
    assert len(items) > 0
    page_id = items[0]["page_id"]

    res = client.get(f"/api/opportunities/{page_id}")
    assert res.status_code == 200
    detail = res.json()
    assert detail["page_id"] == page_id
    assert "metrics" in detail
    assert "reasons" in detail
    assert "recommendation" in detail
    assert "model_signals" in detail


def test_model_metrics_and_features():
    m_res = client.get("/api/model/metrics")
    assert m_res.status_code == 200
    m_data = m_res.json()
    assert "gradient_boosting" in m_data["metrics"]

    f_res = client.get("/api/model/features")
    assert f_res.status_code == 200
    f_data = f_res.json()
    assert "random_forest_top_features" in f_data


def test_archetypes_endpoint():
    res = client.get("/api/archetypes")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is True
    assert "profiles" in data
    assert data["n_clusters"] == 6
    assert data["row_count"] == 30000
    assert data["min_required"] == 50
    assert data["additional_needed"] == 0
    assert data["status_badge"] == "Sufficient data"


def test_archetypes_endpoint_custom_dataset_insufficient_data():
    res = client.get("/api/archetypes?dataset_id=valid_25_upload")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is False
    assert "Not enough behavioral variation" in data["reason"]
    assert len(data["profiles"]) == 0
    assert data["row_count"] == 25
    assert data["min_required"] == 50
    assert data["additional_needed"] == 25
    assert data["status_badge"] == "Insufficient data"
    assert "Groups require enough records and behavioral variation" in data["explanation"]


def test_archetypes_both_cases_small_and_suitable():
    # Case 1: 25-row dataset -> unavailable state
    res_small = client.get("/api/archetypes?dataset_id=valid_25_upload")
    assert res_small.status_code == 200
    d_small = res_small.json()
    assert d_small["available"] is False
    assert d_small["row_count"] == 25
    assert d_small["min_required"] == 50
    assert d_small["additional_needed"] == 25
    assert d_small["status_badge"] == "Insufficient data"
    assert "Groups require enough records and behavioral variation" in d_small["explanation"]
    assert len(d_small["profiles"]) == 0

    # Case 2: 50+ row suitable dataset -> actual groups
    res_large = client.get("/api/archetypes?dataset_id=starter-flyrank")
    assert res_large.status_code == 200
    d_large = res_large.json()
    assert d_large["available"] is True
    assert d_large["row_count"] >= 50
    assert d_large["min_required"] == 50
    assert d_large["additional_needed"] == 0
    assert d_large["status_badge"] == "Sufficient data"
    assert len(d_large["profiles"]) >= 2
    profile_item = next(iter(d_large["profiles"].values()))
    assert "size" in profile_item
    assert "median_impressions" in profile_item
    assert "median_ctr" in profile_item
    assert "recommended_action" in profile_item



def test_csv_export():
    res = client.get("/api/export/csv?limit=20")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    content = res.text
    assert "queue_rank,page_id,opportunity_score" in content
    assert len(content.splitlines()) > 5


def test_auth_flow():
    test_email = "testuser@editorial.ai"
    test_password = "SecretPassword123!"

    # 1. Register (or login if exists)
    reg_res = client.post("/api/auth/register", json={
        "email": test_email,
        "password": test_password,
        "full_name": "Test Editor"
    })
    if reg_res.status_code == 400:
        # Already exists, proceed to login
        pass
    else:
        assert reg_res.status_code == 200
        assert "access_token" in reg_res.json()

    # 2. Login
    login_res = client.post("/api/auth/login", json={
        "email": test_email,
        "password": test_password,
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    assert token is not None

    # 3. Protected /me route
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == test_email


def test_ai_chat_grounded():
    res = client.post("/api/ai/chat", json={
        "message": "What should I refresh first?"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_grounded"] is True
    assert len(data["response"]) > 20


def test_on_demand_analyze():
    res = client.post("/api/analyze", json={
        "impressions_90d": 3500,
        "clicks_90d": 10,
        "ctr": 0.28,
        "avg_position": 5.2,
        "days_since_last_update": 210,
        "engagement_rate": 22.0
    })
    assert res.status_code == 200
    data = res.json()
    assert 0 <= data["opportunity_score"] <= 100
    assert data["action"] in ["REFRESH", "OPTIMIZE", "INVESTIGATE"]
