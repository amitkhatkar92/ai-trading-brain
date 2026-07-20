"""
iios/execution/analytics/predictive/predictive_trend_engine.py
==============================================================
PredictiveTrendEngine — analyses historical operational data for
directional trends and extrapolates forward.

"IMPROVING" means the metric is moving toward healthier values.
"DEGRADING" means the metric is moving toward worse values.

Distinction from M3 TrendAnalyzer:
  - M3 classifies historical trends (backward-looking)
  - This engine classifies forecast trends (forward-looking) and maps
    metric direction to operational significance.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import math
import uuid
from typing import Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    FORECASTER_SYSTEM_ID,
    ForecastHorizon,
    PredictionDomain,
    PredictionType,
    TrendType,
)
from .exceptions import PredictiveEngineNotRunningError
from .predictive_forecaster import _mean, _ols_slope_intercept, _std_dev

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})

# For ratio-type predictions (higher = better): improving = slope > 0
_HIGHER_IS_BETTER = {
    PredictionType.BROKER_AVAILABILITY_FORECAST,
    PredictionType.RECOVERY_PROBABILITY,
    PredictionType.OPERATIONAL_HEALTH_SCORE,
}

# For rate/saturation-type predictions (lower = better): improving = slope < 0
_LOWER_IS_BETTER = {
    PredictionType.FAILURE_PROBABILITY,
    PredictionType.GATEWAY_SATURATION,
    PredictionType.PERFORMANCE_DEGRADATION_RISK,
}


class PredictiveTrendEngine(LifecycleAwareMixin):
    """
    Classifies forecast trends and maps direction to operational significance.

    Thread-safe.  Must be started before use.
    """

    def _on_start(self) -> None:
        _log.info("PredictiveTrendEngine started.", system_id=FORECASTER_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("PredictiveTrendEngine stopped.", system_id=FORECASTER_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PredictiveEngineNotRunningError()

    def analyze(
        self,
        prediction_type:   PredictionType,
        values:            List[float],
        domain:            PredictionDomain,
    ) -> TrendType:
        """
        Classify the trend for a single prediction type.

        Parameters
        ----------
        prediction_type: The metric being analysed.
        values:          Historical time-series (oldest first).
        domain:          Prediction domain.
        """
        self._assert_running()
        if len(values) < 2:
            return TrendType.UNKNOWN
        mean_val = _mean(values)
        std      = _std_dev(values)
        slope, _ = _ols_slope_intercept(values)
        cv       = (std / abs(mean_val)) if mean_val != 0 else 0.0
        if cv > 0.5:
            return TrendType.VOLATILE
        threshold = abs(mean_val * 0.01) if mean_val != 0 else 1e-9
        if abs(slope) <= threshold:
            return TrendType.STABLE
        # Map slope direction to IMPROVING/DEGRADING based on metric semantics
        if prediction_type in _HIGHER_IS_BETTER:
            return TrendType.IMPROVING if slope > 0 else TrendType.DEGRADING
        if prediction_type in _LOWER_IS_BETTER:
            return TrendType.IMPROVING if slope < 0 else TrendType.DEGRADING
        # Default: use raw slope direction
        return TrendType.IMPROVING if slope > 0 else TrendType.DEGRADING

    def analyze_all(
        self,
        historical_analytics: Dict[str, List[float]],
        domain:               PredictionDomain,
    ) -> Dict[PredictionType, TrendType]:
        """
        Classify trends for all available prediction types.

        Input: {prediction_type_value_string: [float, ...]}
        Output: {PredictionType: TrendType}
        """
        self._assert_running()
        result: Dict[PredictionType, TrendType] = {}
        for key, values in historical_analytics.items():
            try:
                pt = PredictionType(key)
            except ValueError:
                continue
            result[pt] = self.analyze(pt, values, domain)
        return result

    def dominant_trend(
        self,
        trends: Dict[PredictionType, TrendType],
    ) -> TrendType:
        """
        Return the dominant trend across all prediction types.

        Counts IMPROVING/DEGRADING/STABLE/VOLATILE; returns the most common.
        DEGRADING takes priority over STABLE when tied.
        """
        if not trends:
            return TrendType.UNKNOWN
        counts: Dict[TrendType, int] = {}
        for t in trends.values():
            counts[t] = counts.get(t, 0) + 1
        if not counts:
            return TrendType.UNKNOWN
        max_count = max(counts.values())
        # Priority in case of tie: DEGRADING > VOLATILE > STABLE > IMPROVING
        for priority in [TrendType.DEGRADING, TrendType.VOLATILE, TrendType.STABLE, TrendType.IMPROVING]:
            if counts.get(priority, 0) == max_count:
                return priority
        return TrendType.UNKNOWN
