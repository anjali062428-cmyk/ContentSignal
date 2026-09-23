"""
Integration Tests for Production Upgrades:
- Auth email verification & password policy
- Watchlist management (star/unstar)
- Impact action tracking
- Evidence Center exports (PDF, DOCX, XLSX)
- Content Opportunity Map & Attention Center
- Dataset Analysis Jobs
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_password_policy_and_verification():
    # Weak password rejected (< 8 chars)
    res_weak = client.post("/api/auth/register", json={
        "email": "weakpass@testdomain.com",
        "password": "short",
    })
    assert res_weak.status_code in [400, 422]

    # Password mismatch rejected
    res_mismatch = client.post("/api/auth/register", json={
        "email": "mismatch@testdomain.com",
        "password": "ValidPassword123!",
        "confirm_password": "DifferentPassword123!",
    })
    assert res_mismatch.status_code == 400

    # Valid registration for non-test domain generates verification token
    import uuid
    new_email = f"newuser_{uuid.uuid4().hex[:8]}@customcompany.org"
    res_reg = client.post("/api/auth/register", json={
        "email": new_email,
        "password": "StrongPassword99!",
        "confirm_password": "StrongPassword99!",
        "full_name": "Test User",
    })
    assert res_reg.status_code == 200
    reg_data = res_reg.json()
    assert reg_data["is_verified"] is False
    assert "masked_email" in reg_data
    token = reg_data["verification_token"]
    assert token is not None

    # Unverified login attempt rejected with 403
    res_unverified_login = client.post("/api/auth/login", json={
        "email": new_email,
        "password": "StrongPassword99!",
    })
    assert res_unverified_login.status_code == 403

    # Verification with bad token fails
    res_bad_verify = client.post("/api/auth/verify-email", json={
        "email": new_email,
        "token": "000000",
    })
    assert res_bad_verify.status_code == 400

    # Verification with correct token succeeds
    res_good_verify = client.post("/api/auth/verify-email", json={
        "email": new_email,
        "token": token,
    })
    assert res_good_verify.status_code == 200
    assert "access_token" in res_good_verify.json()

    # Now login succeeds
    res_login_ok = client.post("/api/auth/login", json={
        "email": new_email,
        "password": "StrongPassword99!",
    })
    assert res_login_ok.status_code == 200
    assert res_login_ok.json()["user"]["is_verified"] is True


def test_watchlist_workflow():
    # Toggle star on page_00001
    res = client.post("/api/watchlist/page_00001")
    assert res.status_code == 200
    data = res.json()
    assert data["page_id"] == "page_00001"
    assert data["is_starred"] is True

    # Check watchlist ids
    res_ids = client.get("/api/watchlist/ids")
    assert res_ids.status_code == 200
    ids = res_ids.json()
    assert "page_00001" in ids

    # Check full watchlist items
    res_items = client.get("/api/watchlist")
    assert res_items.status_code == 200
    items = res_items.json()
    assert any(it["page_id"] == "page_00001" for it in items)

    # Toggle again -> removes from watchlist
    res_untoggle = client.post("/api/watchlist/page_00001")
    assert res_untoggle.status_code == 200
    assert res_untoggle.json()["is_starred"] is False


def test_impact_action_tracking():
    from backend.database import SessionLocal
    from backend.models import Page
    _db = SessionLocal()
    first_p = _db.query(Page).first()
    pid = first_p.page_id if first_p else "page_00001"
    _db.close()

    res = client.post("/api/impact/mark", json={
        "page_id": pid,
        "action_type": "REFRESH",
        "notes": "Updated statistics and refreshed search snippets for Q3.",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["page_id"] == pid
    assert data["action_type"] == "REFRESH"
    assert data["before_metrics"] is not None

    # Get impact summary
    res_summary = client.get("/api/impact")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert summary["total_actions"] >= 1
    assert "REFRESH" in summary["actions_by_type"]
    assert "baseline" in summary["notice"].lower()


def test_evidence_exports():
    # PDF
    res_pdf = client.get("/api/export/evidence/pdf?limit=10")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000

    # DOCX
    res_docx = client.get("/api/export/evidence/docx?limit=10")
    assert res_docx.status_code == 200
    assert "wordprocessingml" in res_docx.headers["content-type"]
    assert len(res_docx.content) > 1000

    # XLSX
    res_xlsx = client.get("/api/export/evidence/xlsx?limit=10")
    assert res_xlsx.status_code == 200
    assert "spreadsheetml" in res_xlsx.headers["content-type"]
    assert len(res_xlsx.content) > 1000


def test_opportunity_map_and_attention_center():
    # Opportunity Map points
    res_map = client.get("/api/opportunity-map?limit=50")
    assert res_map.status_code == 200
    map_data = res_map.json()
    assert "points" in map_data
    assert len(map_data["points"]) > 0
    first_pt = map_data["points"][0]
    assert "visibility" in first_pt
    assert "opportunity_score" in first_pt
    assert "priority" in first_pt

    # Attention Center
    res_ac = client.get("/api/attention-center")
    assert res_ac.status_code == 200
    ac_data = res_ac.json()
    assert "critical_items" in ac_data
    assert "at_risk_items" in ac_data
    assert "stable_items" in ac_data
    assert "content_brief" in ac_data
    assert len(ac_data["content_brief"]["headline"]) > 5
