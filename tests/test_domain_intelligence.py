"""
Unit and integration tests for Domain & URL Page Intelligence.
Validates:
1. Domain extraction and normalization.
2. Rule-based page type classification precedence and heuristics.
3. Dataset validation and ingestion with optional domain/url/page_title columns.
4. Absence of domain intelligence in FlyRank starter dataset.
5. Opportunity queue filtering by domain and page_type.
6. Page intelligence detail endpoint including domain fields.
7. Analytics trends domain aggregations.
8. Grounded AI assistant responses for domain-aware vs starter datasets.
"""
import io
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import SessionLocal
from backend.models import Dataset, Page, Opportunity
from content_engine.config import CLEAN_DATA_PATH
from content_engine.classification.page_classifier import (
    extract_and_normalize_domain,
    normalize_domain,
    classify_page_type,
)

client = TestClient(app)


def test_domain_normalization():
    """Verify domain extraction and canonical normalization."""
    # From standard URLs
    assert extract_and_normalize_domain("https://www.example.com/blog/article-1") == "example.com"
    assert extract_and_normalize_domain("http://sub.domain.co.uk/path?x=1") == "sub.domain.co.uk"
    assert extract_and_normalize_domain("WWW.ACME-CORP.ORG/PRODUCTS") == "acme-corp.org"
    assert extract_and_normalize_domain("https://blog.hubspot.com/marketing/seo") == "blog.hubspot.com"

    # With ports and trailing slashes
    assert extract_and_normalize_domain("https://example.org:8080/path/") == "example.org"

    # Explicit domain normalization
    assert normalize_domain("HTTPS://WWW.MySite.io/") == "mysite.io"
    assert normalize_domain("www.sub.service.com") == "sub.service.com"
    assert normalize_domain("example.com") == "example.com"

    # Edge cases
    assert extract_and_normalize_domain("") is None
    assert extract_and_normalize_domain(None) is None
    assert normalize_domain(None) is None
    assert normalize_domain("") is None


def test_page_type_classification_precedence():
    """Verify deterministic rule-based page type classifier precedence."""
    # 1. Explicit page_type overrides everything
    pt, src = classify_page_type(
        explicit_page_type="Case Study",
        content_type="blog_post",
        url="https://example.com/blog/my-post",
        title="My Blog Post",
    )
    assert pt == "Case Study"
    assert src == "explicit_field"

    # 2. URL pattern matching
    pt, src = classify_page_type(url="https://example.com/blog/2026/top-seo-tips")
    assert pt == "Blog / Article"
    assert src == "url_pattern"

    pt, src = classify_page_type(url="https://example.com/product/content-analyzer")
    assert pt == "Product"
    assert src == "url_pattern"

    pt, src = classify_page_type(url="https://example.com/docs/getting-started")
    assert pt == "Documentation"
    assert src == "url_pattern"

    pt, src = classify_page_type(url="https://example.com/pricing")
    assert pt == "Landing Page"
    assert src == "url_pattern"

    pt, src = classify_page_type(url="https://example.com/category/software")
    assert pt == "Category"
    assert src == "url_pattern"

    pt, src = classify_page_type(url="https://example.com/help/faq")
    assert pt == "FAQ"
    assert src == "url_pattern"

    pt, src = classify_page_type(url="https://example.com/contact-us")
    assert pt == "Landing Page" or pt == "Contact / About"
    assert src == "url_pattern"

    # 3. Page title keyword fallback
    pt, src = classify_page_type(
        url="https://example.com/content/12345",
        title="Complete Documentation and API Reference Guide",
    )
    assert pt == "Documentation"
    assert src == "page_title"

    pt, src = classify_page_type(
        url="https://example.com/content/999",
        title="Frequently Asked Questions (FAQ)",
    )
    assert pt == "FAQ"
    assert src == "page_title"

    # 4. Content type mapping fallback
    pt, src = classify_page_type(
        url="https://example.com/xyz",
        title="General Content",
        content_type="product_page",
    )
    assert pt == "Product"
    assert src == "content_type"

    pt, src = classify_page_type(
        url="https://example.com/xyz",
        title="General Content",
        content_type="how_to",
    )
    assert pt == "Guide / Resource"
    assert src == "content_type"


def test_starter_flyrank_has_no_domain_intelligence():
    """Verify FlyRank starter dataset has domain intelligence disabled and intact."""
    # Check opportunities queue endpoint
    res = client.get("/api/opportunities?dataset_id=starter-flyrank&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert data["has_domain_data"] is False
    assert len(data["available_domains"]) == 0
    assert len(data["available_page_types"]) == 0

    # Every item in starter dataset should have null domain and null url
    for item in data["items"]:
        assert item["domain"] is None
        assert item["url"] is None

    # Check trends endpoint
    trends_res = client.get("/api/trends?dataset_id=starter-flyrank")
    assert trends_res.status_code == 200
    trends = trends_res.json()
    assert trends["has_domain_intelligence"] is False
    assert len(trends["opportunities_by_domain"]) == 0
    assert len(trends["page_type_distribution"]) == 0


def test_domain_dataset_lifecycle_and_features():
    """
    Test uploading a CSV with optional domain/url/page_title columns,
    analyzing the dataset, validating domain extraction, opportunity filtering,
    trends aggregations, and page detail responses.
    """
    # 1. Create test DataFrame based on CLEAN_DATA_PATH
    df = pd.read_csv(CLEAN_DATA_PATH).head(25).copy()
    df["content_id"] = [f"domain_test_page_{i}" for i in range(len(df))]

    # Add optional domain intelligence columns
    urls = [
        "https://www.example.com/blog/article-1",
        "https://www.example.com/blog/article-2",
        "https://www.example.com/pricing",
        "https://docs.example.com/guides/setup",
        "https://store.acme.org/product/widget-pro",
    ] * 5  # 25 rows
    df["url"] = urls
    # Leave domain empty for half the rows to test automatic extraction from URL
    df["domain"] = ["example.com" if i % 2 == 0 else "" for i in range(len(df))]
    df["page_title"] = [f"Test Page Title {i}" for i in range(len(df))]

    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    csv_bytes = csv_buf.getvalue().encode("utf-8")

    files = {"file": ("domain_sample.csv", csv_bytes, "text/csv")}
    upload_res = client.post(
        "/api/datasets/upload",
        files=files,
        data={"name": "Domain Intelligence Test Dataset"},
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["is_valid"] is True
    assert upload_data["has_domain_data"] is True
    assert "example.com" in upload_data["distinct_domains"]
    assert "store.acme.org" in upload_data["distinct_domains"]

    dataset_id = upload_data["dataset_id"]

    try:
        # 2. Analyze dataset to populate pages, metrics, opportunities
        an_res = client.post(f"/api/datasets/{dataset_id}/analyze")
        assert an_res.status_code == 200
        an_data = an_res.json()
        assert an_data["status"] == "analyzed"
        assert an_data["pages_analyzed"] == 25

        # 3. Check Opportunity Queue with domain data
        q_res = client.get(f"/api/opportunities?dataset_id={dataset_id}&page_size=50")
        assert q_res.status_code == 200
        q_data = q_res.json()
        assert q_data["has_domain_data"] is True
        assert len(q_data["available_domains"]) >= 2
        assert "example.com" in q_data["available_domains"]
        assert len(q_data["available_page_types"]) >= 2

        # 4. Test filtering by domain
        filter_domain_res = client.get(
            f"/api/opportunities?dataset_id={dataset_id}&domain=store.acme.org"
        )
        assert filter_domain_res.status_code == 200
        filtered_items = filter_domain_res.json()["items"]
        assert len(filtered_items) > 0
        for item in filtered_items:
            assert item["domain"] == "store.acme.org"

        # 5. Test filtering by page_type
        filter_pt_res = client.get(
            f"/api/opportunities?dataset_id={dataset_id}&page_type=Blog+%2F+Article"
        )
        assert filter_pt_res.status_code == 200
        pt_items = filter_pt_res.json()["items"]
        assert len(pt_items) > 0
        for item in pt_items:
            assert item["page_type"] == "Blog / Article"

        # 6. Test page intelligence detail endpoint returns domain fields
        sample_page_id = q_data["items"][0]["page_id"]
        page_res = client.get(f"/api/opportunities/{sample_page_id}")
        assert page_res.status_code == 200
        page_data = page_res.json()
        assert page_data["domain"] is not None
        assert page_data["url"] is not None
        assert page_data["page_type"] is not None
        assert page_data["page_type_source"] is not None

        # 7. Test trends endpoint has domain intelligence
        trends_res = client.get(f"/api/trends?dataset_id={dataset_id}")
        assert trends_res.status_code == 200
        trends = trends_res.json()
        assert trends["has_domain_intelligence"] is True
        assert len(trends["opportunities_by_domain"]) >= 2
        assert len(trends["page_type_distribution"]) >= 2
        assert len(trends["score_by_page_type"]) >= 2

        # 8. Test AI Assistant answers domain question
        ai_res = client.post(
            "/api/ai/chat",
            json={
                "message": "Which domain has the highest opportunity score?",
                "dataset_id": dataset_id,
            },
        )
        assert ai_res.status_code == 200
        ai_data = ai_res.json()
        assert "example.com" in ai_data["response"] or "acme" in ai_data["response"] or "domain" in ai_data["response"].lower()

    finally:
        # Clean up created dataset
        client.delete(f"/api/datasets/{dataset_id}")


def test_ai_assistant_starter_flyrank_fallback():
    """Verify AI Assistant explains domain data is unavailable for FlyRank starter."""
    ai_res = client.post(
        "/api/ai/chat",
        json={
            "message": "What is the best performing domain in this dataset?",
            "dataset_id": "starter-flyrank",
        },
    )
    assert ai_res.status_code == 200
    ai_data = ai_res.json()
    # Should clearly explain domain data is unavailable for FlyRank Starter
    resp = ai_data["response"].lower()
    assert "domain" in resp
    assert "flyrank" in resp or "unavailable" in resp or "not available" in resp or "does not contain" in resp