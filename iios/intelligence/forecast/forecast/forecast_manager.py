"""
iios/intelligence/forecast/forecast/forecast_manager.py
=========================================================
ForecastManager — lifecycle management for forecasts.
Thin orchestration layer above ForecastEngine + ForecastRegistry.
"""
from __future__ import annotations

import threading
from typing import Any

from .forecast_engine import ForecastEngine, get_forecast_engine
from .forecast_registry import ForecastRegistry, get_forecast_registry
from .forecast_result import ForecastResult
from ..hypothesis_constants import (
    ForecastHorizon,
    ForecastType,
    DEFAULT_CONFIDENCE_INTERVAL,
    DEFAULT_FORECAST_TTL_S,
)
from ..hypothesis_exceptions import ForecastNotFoundError


class ForecastManager:
    """
    Top-level interface for forecast creation, retrieval, and annotation.
    """

    def __init__(self) -> None:
        self._engine:   ForecastEngine   = get_forecast_engine()
        self._registry: ForecastRegistry = get_forecast_registry()
        self._lock:     threading.RLock   = threading.RLock()

    # -- Create ────────────────────────────────────────────────────────────────

    def forecast(
        self,
        hypothesis_id:       str,
        inputs:              dict[str, Any],
        model_id:            str              = "default",
        horizon:             ForecastHorizon  = ForecastHorizon.SHORT_TERM,
        forecast_type:       ForecastType     = ForecastType.POINT,
        confidence_interval: float            = DEFAULT_CONFIDENCE_INTERVAL,
        ttl_s:               float            = DEFAULT_FORECAST_TTL_S,
    ) -> ForecastResult:
        return self._engine.run(
            hypothesis_id       = hypothesis_id,
            inputs              = inputs,
            model_id            = model_id,
            horizon             = horizon,
            forecast_type       = forecast_type,
            confidence_interval = confidence_interval,
            ttl_s               = ttl_s,
        )

    # -- Read ──────────────────────────────────────────────────────────────────

    def get(self, forecast_id: str) -> ForecastResult:
        return self._registry.get(forecast_id)

    def for_hypothesis(self, hypothesis_id: str) -> list[ForecastResult]:
        return self._registry.for_hypothesis(hypothesis_id)

    def all(self) -> list[ForecastResult]:
        return self._registry.all()

    # -- Annotate / update ─────────────────────────────────────────────────────

    def record_actual(self, forecast_id: str, actual_value: float) -> ForecastResult:
        """Record an observed outcome so the evaluator can score this forecast."""
        result = self._registry.get(forecast_id)
        result.actual_value = actual_value
        result.is_evaluated = True
        return result

    def add_note(self, forecast_id: str, note: str) -> None:
        result = self._registry.get(forecast_id)
        result.notes.append(note)

    # -- Model registration ────────────────────────────────────────────────────

    def register_model(self, model: Any) -> None:
        self._engine.register_model(model)

    def list_models(self) -> list[str]:
        return self._engine.list_models()

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return self._engine.stats()


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:    threading.Lock             = threading.Lock()
_MANAGER: ForecastManager | None    = None


def get_forecast_manager() -> ForecastManager:
    global _MANAGER
    if _MANAGER is None:
        with _LOCK:
            if _MANAGER is None:
                _MANAGER = ForecastManager()
    return _MANAGER


def reset_forecast_manager() -> None:
    global _MANAGER
    with _LOCK:
        _MANAGER = None
