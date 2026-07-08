"""
iios/intelligence/forecast/uncertainty/uncertainty_engine.py
=============================================================
UncertaintyEngine — quantifies aleatoric, epistemic, model,
data, and parameter uncertainty for a given forecast.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from typing import Any

from ..hypothesis_constants import UncertaintyType
from ..forecast.forecast_result import ForecastResult


@dataclass
class UncertaintyComponent:
    """A single uncertainty dimension estimate."""

    uncertainty_type: UncertaintyType
    value:            float            # total uncertainty [0, 1]
    description:      str              = ""
    metadata:         dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "uncertainty_type": self.uncertainty_type.value,
            "value":            round(self.value, 4),
            "description":      self.description,
            "metadata":         self.metadata,
        }


@dataclass
class UncertaintyReport:
    """Aggregated uncertainty across all dimensions."""

    forecast_id:  str                        = ""
    components:   list[UncertaintyComponent] = field(default_factory=list)
    total:        float                      = 0.0   # [0, 1] – higher = more uncertain
    confidence:   float                      = 0.0   # 1 - total
    metadata:     dict[str, Any]             = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "forecast_id": self.forecast_id,
            "components":  [c.to_dict() for c in self.components],
            "total":       round(self.total, 4),
            "confidence":  round(self.confidence, 4),
            "metadata":    self.metadata,
        }


class UncertaintyEngine:
    """
    Decomposes forecast uncertainty into five dimensions and aggregates
    them into a single UncertaintyReport.

    Each component is estimated from proxy signals available in
    ForecastResult (range width, confidence, model confidence, etc.).
    Domain-specific uncertainty can be injected via ``inject_component``.
    """

    def __init__(self) -> None:
        self._lock:     threading.RLock = threading.RLock()
        self._injected: dict[str, list[UncertaintyComponent]] = {}

    # -- Estimation ────────────────────────────────────────────────────────────

    def estimate(self, forecast: ForecastResult) -> UncertaintyReport:
        """
        Estimate all uncertainty dimensions from a ForecastResult.
        Returns an UncertaintyReport.
        """
        aleatoric  = self._aleatoric(forecast)
        epistemic  = self._epistemic(forecast)
        model      = self._model(forecast)
        data       = self._data(forecast)
        parameter  = self._parameter(forecast)

        components = [aleatoric, epistemic, model, data, parameter]

        with self._lock:
            injected = list(self._injected.get(forecast.forecast_id, []))
        components.extend(injected)

        # Aggregate — weighted RMS so larger uncertainties dominate
        total = math.sqrt(
            sum(c.value ** 2 for c in components) / len(components)
        ) if components else 0.0
        total = min(1.0, total)

        return UncertaintyReport(
            forecast_id = forecast.forecast_id,
            components  = components,
            total       = total,
            confidence  = max(0.0, 1.0 - total),
        )

    def estimate_from_values(
        self,
        forecast_id:     str,
        value:           float,
        range_low:       float,
        range_high:      float,
        model_confidence: float = 0.5,
    ) -> UncertaintyReport:
        """Lightweight path that does not require a full ForecastResult."""
        from ..forecast.forecast_result import ForecastResult as FR
        from ..hypothesis_constants import ForecastHorizon, ForecastType
        dummy = FR(
            forecast_id = forecast_id,
            value       = value,
            range_low   = range_low,
            range_high  = range_high,
            confidence  = model_confidence,
        )
        return self.estimate(dummy)

    # -- Inject custom component ───────────────────────────────────────────────

    def inject_component(
        self,
        forecast_id:      str,
        uncertainty_type: UncertaintyType,
        value:            float,
        description:      str = "",
        metadata:         dict[str, Any] | None = None,
    ) -> None:
        comp = UncertaintyComponent(
            uncertainty_type = uncertainty_type,
            value            = max(0.0, min(1.0, value)),
            description      = description,
            metadata         = metadata or {},
        )
        with self._lock:
            self._injected.setdefault(forecast_id, []).append(comp)

    # -- Private estimators ────────────────────────────────────────────────────

    @staticmethod
    def _aleatoric(f: ForecastResult) -> UncertaintyComponent:
        """Inherent randomness — proxy: relative range width."""
        if f.value != 0:
            rel = (f.range_high - f.range_low) / (2.0 * abs(f.value))
        else:
            rel = (f.range_high - f.range_low)
        value = min(1.0, rel * 0.5)
        return UncertaintyComponent(
            uncertainty_type = UncertaintyType.ALEATORIC,
            value            = value,
            description      = "Inherent randomness (relative range width)",
        )

    @staticmethod
    def _epistemic(f: ForecastResult) -> UncertaintyComponent:
        """Model ignorance — proxy: inverse of model confidence."""
        value = max(0.0, 1.0 - f.confidence)
        return UncertaintyComponent(
            uncertainty_type = UncertaintyType.EPISTEMIC,
            value            = value * 0.8,
            description      = "Model ignorance (1 - model confidence)",
        )

    @staticmethod
    def _model(f: ForecastResult) -> UncertaintyComponent:
        """Model mis-specification — proxy: constant baseline."""
        return UncertaintyComponent(
            uncertainty_type = UncertaintyType.MODEL,
            value            = 0.1,
            description      = "Model specification risk (baseline)",
        )

    @staticmethod
    def _data(f: ForecastResult) -> UncertaintyComponent:
        """Data quality — from metadata if present, else baseline."""
        value = float(f.metadata.get("data_quality_uncertainty", 0.05))
        return UncertaintyComponent(
            uncertainty_type = UncertaintyType.DATA,
            value            = min(1.0, max(0.0, value)),
            description      = "Data quality uncertainty",
        )

    @staticmethod
    def _parameter(f: ForecastResult) -> UncertaintyComponent:
        """Parameter estimation — from CI width relative to range."""
        ci_w  = f.range_width
        scale = abs(f.value) if f.value != 0 else 1.0
        value = min(1.0, (ci_w / scale) * 0.25) if scale else 0.05
        return UncertaintyComponent(
            uncertainty_type = UncertaintyType.PARAMETER,
            value            = value,
            description      = "Parameter estimation uncertainty",
        )

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {"injected_entries": len(self._injected)}


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:   threading.Lock              = threading.Lock()
_ENGINE: UncertaintyEngine | None   = None


def get_uncertainty_engine() -> UncertaintyEngine:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = UncertaintyEngine()
    return _ENGINE


def reset_uncertainty_engine() -> None:
    global _ENGINE
    with _LOCK:
        _ENGINE = None
