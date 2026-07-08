"""
iios/intelligence/forecast/evaluation/forecast_evaluator.py
===========================================================
ForecastEvaluator — scores a forecast against its actual outcome
and stores the result in ForecastTracker + ModelFeedback.
"""
from __future__ import annotations

import threading
from typing import Any

from .forecast_tracker import ForecastTracker, TrackedOutcome, get_forecast_tracker
from .model_feedback import ModelFeedback, get_model_feedback
from .prediction_accuracy import AccuracyReport, compute_accuracy
from ..hypothesis_exceptions import NoForecastToEvaluateError
from ..forecast.forecast_registry import ForecastRegistry, get_forecast_registry
from ..forecast.forecast_result import ForecastResult


class ForecastEvaluator:
    """
    Evaluates forecast accuracy when actual outcomes are known.
    Persists results to ForecastTracker and ModelFeedback.
    """

    def __init__(self) -> None:
        self._registry: ForecastRegistry = get_forecast_registry()
        self._tracker:  ForecastTracker   = get_forecast_tracker()
        self._feedback: ModelFeedback     = get_model_feedback()
        self._lock:     threading.RLock   = threading.RLock()

    # -- Evaluate ──────────────────────────────────────────────────────────────

    def evaluate(
        self,
        forecast_id:  str,
        actual_value: float,
    ) -> AccuracyReport:
        """
        Score forecast against actual_value.
        Updates the ForecastResult.is_evaluated flag in the registry.
        """
        result = self._registry.get(forecast_id)

        report = compute_accuracy(
            forecast_id  = forecast_id,
            predicted    = result.value,
            actual       = actual_value,
            range_low    = result.range_low,
            range_high   = result.range_high,
        )

        # Persist actual on the ForecastResult
        result.actual_value = actual_value
        result.is_evaluated = True

        # Track in history
        self._tracker.record(TrackedOutcome(
            forecast_id = forecast_id,
            model_id    = result.model_id,
            predicted   = result.value,
            actual      = actual_value,
            composite   = report.composite,
        ))

        # Feed back to model diagnostics
        self._feedback.record(result.model_id, report)

        return report

    def evaluate_by_result(
        self,
        result:       ForecastResult,
        actual_value: float,
    ) -> AccuracyReport:
        """Evaluate without requiring the result to be in the registry."""
        report = compute_accuracy(
            forecast_id  = result.forecast_id,
            predicted    = result.value,
            actual       = actual_value,
            range_low    = result.range_low,
            range_high   = result.range_high,
        )
        result.actual_value = actual_value
        result.is_evaluated = True

        self._tracker.record(TrackedOutcome(
            forecast_id = result.forecast_id,
            model_id    = result.model_id,
            predicted   = result.value,
            actual      = actual_value,
            composite   = report.composite,
        ))
        self._feedback.record(result.model_id, report)
        return report

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "tracker":  self._tracker.stats(),
            "feedback": self._feedback.stats(),
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:      threading.Lock             = threading.Lock()
_EVALUATOR: ForecastEvaluator | None  = None


def get_forecast_evaluator() -> ForecastEvaluator:
    global _EVALUATOR
    if _EVALUATOR is None:
        with _LOCK:
            if _EVALUATOR is None:
                _EVALUATOR = ForecastEvaluator()
    return _EVALUATOR


def reset_forecast_evaluator() -> None:
    global _EVALUATOR
    with _LOCK:
        _EVALUATOR = None
