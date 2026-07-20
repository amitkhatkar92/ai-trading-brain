"""
iios/execution/analytics/predictive/predictive_scorer.py
========================================================
PredictiveScorer — scores and validates forecast confidence, assigns
ConfidenceLevels, and adjusts bounds based on scoring criteria.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import List

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import FORECASTER_SYSTEM_ID, ConfidenceLevel, confidence_to_level
from .exceptions import PredictiveEngineNotRunningError
from .predictive_response import Forecast

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class PredictiveScorer(LifecycleAwareMixin):
    """
    Scores forecast confidence and provides aggregate scoring metrics.

    Thread-safe.  Must be started before use.
    """

    def _on_start(self) -> None:
        _log.info("PredictiveScorer started.", system_id=FORECASTER_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("PredictiveScorer stopped.", system_id=FORECASTER_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PredictiveEngineNotRunningError()

    def score(self, forecast: Forecast) -> ConfidenceLevel:
        """Return the ConfidenceLevel for a single forecast."""
        self._assert_running()
        return confidence_to_level(forecast.confidence)

    def score_all(self, forecasts: List[Forecast]) -> List[ConfidenceLevel]:
        """Return ConfidenceLevel for each forecast in the list."""
        self._assert_running()
        return [self.score(f) for f in forecasts]

    def average_confidence(self, forecasts: List[Forecast]) -> float:
        """Compute the mean confidence across all forecasts."""
        self._assert_running()
        if not forecasts:
            return 0.0
        return sum(f.confidence for f in forecasts) / len(forecasts)

    def high_confidence_count(self, forecasts: List[Forecast]) -> int:
        """Count forecasts at HIGH confidence level."""
        self._assert_running()
        return sum(1 for f in forecasts if f.confidence >= 0.80)

    def low_confidence_count(self, forecasts: List[Forecast]) -> int:
        """Count forecasts at LOW or VERY_LOW confidence level."""
        self._assert_running()
        return sum(1 for f in forecasts if f.confidence < 0.60)

    def validate_confidence_bounds(self, forecast: Forecast) -> bool:
        """
        Validate that all forecast points have consistent confidence bounds.

        Returns True if all points have lower_bound <= value <= upper_bound.
        """
        self._assert_running()
        for pt in forecast.forecast_points:
            if pt.lower_bound > pt.value or pt.value > pt.upper_bound:
                return False
        return True
