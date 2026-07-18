"""
iios/execution/analytics/performance/performance_trend_analyzer.py
==================================================================
PerformanceTrendAnalyzer — detects trends in historical KPI time-series
using pure-Python linear regression.

Detection logic:
  - Slope computed as: Σ(xi−x̄)(yi−ȳ) / Σ(xi−x̄)²
  - Direction: UP if slope > threshold, DOWN if slope < -threshold, else FLAT
  - VOLATILE if std_dev / mean > 0.5 (coefficient of variation)
  - Direction threshold: 1% of mean value

NO external numeric libraries.
NO predictive forecasting.

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import math
import uuid
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import CALC_SYSTEM_ID, AggregationWindow, KPIType, PerformanceDomain, TrendDirection
from .exceptions import PerformanceEngineNotRunningError, PerformanceTrendError
from .performance_calculator import _safe_mean, _std_dev
from .performance_response import TrendAnalysis

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})

# Direction threshold: slope must be > 1% of mean to be considered UP/DOWN
_SLOPE_THRESHOLD_RATIO = 0.01
# Coefficient of variation threshold to classify as VOLATILE
_CV_VOLATILE_THRESHOLD = 0.5


def _linear_regression_slope(values: List[float]) -> float:
    """Compute the linear regression slope using pure-Python arithmetic."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = _safe_mean(values)
    num   = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denom = sum((i - x_mean) ** 2 for i in range(n))
    if denom == 0.0:
        return 0.0
    return num / denom


class PerformanceTrendAnalyzer(LifecycleAwareMixin):
    """
    Analyses historical KPI values for trend direction and magnitude.

    Thread-safe.  Must be started before use.
    """

    def _on_start(self) -> None:
        _log.info("PerformanceTrendAnalyzer started.", system_id=CALC_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("PerformanceTrendAnalyzer stopped.", system_id=CALC_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PerformanceEngineNotRunningError()

    def analyze(
        self,
        kpi_type:  KPIType,
        domain:    PerformanceDomain,
        values:    List[float],
        window_seconds: float = 0.0,
    ) -> TrendAnalysis:
        """
        Analyse a time-series of KPI values and return a TrendAnalysis.

        Parameters
        ----------
        kpi_type:       KPI being analysed.
        domain:         Performance domain.
        values:         Ordered list of past KPI values (oldest first).
        window_seconds: Duration of the series in seconds.
        """
        self._assert_running()
        if not values:
            return TrendAnalysis(
                trend_id       = str(uuid.uuid4()),
                kpi_type       = kpi_type,
                domain         = domain,
                direction      = TrendDirection.FLAT,
                slope          = 0.0,
                magnitude      = 0.0,
                data_points    = 0,
                window_seconds = window_seconds,
            )

        n        = len(values)
        mean_val = _safe_mean(values)
        std      = _std_dev(values)
        slope    = _linear_regression_slope(values)
        min_val  = min(values)
        max_val  = max(values)

        # Classify direction
        threshold = abs(mean_val * _SLOPE_THRESHOLD_RATIO) if mean_val != 0 else 1e-9
        cv = (std / abs(mean_val)) if mean_val != 0 else 0.0
        if cv > _CV_VOLATILE_THRESHOLD:
            direction = TrendDirection.VOLATILE
        elif slope > threshold:
            direction = TrendDirection.UP
        elif slope < -threshold:
            direction = TrendDirection.DOWN
        else:
            direction = TrendDirection.FLAT

        # Magnitude: relative change across the series (first→last / mean)
        if n >= 2 and mean_val != 0.0:
            magnitude = abs(values[-1] - values[0]) / abs(mean_val)
            magnitude = min(1.0, magnitude)
        else:
            magnitude = 0.0

        return TrendAnalysis(
            trend_id       = str(uuid.uuid4()),
            kpi_type       = kpi_type,
            domain         = domain,
            direction      = direction,
            slope          = slope,
            magnitude      = magnitude,
            data_points    = n,
            min_value      = min_val,
            max_value      = max_val,
            mean_value     = mean_val,
            std_dev        = std,
            window_seconds = window_seconds,
        )

    def analyze_all(
        self,
        historical_data: Dict[str, List[float]],
        domain:          PerformanceDomain,
        window_seconds:  float = 0.0,
    ) -> List[TrendAnalysis]:
        """
        Analyse all KPI series in a historical_data dict.

        Input: {kpi_type_value_string: [float, ...]}
        """
        self._assert_running()
        results: List[TrendAnalysis] = []
        for kpi_str, values in historical_data.items():
            try:
                kpi_type = KPIType(kpi_str)
            except ValueError:
                continue
            if values:
                results.append(
                    self.analyze(kpi_type, domain, values, window_seconds)
                )
        return results
