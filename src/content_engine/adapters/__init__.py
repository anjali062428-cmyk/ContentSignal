"""
Dataset Adapter module.
"""
from content_engine.adapters.base import DatasetAdapter
from content_engine.adapters.flyrank import FlyRankAdapter
from content_engine.adapters.generic_tabular import GenericTabularAdapter
from content_engine.adapters.time_series import TimeSeriesAdapter

__all__ = ["DatasetAdapter", "FlyRankAdapter", "GenericTabularAdapter", "TimeSeriesAdapter"]
