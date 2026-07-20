"""
iios/execution/analytics/predictive/predictive_model_registry.py
================================================================
PredictiveModelRegistry — manages forecast model definitions.

Models define which forecasting algorithm to apply for a given
PredictionType and ForecastHorizon.  Supports versioning, fallback,
and comparison.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    FORECASTER_SYSTEM_ID,
    ForecastAlgorithm,
    ForecastHorizon,
    PredictionDomain,
    PredictionType,
)
from .exceptions import PredictionModelError, PredictiveEngineNotRunningError

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


# ── ForecastModel definition ──────────────────────────────────────────────────

@dataclass(frozen=True)
class ForecastModel:
    """
    Immutable definition of a forecast model.

    Fields
    ------
    model_id:         Unique model identifier.
    name:             Human-readable name.
    algorithm:        Forecasting algorithm.
    description:      Description.
    version:          Semantic version string.
    supported_types:  PredictionTypes this model covers (empty = all).
    supported_domains:PredictionDomains this model covers (empty = all).
    min_data_points:  Minimum historical points required.
    is_fallback:      Whether this is a fallback model.
    """

    model_id:          str
    name:              str
    algorithm:         ForecastAlgorithm
    description:       str                            = ""
    version:           str                            = "1.0.0"
    supported_types:   Tuple[PredictionType, ...]      = field(default_factory=tuple)
    supported_domains: Tuple[PredictionDomain, ...]    = field(default_factory=tuple)
    min_data_points:   int                            = 3
    is_fallback:       bool                           = False

    def supports_type(self, prediction_type: PredictionType) -> bool:
        return not self.supported_types or prediction_type in self.supported_types

    def supports_domain(self, domain: PredictionDomain) -> bool:
        return not self.supported_domains or domain in self.supported_domains


# ── Built-in models ───────────────────────────────────────────────────────────

_DEFAULT_MODELS: List[ForecastModel] = [
    ForecastModel(
        model_id    = "linear-v1",
        name        = "Linear Extrapolation v1",
        algorithm   = ForecastAlgorithm.LINEAR,
        description = "Ordinary least squares linear extrapolation.",
        min_data_points = 2,
        is_fallback = False,
    ),
    ForecastModel(
        model_id    = "exponential-v1",
        name        = "Holt's Exponential Smoothing v1",
        algorithm   = ForecastAlgorithm.EXPONENTIAL,
        description = "Double exponential smoothing with trend component.",
        min_data_points = 3,
        is_fallback = False,
    ),
    ForecastModel(
        model_id    = "hybrid-v1",
        name        = "Hybrid Linear+Exponential v1",
        algorithm   = ForecastAlgorithm.HYBRID,
        description = "Linear trend direction + exponential smoothed level.",
        min_data_points = 4,
        is_fallback = False,
    ),
    ForecastModel(
        model_id    = "fallback-v1",
        name        = "Fallback Constant Forecast v1",
        algorithm   = ForecastAlgorithm.LINEAR,
        description = "Returns last known value as the forecast.",
        min_data_points = 1,
        is_fallback = True,
    ),
]

_DEFAULT_MODEL_ID = "hybrid-v1"
_FALLBACK_MODEL_ID = "fallback-v1"


# ── Registry ──────────────────────────────────────────────────────────────────

class PredictiveModelRegistry(LifecycleAwareMixin):
    """
    Registry for ForecastModel definitions.

    Thread-safe.  Must be started before use.

    Provides:
    - Model registration and lookup
    - Best-model selection for a prediction_type + domain
    - Fallback model lookup
    """

    def __init__(self) -> None:
        super().__init__()
        self._models: Dict[str, ForecastModel] = {}
        self._lock   = threading.Lock()

    def _on_start(self) -> None:
        with self._lock:
            for model in _DEFAULT_MODELS:
                self._models[model.model_id] = model
        _log.info(
            "PredictiveModelRegistry started.",
            model_count = len(_DEFAULT_MODELS),
            system_id   = FORECASTER_SYSTEM_ID,
        )

    def _on_stop(self) -> None:
        _log.info("PredictiveModelRegistry stopped.", system_id=FORECASTER_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PredictiveEngineNotRunningError()

    # ── Public API ────────────────────────────────────────────────────────────

    def register(self, model: ForecastModel) -> None:
        """Register a new model (replaces existing model with same ID)."""
        self._assert_running()
        with self._lock:
            self._models[model.model_id] = model

    def get(self, model_id: str) -> ForecastModel:
        """Return a model by ID or raise PredictionModelError."""
        with self._lock:
            model = self._models.get(model_id)
        if model is None:
            raise PredictionModelError(f"Model not found: {model_id!r}", model_id=model_id)
        return model

    def get_best(
        self,
        prediction_type: PredictionType,
        domain:          PredictionDomain,
        data_points:     int = 0,
    ) -> ForecastModel:
        """
        Select the best model for a given prediction_type and domain.

        Preference order: hybrid → exponential → linear → fallback.
        Falls back to fallback if required data_points not met.
        """
        self._assert_running()
        _preference = [
            _DEFAULT_MODEL_ID,
            "exponential-v1",
            "linear-v1",
            _FALLBACK_MODEL_ID,
        ]
        with self._lock:
            models = dict(self._models)
        for mid in _preference:
            m = models.get(mid)
            if m and m.supports_type(prediction_type) and m.supports_domain(domain):
                if data_points >= m.min_data_points:
                    return m
        # Return fallback
        fallback = models.get(_FALLBACK_MODEL_ID)
        if fallback:
            return fallback
        raise PredictionModelError("No suitable model found.", model_id="")

    def get_fallback(self) -> ForecastModel:
        """Return the designated fallback model."""
        with self._lock:
            m = self._models.get(_FALLBACK_MODEL_ID)
        if m is None:
            raise PredictionModelError("Fallback model not found.", model_id=_FALLBACK_MODEL_ID)
        return m

    def list_models(self) -> List[ForecastModel]:
        with self._lock:
            return list(self._models.values())

    @property
    def model_count(self) -> int:
        with self._lock:
            return len(self._models)
