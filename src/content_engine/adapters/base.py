"""
Abstract Base Dataset Adapter.
Defines lifecycle interface for all dataset adapters:
profile -> detect_capabilities -> check_readiness -> map_canonical -> train_or_evaluate -> score.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
import pandas as pd


class DatasetAdapter(ABC):
    def __init__(self, dataset_id: str, name: Optional[str] = None):
        self.dataset_id = dataset_id
        self.name = name or dataset_id

    @abstractmethod
    def profile(self, data_source: Any) -> Dict[str, Any]:
        """Profiles the dataset metadata and distributions safely."""
        pass

    @abstractmethod
    def detect_capabilities(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Detects semantic capabilities (CONTENT, VISIBILITY, ENGAGEMENT, SEARCH, etc.)."""
        pass

    @abstractmethod
    def check_readiness(self, profile: Dict[str, Any], capabilities: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates dataset against ContentSignal 10-point checklist."""
        pass

    @abstractmethod
    def map_canonical(self, df: pd.DataFrame, target: Optional[str] = None) -> Tuple[list, pd.DataFrame]:
        """Maps source columns to standard canonical slots."""
        pass

    @abstractmethod
    def train_or_evaluate(self, df: pd.DataFrame, canonical_df: pd.DataFrame, target: Optional[str] = None) -> Dict[str, Any]:
        """Trains dataset-specific model or computes empirical baseline with a model report."""
        pass

    @abstractmethod
    def score(self, df: pd.DataFrame, canonical_df: pd.DataFrame, model_output: Dict[str, Any]) -> pd.DataFrame:
        """Computes Opportunity Scores, Priorities, Reasons, and Actions."""
        pass

    @classmethod
    def is_applicable(cls, columns: list) -> bool:
        """Determines if this adapter is applicable to the given columns."""
        return True

    def train_or_score(self, df: pd.DataFrame, target: Optional[str] = None) -> Dict[str, Any]:
        """Convenience method running mapping, training, and scoring."""
        mappings, can_df = self.map_canonical(df, target=target)
        model_out = self.train_or_evaluate(df, can_df, target=target)
        df_scored = self.score(df, can_df, model_out)
        return {
            "mappings": mappings,
            "can_df": can_df,
            "model_report": model_out.get("model_report", {}),
            "df_scored": df_scored,
            "model_output": model_out,
        }

