"""
iios/intelligence/forecast/forecast/forecast_model.py
=====================================================
Abstract ForecastModel + concrete PointForecastModel.
"""
from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ForecastModelConfig:
    """Static configuration for a forecast model."""

    model_id:       str            = field(default_factory=lambda: str(uuid.uuid4()))
    name:           str            = "Unnamed model"
    version:        str            = "1.0"
    min_data_points: int           = 1
    metadata:       dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id":        self.model_id,
            "name":            self.name,
            "version":         self.version,
            "min_data_points": self.min_data_points,
            "metadata":        self.metadata,
        }


class ForecastModel(ABC):
    """
    Abstract base class for all forecast models.

    Every model produces a ``ForecastResult``-compatible dict via ``predict()``.
    Models are stateless by convention; state lives in the registry.
    """

    def __init__(self, config: ForecastModelConfig) -> None:
        self.config   = config
        self.model_id = config.model_id

    @abstractmethod
    def predict(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Run the forecast.

        Parameters
        ----------
        inputs : domain-specific values (e.g. historical data, features)

        Returns
        -------
        dict with at minimum: value, range_low, range_high, probability, confidence
        """


class PointForecastModel(ForecastModel):
    """
    Simplest model: returns a single point value with a symmetric range.
    Useful as a default / baseline / stub.
    """

    def __init__(
        self,
        config:       ForecastModelConfig | None = None,
        uncertainty:  float = 0.1,
    ) -> None:
        if config is None:
            config = ForecastModelConfig(
                name    = "PointForecastModel",
                version = "1.0",
            )
        super().__init__(config)
        self.uncertainty = max(0.0, uncertainty)

    def predict(self, inputs: dict[str, Any]) -> dict[str, Any]:
        value: float = float(inputs.get("value", 0.0))
        half           = abs(value) * self.uncertainty
        return {
            "value":       value,
            "range_low":   value - half,
            "range_high":  value + half,
            "probability": 0.5,
            "confidence":  1.0 - self.uncertainty,
            "model_id":    self.model_id,
        }


class WeightedEnsembleForecastModel(ForecastModel):
    """
    Combines multiple sub-model outputs as a weighted average.
    Weights default to uniform if not provided.
    """

    def __init__(
        self,
        sub_models:  list[ForecastModel],
        weights:     list[float] | None = None,
        config:      ForecastModelConfig | None = None,
    ) -> None:
        if config is None:
            config = ForecastModelConfig(
                name    = "WeightedEnsembleForecastModel",
                version = "1.0",
            )
        super().__init__(config)
        self.sub_models = sub_models
        n = len(sub_models)
        if weights is None:
            self.weights: list[float] = [1.0 / n] * n if n else []
        else:
            total = sum(weights) or 1.0
            self.weights = [w / total for w in weights]

    def predict(self, inputs: dict[str, Any]) -> dict[str, Any]:
        if not self.sub_models:
            return {
                "value": 0.0, "range_low": 0.0, "range_high": 0.0,
                "probability": 0.5, "confidence": 0.0, "model_id": self.model_id,
            }
        results = [m.predict(inputs) for m in self.sub_models]
        w       = self.weights
        val     = sum(r["value"] * w[i] for i, r in enumerate(results))
        lo      = sum(r["range_low"] * w[i] for i, r in enumerate(results))
        hi      = sum(r["range_high"] * w[i] for i, r in enumerate(results))
        prob    = sum(r.get("probability", 0.5) * w[i] for i, r in enumerate(results))
        conf    = sum(r.get("confidence",  0.5) * w[i] for i, r in enumerate(results))
        return {
            "value":       val,
            "range_low":   lo,
            "range_high":  hi,
            "probability": prob,
            "confidence":  conf,
            "model_id":    self.model_id,
        }
