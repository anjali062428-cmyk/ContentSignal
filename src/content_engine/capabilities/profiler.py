"""
Dataset Profiling Module.
Provides memory-safe, chunked metadata profiling for tabular and time-series files.
Computes row counts, column counts, data types, missingness, duplicates,
constant columns, cardinality, and summary distributions without crashing on large files.
"""
import io
import os
from pathlib import Path
from typing import Dict, Any, Union, Optional, List
import numpy as np
import pandas as pd


def profile_dataset(
    data_source: Union[str, Path, pd.DataFrame, bytes],
    sample_size: int = 10000,
    max_file_size_mb: float = 50.0,
) -> Dict[str, Any]:
    """
    Profiles a dataset safely.
    Works on a DataFrame, file path, or bytes.
    Returns comprehensive profile metadata dictionary.
    """
    df_sample: Optional[pd.DataFrame] = None
    total_rows: int = 0
    file_size_bytes: int = 0
    is_streamed: bool = False

    # 1. Inspect source & load sample safely
    if isinstance(data_source, pd.DataFrame):
        df_full = data_source
        total_rows = len(df_full)
        df_sample = df_full.head(sample_size).copy()
        file_size_bytes = int(df_full.memory_usage(deep=True).sum())
    elif isinstance(data_source, (str, Path)):
        file_path = Path(data_source)
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found at: {file_path}")
        file_size_bytes = file_path.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)

        if file_size_mb > max_file_size_mb:
            is_streamed = True
            # Read first chunk safely
            try:
                chunk_iter = pd.read_csv(file_path, chunksize=sample_size, encoding="utf-8", on_bad_lines="skip")
                df_sample = next(chunk_iter)
            except UnicodeDecodeError:
                chunk_iter = pd.read_csv(file_path, chunksize=sample_size, encoding="latin-1", on_bad_lines="skip")
                df_sample = next(chunk_iter)
            # Estimate total rows by line counting without loading all columns
            with open(file_path, "rb") as f:
                total_rows = sum(1 for _ in f) - 1
            if total_rows < 0:
                total_rows = len(df_sample)
        else:
            try:
                df_full = pd.read_csv(file_path, encoding="utf-8")
            except UnicodeDecodeError:
                df_full = pd.read_csv(file_path, encoding="latin-1")
            total_rows = len(df_full)
            df_sample = df_full
    elif isinstance(data_source, bytes):
        file_size_bytes = len(data_source)
        buf = io.BytesIO(data_source)
        try:
            df_full = pd.read_csv(buf, encoding="utf-8")
        except UnicodeDecodeError:
            buf.seek(0)
            df_full = pd.read_csv(buf, encoding="latin-1")
        total_rows = len(df_full)
        df_sample = df_full
    else:
        raise TypeError(f"Unsupported data source type: {type(data_source)}")

    if df_sample is None or df_sample.empty:
        return {
            "row_count": 0,
            "column_count": 0,
            "columns": [],
            "dtypes": {},
            "missing_counts": {},
            "missing_rates": {},
            "duplicate_count": 0,
            "duplicate_rate": 0.0,
            "constant_columns": [],
            "cardinality": {},
            "numeric_columns": [],
            "numeric_stats": {},
            "file_size_bytes": file_size_bytes,
            "is_streamed": is_streamed,
            "sample_records": [],
        }

    # Normalize column names (strip whitespace)
    columns = [str(c).strip() for c in df_sample.columns]
    df_sample.columns = columns
    total_cols = len(columns)

    # Missingness
    missing_counts = {col: int(df_sample[col].isnull().sum()) for col in columns}
    missing_rates = {col: round(float(missing_counts[col] / max(1, len(df_sample)) * 100.0), 2) for col in columns}

    # Dtypes classification using pandas API types (prevents numpy issubdtype StringDtype errors)
    dtypes = {}
    numeric_columns = []
    categorical_columns = []
    datetime_columns = []

    for col in columns:
        series = df_sample[col]
        dtype_str = str(series.dtype).lower()
        if pd.api.types.is_bool_dtype(series):
            dtypes[col] = "boolean"
            categorical_columns.append(col)
        elif pd.api.types.is_numeric_dtype(series):
            dtypes[col] = "float" if "float" in dtype_str else "int"
            numeric_columns.append(col)
        elif pd.api.types.is_bool_dtype(series):
            dtypes[col] = "boolean"
            categorical_columns.append(col)
        elif pd.api.types.is_datetime64_any_dtype(series):
            dtypes[col] = "datetime"
            datetime_columns.append(col)
        else:
            # Check if strings can be parsed as dates
            sample_non_null = series.dropna().head(20)
            is_date = False
            if len(sample_non_null) > 0:
                try:
                    pd.to_datetime(sample_non_null, errors="raise")
                    is_date = True
                except Exception:
                    is_date = False
            if is_date:
                dtypes[col] = "datetime"
                datetime_columns.append(col)
            else:
                dtypes[col] = "string"
                categorical_columns.append(col)

    # Cardinality & Constant columns
    cardinality = {}
    constant_columns = []
    for col in columns:
        nunique = int(df_sample[col].nunique(dropna=False))
        cardinality[col] = nunique
        if nunique <= 1 and len(df_sample) > 0:
            constant_columns.append(col)

    # Duplicates count
    if not is_streamed:
        duplicate_count = int(df_sample.duplicated().sum())
        duplicate_rate = round(float(duplicate_count / max(1, total_rows) * 100.0), 2)
    else:
        duplicate_count = int(df_sample.duplicated().sum())
        duplicate_rate = round(float(duplicate_count / max(1, len(df_sample)) * 100.0), 2)

    # Numeric summary statistics
    numeric_stats = {}
    for col in numeric_columns:
        s = df_sample[col].dropna()
        if len(s) > 0:
            numeric_stats[col] = {
                "min": float(np.round(s.min(), 4)),
                "max": float(np.round(s.max(), 4)),
                "mean": float(np.round(s.mean(), 4)),
                "std": float(np.round(s.std(), 4)) if len(s) > 1 else 0.0,
                "zero_pct": round(float((s == 0).sum() / max(1, len(s)) * 100.0), 2),
            }

    # Head records (safe JSON serialization)
    sample_records = []
    for record in df_sample.head(5).to_dict(orient="records"):
        clean_rec = {}
        for k, v in record.items():
            if pd.isna(v):
                clean_rec[k] = None
            elif isinstance(v, (np.integer, int)):
                clean_rec[k] = int(v)
            elif isinstance(v, (np.floating, float)):
                clean_rec[k] = float(np.round(v, 4))
            else:
                clean_rec[k] = str(v)
        sample_records.append(clean_rec)

    # Check for wide-format time series (e.g. 20+ columns that are date-formatted)
    date_like_cols = 0
    for col in columns[1:]:
        if len(col) == 10 and col.count("-") == 2:  # YYYY-MM-DD
            date_like_cols += 1
    is_wide_time_series = date_like_cols > 20

    return {
        "row_count": total_rows,
        "column_count": total_cols,
        "total_rows": total_rows,
        "total_columns": total_cols,
        "columns": columns,
        "dtypes": dtypes,
        "missing_counts": missing_counts,
        "missing_rates": missing_rates,
        "duplicate_count": duplicate_count,
        "duplicate_rate": duplicate_rate,
        "constant_columns": constant_columns,
        "cardinality": cardinality,
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "datetime_columns": datetime_columns,
        "numeric_stats": numeric_stats,
        "file_size_bytes": file_size_bytes,
        "is_streamed": is_streamed,
        "is_wide_time_series": is_wide_time_series,
        "sample_records": sample_records,
    }
