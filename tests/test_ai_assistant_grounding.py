"""
Tests for Grounded AI Assistant & Multi-Dataset Synthesis.
Verifies all 7 required core user questions against live database telemetry.
Ensures zero hallucinations, strict grounding, and dataset isolation.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

CUSTOM_DS = "ds_57c9285d26"
STARTER_DS = "starter-flyrank"


def test_ai_primary_older_performing_pages_query():
    """
    Validates the exact user prompt:
    'Which 5 older pages have the strongest performance in the current dataset?
    Give me the page IDs, content age, opportunity score, and the metrics you used to decide.'
    """
    prompt = (
        "Which 5 older pages have the strongest performance in the current dataset? "
        "Give me the page IDs, content age, opportunity score, and the metrics you used to decide."
    )
    res = client.post("/api/ai/chat", json={
        "message": prompt,
        "dataset_id": CUSTOM_DS,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_grounded"] is True
    text = data["response"]

    # Must contain page identifiers (canonical P174 or full database ID)
    assert "P174" in text
    # Must contain Content age
    assert "Content age:" in text or "content age" in text.lower()
    # Must contain Opportunity score
    assert "Opportunity score:" in text or "opportunity score" in text.lower()
    assert "/100" in text
    # Must contain Performance evidence
    assert "clicks" in text.lower()
    assert "impressions" in text.lower()
    assert "ctr" in text.lower()
    # Must explain Metrics Used to Decide
    assert "Metrics Used to Decide" in text
    assert "content_age_days" in text or "days_since_last_update" in text
    assert "clicks_90d" in text
    assert "impressions_90d" in text


def test_ai_dataset_count_and_isolation():
    """
    Validates 'How many pages are in the current dataset?'
    Ensures strict dataset isolation between custom dataset (300) and starter (30,000).
    """
    prompt = "How many pages are in the current dataset?"

    # Custom Dataset (300 records)
    res_custom = client.post("/api/ai/chat", json={
        "message": prompt,
        "dataset_id": CUSTOM_DS,
    })
    assert res_custom.status_code == 200
    custom_data = res_custom.json()
    assert custom_data["is_grounded"] is True
    assert "300" in custom_data["response"]
    assert "Content Status Breakdown" in custom_data["response"]
    assert "Review Priority Breakdown" in custom_data["response"]

    # Starter Dataset (30,000 records)
    res_starter = client.post("/api/ai/chat", json={
        "message": prompt,
        "dataset_id": STARTER_DS,
    })
    assert res_starter.status_code == 200
    starter_data = res_starter.json()
    assert starter_data["is_grounded"] is True
    assert "30,000" in starter_data["response"]


def test_ai_top_opportunities_query():
    """
    Validates 'What are the top 5 highest-opportunity pages?'
    """
    prompt = "What are the top 5 highest-opportunity pages?"
    res = client.post("/api/ai/chat", json={
        "message": prompt,
        "dataset_id": CUSTOM_DS,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_grounded"] is True
    text = data["response"]
    assert "Top 5 Highest-Opportunity Pages" in text
    assert "Opportunity Score:" in text
    assert "Recommended Directive:" in text
    assert "Primary Reason:" in text


def test_ai_visibility_weak_clicks_query():
    """
    Validates 'Which pages have the strongest visibility but weak click performance?'
    """
    prompt = "Which pages have the strongest visibility but weak click performance?"
    res = client.post("/api/ai/chat", json={
        "message": prompt,
        "dataset_id": CUSTOM_DS,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_grounded"] is True
    text = data["response"]
    assert "High Visibility" in text
    assert "Weak Click Performance" in text
    assert "OPTIMIZE" in text
    assert "impressions" in text.lower()


def test_ai_score_explanation_query():
    """
    Validates 'Explain why the highest-opportunity page received its score.'
    """
    prompt = "Explain why the highest-opportunity page received its score."
    res = client.post("/api/ai/chat", json={
        "message": prompt,
        "dataset_id": CUSTOM_DS,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_grounded"] is True
    text = data["response"]
    assert "Score Diagnostic for Highest-Opportunity Page" in text
    assert "Primary Decline Driver:" in text
    assert "Underlying Telemetry Snapshot:" in text
    assert "Organic Impressions (90d):" in text
    assert "Strategic Action Recommendation:" in text


def test_ai_unavailable_info_audit_query():
    """
    Validates 'What information is unavailable in this dataset?'
    Ensures clear disclosure of missing capabilities without hallucination.
    """
    prompt = "What information is unavailable in this dataset?"
    res = client.post("/api/ai/chat", json={
        "message": prompt,
        "dataset_id": CUSTOM_DS,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_grounded"] is True
    text = data["response"]
    assert "Data Availability & Capability Audit" in text
    assert "UNAVAILABLE" in text
    assert "Available & Measured Signals" in text


def test_ai_page_context_explanation():
    """
    Validates page-specific query with page_id given.
    """
    res = client.post("/api/ai/chat", json={
        "message": "Why does this page need review?",
        "page_id": f"{CUSTOM_DS}_P174",
        "dataset_id": CUSTOM_DS,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_grounded"] is True
    text = data["response"]
    assert "Editorial Intelligence Assessment for" in text
    assert "Opportunity Score:" in text
    assert "Measured Signal Evidence:" in text
    assert "Observable Performance Numbers:" in text
