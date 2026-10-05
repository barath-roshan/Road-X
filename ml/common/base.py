"""Foundational model abstractions for RoadX ML subsystem."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Union


class BaseModel(ABC):
    """Abstract Base Class for all RoadX predictive and analytical models.

    Defines a consistent lifecycle interface: train -> predict / predict_proba -> save / load.
    """

    def __init__(self, model_name: str, version: str = "0.1.0") -> None:
        self.model_name = model_name
        self.version = version
        self._is_fitted: bool = False
        self.metadata: Dict[str, Any] = {}

    @property
    def is_fitted(self) -> bool:
        """Indicates whether the model has been trained or loaded with fitted parameters."""
        return self._is_fitted

    @abstractmethod
    def train(self, *args: Any, **kwargs: Any) -> Any:
        """Train the model on provided data and return training metrics/summary."""
        raise NotImplementedError

    @abstractmethod
    def predict(self, X: Any, *args: Any, **kwargs: Any) -> Any:
        """Generate class predictions or continuous estimates for input X."""
        raise NotImplementedError

    @abstractmethod
    def predict_proba(self, X: Any, *args: Any, **kwargs: Any) -> Any:
        """Generate prediction probabilities or risk confidence scores for input X."""
        raise NotImplementedError

    @abstractmethod
    def save(self, path: Union[str, Path]) -> None:
        """Persist model weights, hyperparameters, and artifacts to disk."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def load(cls, path: Union[str, Path]) -> BaseModel:
        """Load a persisted model artifact from disk and return an initialized instance."""
        raise NotImplementedError
