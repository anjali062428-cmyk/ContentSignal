"""
Comprehensive tests for Dataset Management and CSV Upload feature.
Tests schema validation, quarantine, unexpected columns rejection, missing columns,
duplicate IDs, invalid percentage scales, dataset isolation, active dataset switching,
and starter dataset deletion protection.
"""
import io
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import SessionLocal
from backend.models import Dataset, Page, Opportunity
from content_engine.config import CLEAN_DATA_PATH, RAW_DATA_PATH

client = TestClient(app)


@pytest.fixture
def clean_sample_df():
    df = pd.read_csv(CLEAN_DATA_PATH).head(30)
    # Ensure unique content_id
    df["content_id"] = [f"test_page_{i}" for i in range(len(df))]
    return df


def test_list_datasets():
    """Verify that GET /api/datasets returns at least the starter dataset."""
    res = client.get("/api/datasets")
    assert res.status_code == 200
    datasets = res.json()
    assert len(datasets) >= 1
    starter = next((d for d in datasets if d["dataset_id"] == "starter-flyrank"), None)
    assert starter is not None
    assert starter["is_starter"] == True
    assert starter["row_count"] == 30000


def test_valid_csv_upload(clean_sample_df):
    """Test valid 44-column CSV upload passes validation."""
    csv_buf = io.StringIO()
    clean_sample_df.to_csv(csv_buf, index=False)
    csv_bytes = csv_buf.getvalue().encode("utf-8")

    files = {"file": ("valid_sample.csv", csv_bytes, "text/csv")}
    res = client.post("/api/datasets/upload", files=files, data={"name": "Valid Test Dataset"})
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] == True
    assert data["valid_status"] == "VALID"
    assert data["row_count"] == len(clean_sample_df)
    assert data["column_count"] == 44
    assert len(data["errors"]) == 0
    assert "dataset_id" in data

    # Clean up uploaded dataset
    client.delete(f"/api/datasets/{data['dataset_id']}")


def test_missing_columns_rejected(clean_sample_df):
    """Test that CSV missing required columns is rejected."""
    df_missing = clean_sample_df.drop(columns=["impressions_90d", "clicks_90d", "ctr"])
    csv_buf = io.StringIO()
    df_missing.to_csv(csv_buf, index=False)
    csv_bytes = csv_buf.getvalue().encode("utf-8")

    files = {"file": ("missing_cols.csv", csv_bytes, "text/csv")}
    res = client.post("/api/datasets/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] == False
    assert data["valid_status"] == "INVALID"
    assert "impressions_90d" in data["missing_required_fields"]
    assert "clicks_90d" in data["missing_required_fields"]
    assert len(data["errors"]) > 0

    # Clean up
    client.delete(f"/api/datasets/{data['dataset_id']}")


def test_unexpected_columns_rejected(clean_sample_df):
    """Test that CSV containing unexpected/undocumented columns is rejected."""
    df_extra = clean_sample_df.copy()
    df_extra["unknown_hack_column"] = "suspicious_data"
    df_extra["another_rogue_metric"] = 999.9

    csv_buf = io.StringIO()
    df_extra.to_csv(csv_buf, index=False)
    csv_bytes = csv_buf.getvalue().encode("utf-8")

    files = {"file": ("unexpected_cols.csv", csv_bytes, "text/csv")}
    res = client.post("/api/datasets/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] == False
    assert "unknown_hack_column" in data["unexpected_fields"]
    assert "another_rogue_metric" in data["unexpected_fields"]

    client.delete(f"/api/datasets/{data['dataset_id']}")


def test_restricted_columns_quarantined():
    """Test that 9 proprietary FlyRank columns are quarantined and removed."""
    df_raw = pd.read_csv(RAW_DATA_PATH).head(20)
    csv_buf = io.StringIO()
    df_raw.to_csv(csv_buf, index=False)
    csv_bytes = csv_buf.getvalue().encode("utf-8")

    files = {"file": ("raw_with_flyrank.csv", csv_bytes, "text/csv")}
    res = client.post("/api/datasets/upload", files=files, data={"name": "Quarantine Test"})
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] == True
    assert len(data["quarantined_fields"]) == 9
    assert "health_score" in data["quarantined_fields"]
    assert "is_declining" in data["quarantined_fields"]

    client.delete(f"/api/datasets/{data['dataset_id']}")


def test_duplicate_ids_detected(clean_sample_df):
    """Test that duplicate content_ids are detected and rejected."""
    df_dup = clean_sample_df.copy()
    df_dup.loc[1, "content_id"] = df_dup.loc[0, "content_id"]  # Introduce duplicate

    csv_buf = io.StringIO()
    df_dup.to_csv(csv_buf, index=False)
    csv_bytes = csv_buf.getvalue().encode("utf-8")

    files = {"file": ("duplicates.csv", csv_bytes, "text/csv")}
    res = client.post("/api/datasets/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] == False
    assert data["duplicate_ids_count"] >= 1

    client.delete(f"/api/datasets/{data['dataset_id']}")


def test_invalid_percentage_values(clean_sample_df):
    """Test that percentage values > 100% or negative are flagged."""
    df_bad_rate = clean_sample_df.copy()
    df_bad_rate.loc[0, "ctr"] = 250.0  # Invalid > 100%

    csv_buf = io.StringIO()
    df_bad_rate.to_csv(csv_buf, index=False)
    csv_bytes = csv_buf.getvalue().encode("utf-8")

    files = {"file": ("bad_rate.csv", csv_bytes, "text/csv")}
    res = client.post("/api/datasets/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] == False
    assert any("ctr" in err.lower() for err in data["errors"])

    client.delete(f"/api/datasets/{data['dataset_id']}")


def test_dataset_isolation_and_analysis(clean_sample_df):
    """Upload second dataset, analyze it, and verify database isolation."""
    sample_size = 25
    df_subset = clean_sample_df.head(sample_size).copy()
    df_subset["content_id"] = [f"second_ds_page_{i}" for i in range(sample_size)]

    csv_buf = io.StringIO()
    df_subset.to_csv(csv_buf, index=False)
    csv_bytes = csv_buf.getvalue().encode("utf-8")

    # 1. Upload
    files = {"file": ("second_dataset.csv", csv_bytes, "text/csv")}
    up_res = client.post("/api/datasets/upload", files=files, data={"name": "Second Custom Dataset"})
    assert up_res.status_code == 200
    up_data = up_res.json()
    assert up_data["is_valid"] == True
    ds_id = up_data["dataset_id"]

    # 2. Analyze
    an_res = client.post(f"/api/datasets/{ds_id}/analyze")
    assert an_res.status_code == 200
    an_data = an_res.json()
    assert an_data["status"] == "analyzed"
    assert an_data["pages_analyzed"] == sample_size

    # 3. Check DB records are isolated
    db = SessionLocal()
    try:
        starter_count = db.query(Page).filter(Page.dataset_id == "starter-flyrank").count()
        second_count = db.query(Page).filter(Page.dataset_id == ds_id).count()
        assert starter_count == 30000
        assert second_count == sample_size

        starter_opps = db.query(Opportunity).filter(Opportunity.dataset_id == "starter-flyrank").count()
        second_opps = db.query(Opportunity).filter(Opportunity.dataset_id == ds_id).count()
        assert starter_opps == 30000
        assert second_opps == sample_size
    finally:
        db.close()

    # 4. Check active dataset switching in API
    overview_starter = client.get("/api/overview?dataset_id=starter-flyrank").json()
    assert overview_starter["total_pages_analyzed"] == 30000

    overview_second = client.get(f"/api/overview?dataset_id={ds_id}").json()
    assert overview_second["total_pages_analyzed"] == sample_size

    # Check queue query with dataset_id
    queue_res = client.get(f"/api/opportunities?dataset_id={ds_id}&limit=50").json()
    assert queue_res["total"] == sample_size

    # Check export CSV with dataset_id
    csv_export_res = client.get(f"/api/export/csv?dataset_id={ds_id}")
    assert csv_export_res.status_code == 200
    lines = csv_export_res.text.strip().split("\n")
    assert len(lines) == sample_size + 1  # header + rows

    # 5. Clean up
    del_res = client.delete(f"/api/datasets/{ds_id}")
    assert del_res.status_code == 200


def test_cannot_delete_starter_dataset():
    """Verify that deleting starter-flyrank is strictly forbidden."""
    res = client.delete("/api/datasets/starter-flyrank")
    assert res.status_code == 400
    assert "Forbidden" in res.json()["detail"] or "cannot be deleted" in res.json()["detail"]

    # Verify starter dataset remains in DB
    db = SessionLocal()
    try:
        starter = db.query(Dataset).filter(Dataset.dataset_id == "starter-flyrank").first()
        assert starter is not None
        assert starter.row_count == 30000
    finally:
        db.close()