"""
Capabilities module for semantic capability detection and memory-safe profiling.
"""
from content_engine.capabilities.profiler import profile_dataset
from content_engine.capabilities.detector import detect_dataset_capabilities

__all__ = ["profile_dataset", "detect_dataset_capabilities"]
