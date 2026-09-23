"""
Unit tests for data quarantine and schema validation.
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from content_engine.config import (
    RAW_DATA_PATH,
    CLEAN_DATA_PATH,
    DOCUMENTED_44_COLUMNS,
    RESTRICTED_FLYRANK_COLUMNS,
)
from content_engine.validation.quarantine import quarantine_and_clean_dataset


def test_raw_dataset_exists_and_unmodified():
    assert RAW_DATA_PATH.exists(), "Raw dataset must exist."
    df_raw = pd.read_csv(RAW_DATA_PATH)
    assert df_raw.shape == (30000, 53), f"Raw dataset must remain untouched (30000, 53), got {df_raw.shape}"


def test_clean_dataset_quarantined_columns():
    df_clean = pd.read_csv(CLEAN_DATA_PATH)
    assert df_clean.shape == (30000, 44), f"Clean dataset must have (30000, 44), got {df_clean.shape}"

    # Verify zero restricted columns remain
    for col in RESTRICTED_FLYRANK_COLUMNS:
        assert col not in df_clean.columns, f"Restricted column '{col}' leaked into clean dataset!"

    # Verify exact 44 documented columns
    assert list(df_clean.columns) == DOCUMENTED_44_COLUMNS, "Columns do not match documented 44 columns."


def test_quarantine_fails_on_unexpected_column(tmp_path):
    dummy_csv = tmp_path / "corrupted.csv"
    clean_csv = tmp_path / "clean_out.csv"
    rep_dir = tmp_path / "reps"

    # Create dummy with an unexpected column
    df = pd.DataFrame({"content_id": ["c1"], "client_id": ["cl1"], "unauthorized_column": [123]})
    df.to_csv(dummy_csv, index=False)

    with pytest.raises(ValueError, match="SECURITY ALERT: Unexpected undocumented columns detected"):
        quarantine_and_clean_dataset(raw_path=dummy_csv, clean_path=clean_csv, reports_dir=rep_dir)


def test_rate_scales():
    df_clean = pd.read_csv(CLEAN_DATA_PATH)
    # Rate columns are percentage-scale (e.g., ctr=0.76 means 0.76%)
    median_ctr = df_clean["ctr"].dropna().median()
    assert 0.0 <= median_ctr <= 15.0, f"CTR scale unexpected: median CTR is {median_ctr}"


def test_position_sentinel():
    df_clean = pd.read_csv(CLEAN_DATA_PATH)
    zero_pos = (df_clean["avg_position"] == 0).sum()
    assert zero_pos > 0, "Expected missing position sentinel values (avg_position == 0)"
