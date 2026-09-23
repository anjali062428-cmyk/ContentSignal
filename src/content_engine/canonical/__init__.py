"""
Canonical feature representation and column mapping module.
"""
from content_engine.canonical.schema import CANONICAL_SLOTS, CanonicalRecord
from content_engine.canonical.mapper import map_dataframe_to_canonical

__all__ = ["CANONICAL_SLOTS", "CanonicalRecord", "map_dataframe_to_canonical"]
