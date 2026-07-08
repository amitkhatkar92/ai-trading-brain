"""
iios/intelligence/forecast/forecast/forecast_registry.py
=========================================================
Thread-safe store for ForecastResult objects.
"""
from __future__ import annotations

import threading
from typing import Any

from .forecast_result import ForecastResult
from ..hypothesis_constants import MAX_FORECASTS
from ..hypothesis_exceptions import ForecastNotFoundError


class ForecastAlreadyExistsError(Exception):
    code = "HFE-025"

    def __init__(self, forecast_id: str) -> None:
        super().__init__(f"[{self.code}] Forecast already exists: {forecast_id!r}")


class ForecastRegistry:
    """Thread-safe store for ForecastResult instances."""

    def __init__(self) -> None:
        self._store:        dict[str, ForecastResult]  = {}
        self._by_hyp:       dict[str, list[str]]       = {}
        self._lock:         threading.RLock             = threading.RLock()

    # -- Write ─────────────────────────────────────────────────────────────────

    def add(self, result: ForecastResult, overwrite: bool = False) -> None:
        with self._lock:
            if not overwrite and result.forecast_id in self._store:
                raise ForecastAlreadyExistsError(result.forecast_id)
            if len(self._store) >= MAX_FORECASTS and result.forecast_id not in self._store:
                raise OverflowError(f"ForecastRegistry full (max {MAX_FORECASTS})")
            self._store[result.forecast_id] = result
            ids = self._by_hyp.setdefault(result.hypothesis_id, [])
            if result.forecast_id not in ids:
                ids.append(result.forecast_id)

    def remove(self, forecast_id: str) -> None:
        with self._lock:
            r = self._store.pop(forecast_id, None)
            if r and r.hypothesis_id in self._by_hyp:
                try:
                    self._by_hyp[r.hypothesis_id].remove(forecast_id)
                except ValueError:
                    pass

    # -- Read ──────────────────────────────────────────────────────────────────

    def get(self, forecast_id: str) -> ForecastResult:
        with self._lock:
            r = self._store.get(forecast_id)
        if r is None:
            raise ForecastNotFoundError(forecast_id)
        return r

    def has(self, forecast_id: str) -> bool:
        with self._lock:
            return forecast_id in self._store

    def for_hypothesis(self, hypothesis_id: str) -> list[ForecastResult]:
        with self._lock:
            ids = list(self._by_hyp.get(hypothesis_id, []))
            return [self._store[i] for i in ids if i in self._store]

    def all(self) -> list[ForecastResult]:
        with self._lock:
            return list(self._store.values())

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total     = len(self._store)
            evaluated = sum(1 for r in self._store.values() if r.is_evaluated)
            return {
                "total":     total,
                "evaluated": evaluated,
                "pending":   total - evaluated,
            }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:     threading.Lock              = threading.Lock()
_REGISTRY: ForecastRegistry | None    = None


def get_forecast_registry() -> ForecastRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        with _LOCK:
            if _REGISTRY is None:
                _REGISTRY = ForecastRegistry()
    return _REGISTRY


def reset_forecast_registry() -> None:
    global _REGISTRY
    with _LOCK:
        _REGISTRY = None
