"""
iios/intelligence/forecast/evaluation/forecast_tracker.py
==========================================================
ForecastTracker — records forecast outcomes over time for trend analysis.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrackedOutcome:
    """One (forecast, actual) data point."""

    forecast_id:  str
    model_id:     str
    predicted:    float
    actual:       float
    composite:    float    # accuracy score [0, 1]
    recorded_at:  float    = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "forecast_id":  self.forecast_id,
            "model_id":     self.model_id,
            "predicted":    round(self.predicted, 6),
            "actual":       round(self.actual, 6),
            "composite":    round(self.composite, 4),
            "recorded_at":  self.recorded_at,
        }


class ForecastTracker:
    """
    Maintains a rolling history of forecast outcomes.
    Exposes rolling accuracy metrics per model_id.
    """

    def __init__(self, max_history: int = 10_000) -> None:
        self._history:     list[TrackedOutcome]          = []
        self._by_model:    dict[str, list[TrackedOutcome]] = {}
        self._max:         int                            = max_history
        self._lock:        threading.RLock                = threading.RLock()

    # -- Record ────────────────────────────────────────────────────────────────

    def record(self, outcome: TrackedOutcome) -> None:
        with self._lock:
            self._history.append(outcome)
            if len(self._history) > self._max:
                oldest = self._history.pop(0)
                bucket = self._by_model.get(oldest.model_id, [])
                if bucket and oldest in bucket:
                    bucket.remove(oldest)
            self._by_model.setdefault(outcome.model_id, []).append(outcome)

    # -- Read ──────────────────────────────────────────────────────────────────

    def history(self, model_id: str | None = None) -> list[TrackedOutcome]:
        with self._lock:
            if model_id is None:
                return list(self._history)
            return list(self._by_model.get(model_id, []))

    def rolling_accuracy(
        self,
        model_id: str | None = None,
        n_last:   int         = 100,
    ) -> float:
        outcomes = self.history(model_id)[-n_last:]
        if not outcomes:
            return 0.0
        return sum(o.composite for o in outcomes) / len(outcomes)

    def model_ids(self) -> list[str]:
        with self._lock:
            return list(self._by_model.keys())

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_outcomes":  len(self._history),
                "models_tracked":  len(self._by_model),
            }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:    threading.Lock           = threading.Lock()
_TRACKER: ForecastTracker | None  = None


def get_forecast_tracker() -> ForecastTracker:
    global _TRACKER
    if _TRACKER is None:
        with _LOCK:
            if _TRACKER is None:
                _TRACKER = ForecastTracker()
    return _TRACKER


def reset_forecast_tracker() -> None:
    global _TRACKER
    with _LOCK:
        _TRACKER = None
