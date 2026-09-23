"""
Unit and Integration Tests for SRS Section 24: Projects & System API Specification.
Covers:
- GET /health & GET /api/health
- POST /auth/login (root-level alias)
- POST /projects & GET /projects
- GET /projects/{project_id}
- GET /projects/{project_id}/runs
- GET /projects/{project_id}/runs/{run_id}
- GET /projects/{project_id}/content (filtering, pagination, 30d comparative metrics)
- GET /projects/{project_id}/content/{content_id}
- GET /projects/{project_id}/recommendations
- PATCH /projects/{project_id}/actions/{action_id}
- GET /projects/{project_id}/export (CSV & JSON)
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_check_endpoints():
    """Validates SRS Section 24 GET /health and /api/health diagnostics."""
    for path in ["/health", "/api/health"]:
        res = client.get(path)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Content Intelligence Engine API"
        assert data["version"] == "2.0.0"
        assert data["database"] == "connected"
        assert "model_available" in data
        assert "available_disk_mb" in data
        assert data["worker_status"] == "ready"


def test_root_auth_login():
    """Validates SRS Section 24 POST /auth/login root endpoint."""
    test_email = "testuser@editorial.ai"
    test_password = "SecretPassword123!"
    client.post("/api/auth/register", json={
        "email": test_email,
        "password": test_password,
        "full_name": "Test Editor",
    })
    res = client.post("/auth/login", json={
        "email": test_email,
        "password": test_password,
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == test_email



def test_projects_crud_and_runs():
    """Validates POST /projects, GET /projects, and GET /projects/{id}."""
    # List projects
    res_list = client.get("/projects")
    assert res_list.status_code == 200
    projects = res_list.json()
    assert len(projects) >= 1
    starter = next((p for p in projects if p["project_id"] == "starter-flyrank"), None)
    assert starter is not None
    assert starter["is_starter"] is True
    assert starter["row_count"] == 30000
    assert starter["active_run_summary"] is not None
    assert starter["active_run_summary"]["status"] == "COMPLETED"

    # Create new project
    res_create = client.post("/projects", json={
        "name": "Acme Content Operations",
        "description": "Production SEO intelligence workspace",
        "domain": "acme.io",
    })
    assert res_create.status_code == 200
    new_proj = res_create.json()
    proj_id = new_proj["project_id"]
    assert proj_id.startswith("proj_")
    assert new_proj["name"] == "Acme Content Operations"

    # Get project detail
    res_detail = client.get(f"/projects/{proj_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["project_id"] == proj_id
    assert detail["validation_status"] == "pending"

    # Test alias resolution for default/starter
    res_default = client.get("/projects/default")
    assert res_default.status_code == 200
    assert res_default.json()["project_id"] == "starter-flyrank"


def test_project_runs_and_audit():
    """Validates GET /projects/{id}/runs and GET /projects/{id}/runs/{run_id}."""
    res_runs = client.get("/projects/starter-flyrank/runs")
    assert res_runs.status_code == 200
    runs = res_runs.json()
    assert len(runs) >= 1
    assert runs[0]["status"] == "COMPLETED"
    run_id = runs[0]["job_id"]

    # Get run detail with execution logs, stage timings, champion model metrics
    res_run_detail = client.get(f"/projects/starter-flyrank/runs/{run_id}")
    assert res_run_detail.status_code == 200
    run_detail = res_run_detail.json()
    assert run_detail["run_id"] == run_id
    assert run_detail["status"] == "COMPLETED"
    assert len(run_detail["execution_logs"]) >= 1
    assert "validation_sec" in run_detail["stage_timings"]
    assert "roc_auc" in run_detail["champion_model_metrics"]
    assert run_detail["champion_model_metrics"]["roc_auc"] >= 0.80


def test_project_content_and_filtering():
    """Validates GET /projects/{id}/content with filters and 30-day comparative metrics."""
    res_content = client.get("/projects/starter-flyrank/content?page=1&page_size=10")
    assert res_content.status_code == 200
    data = res_content.json()
    assert data["total"] >= 30000
    assert len(data["items"]) == 10

    first_item = data["items"][0]
    assert "opportunity_score" in first_item
    assert "content_status" in first_item
    assert "confidence_tier" in first_item
    assert "impressions_last_30d" in first_item
    assert "clicks_last_30d" in first_item
    assert "trend_classification" in first_item
    assert len(first_item["reasons"]) >= 1

    # Filter by content_status = REFRESH NOW
    res_filtered = client.get("/projects/starter-flyrank/content?content_status=REFRESH%20NOW&page_size=5")
    assert res_filtered.status_code == 200
    filtered_data = res_filtered.json()
    assert filtered_data["total"] > 0
    assert all(item["content_status"] == "REFRESH NOW" for item in filtered_data["items"])

    # Filter by confidence_tier = HIGH
    res_conf = client.get("/projects/starter-flyrank/content?confidence_tier=HIGH&page_size=5")
    assert res_conf.status_code == 200
    assert all(item["confidence_tier"] == "HIGH" for item in res_conf.json()["items"])


def test_project_content_detail():
    """Validates GET /projects/{id}/content/{content_id}."""
    opp_res = client.get("/projects/starter-flyrank/content?page=1&page_size=1")
    assert opp_res.status_code == 200
    items = opp_res.json()["items"]
    assert len(items) > 0
    page_id = items[0]["page_id"]

    res = client.get(f"/projects/starter-flyrank/content/{page_id}")
    assert res.status_code == 200
    detail = res.json()
    assert detail["page_id"] == page_id
    assert "comparison_30d" in detail
    assert "clicks_last_30d" in detail["comparison_30d"]
    assert "impressions_last_30d" in detail["comparison_30d"]
    assert "trend_classification" in detail["comparison_30d"]
    assert len(detail["reasons"]) >= 1
    assert "checklist" in detail["recommendation"]
    assert len(detail["recommendation"]["checklist"]) >= 3



def test_project_recommendations():
    """Validates GET /projects/{id}/recommendations grouped by action directive."""
    res = client.get("/projects/starter-flyrank/recommendations?limit=50")
    assert res.status_code == 200
    data = res.json()
    assert data["project_id"] == "starter-flyrank"
    assert data["total_recommendations"] == 50
    assert "grouped_by_action" in data
    grouped = data["grouped_by_action"]
    assert "REFRESH" in grouped
    assert "OPTIMIZE" in grouped
    assert "PROTECT" in grouped

    # Each recommendation item must have required fields
    if grouped["REFRESH"]:
        rec_item = grouped["REFRESH"][0]
        assert "opportunity_score" in rec_item
        assert "confidence" in rec_item
        assert "primary_reason" in rec_item


def test_project_action_workflow_tracking():
    """Validates PATCH /projects/{id}/actions/{action_id}."""
    # Update page_00001 to IN_PROGRESS
    res_patch = client.patch(
        "/projects/starter-flyrank/actions/page_00001",
        json={"status": "IN_PROGRESS", "notes": "Content team reviewing Q3 search intent."}
    )
    assert res_patch.status_code == 200
    action_data = res_patch.json()
    assert action_data["page_id"] == "page_00001"
    assert action_data["status"] == "IN_PROGRESS"
    assert "Content team reviewing" in action_data["notes"]

    # Transition to COMPLETED
    res_done = client.patch(
        "/projects/starter-flyrank/actions/page_00001",
        json={"status": "COMPLETED", "notes": "Refresh published; baseline benchmark locked."}
    )
    assert res_done.status_code == 200
    assert res_done.json()["status"] == "COMPLETED"


def test_project_exports():
    """Validates GET /projects/{id}/export for both CSV and JSON formats."""
    # CSV export
    res_csv = client.get("/projects/starter-flyrank/export?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    csv_text = res_csv.text
    assert "Rank,Page ID,Title,URL,Domain" in csv_text
    assert "Opportunity Score" in csv_text
    assert "Action Directive" in csv_text
    assert len(csv_text.splitlines()) > 50

    # JSON export
    res_json = client.get("/projects/starter-flyrank/export?format=json")
    assert res_json.status_code == 200
    json_data = res_json.json()
    assert json_data["project_id"] == "starter-flyrank"
    assert json_data["total_items"] > 0
    assert "items" in json_data
    assert "opportunity_score" in json_data["items"][0]
