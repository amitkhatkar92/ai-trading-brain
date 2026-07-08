"""
iios/intelligence/forecast/forecast/forecast_engine.py
=======================================================
ForecastEngine — runs a model against inputs and stores the result.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from .forecast_model import ForecastModel, PointForecastModel, ForecastModelConfig
from .forecast_registry import ForecastRegistry, get_forecast_registry
from .forecast_result import ForecastResult
from ..hypothesis_constants import (
    ForecastHorizon,
    ForecastType,
    DEFAULT_CONFIDENCE_INTERVAL,
    DEFAULT_FORECAST_TTL_S,
)
from ..hypothesis_exceptions import (
    ForecastModelError,
    InsufficientDataError,
)


class ForecastEngine:
    """
    Runs registered ForecastModel instances and persists results.
    Plug-in point for domain-specific forecast modules.
    """

    def __init__(self) -> None:
        self._models:   dict[str, ForecastModel] = {}
        self._registry: ForecastRegistry          = get_forecast_registry()
        self._lock:     threading.RLock            = threading.RLock()
        self._counter:  int                        = 0

        # Register a sensible default
        default_cfg    = ForecastModelConfig(model_id="default", name="PointForecastModel")
        self._default_model = PointForecastModel(config=default_cfg)
        self._models["default"] = self._default_model

    # -- Model registration ────────────────────────────────────────────────────

    def register_model(self, model: ForecastModel) -> None:
        with self._lock:
            self._models[model.model_id] = model

    def unregister_model(self, model_id: str) -> None:
        with self._lock:
            self._models.pop(model_id, None)

    def list_models(self) -> list[str]:
        with self._lock:
            return list(self._models.keys())

    # -- Core forecast ─────────────────────────────────────────────────────────

    def run(
        self,
        hypothesis_id:       str,
        inputs:              dict[str, Any],
        model_id:            str              = "default",
        horizon:             ForecastHorizon  = ForecastHorizon.SHORT_TERM,
        forecast_type:       ForecastType     = ForecastType.POINT,
        confidence_interval: float            = DEFAULT_CONFIDENCE_INTERVAL,
        ttl_s:               float            = DEFAULT_FORECAST_TTL_S,
    ) -> ForecastResult:
        """
        Execute model and store the ForecastResult.
        Thread-safe.
        """
        with self._lock:
            model = self._models.get(model_id)
            if model is None:
                raise ForecastModelError(f"Model {model_id!r} not registered")
            if model.config.min_data_points > 0:
                n = len(inputs.get("data", inputs))
                if isinstance(inputs.get("data"), (list, tuple)):
                    n = len(inputs["data"])
                else:
                    n = 1
                if n < model.config.min_data_points:
                    raise InsufficientDataError(model.config.min_data_points, n)

        t0 = time.monotonic()
        try:
            raw = model.predict(inputs)
        except (ForecastModelError, InsufficientDataError):
            raise
        except Exception as exc:
            raise ForecastModelError(str(exc)) from exc

        elapsed_ms = (time.monotonic() - t0) * 1_000.0

        result = ForecastResult(
            hypothesis_id       = hypothesis_id,
            model_id            = model_id,
            horizon             = horizon,
            forecast_type       = forecast_type,
            value               = float(raw.get("value", 0.0)),
            range_low           = float(raw.get("range_low", 0.0)),
            range_high          = float(raw.get("range_high", 0.0)),
            probability         = float(raw.get("probability", 0.5)),
            confidence          = float(raw.get("confidence", 0.5)),
            confidence_interval = confidence_interval,
            ttl_s               = ttl_s,
            metadata            = {"elapsed_ms": round(elapsed_ms, 2)},
        )

        self._registry.add(result)
        with self._lock:
            self._counter += 1
        return result

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            model_count = len(self._models)
            counter     = self._counter
        return {
            "models_registered": model_count,
            "forecasts_run":     counter,
            "registry":          self._registry.stats(),
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:   threading.Lock           = threading.Lock()
_ENGINE: ForecastEngine | None   = None


def get_forecast_engine() -> ForecastEngine:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = ForecastEngine()
    return _ENGINE


def reset_forecast_engine() -> None:
    global _ENGINE
    with _LOCK:
        _ENGINE = None
