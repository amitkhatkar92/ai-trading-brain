"""iios/execution/monitoring/metrics/metrics_aggregator.py
==================================================
MetricsAggregator — time-window and cross-window aggregation for metrics.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from .constants import (
    AggregationType,
    MetricType,
    WindowSize,
)
from .metrics_calculator import MetricsCalculator
from .metrics_collector import MetricsCollector


# ── Dispatch table: AggregationType → calculator method ──────────────────────

_AGGREGATION_DISPATCH = {
    AggregationType.SUM:     MetricsCalculator.calculate_sum,
    AggregationType.AVERAGE: MetricsCalculator.calculate_average,
    AggregationType.MEDIAN:  MetricsCalculator.calculate_median,
    AggregationType.MIN:     MetricsCalculator.calculate_min,
    AggregationType.MAX:     MetricsCalculator.calculate_max,
    AggregationType.COUNT:   MetricsCalculator.calculate_count,
    AggregationType.P95:     MetricsCalculator.calculate_p95,
    AggregationType.P99:     MetricsCalculator.calculate_p99,
    AggregationType.STD_DEV: MetricsCalculator.calculate_std_dev,
}


class MetricsAggregator:
    """
    Aggregates metric values over rolling time windows.

    Uses MetricsCollector to source raw data and MetricsCalculator
    to apply aggregation functions.  Stateless beyond holding
    references to the injected collector.
    """

    def __init__(self, collector: MetricsCollector) -> None:
        self._collector = collector

    # ── Single metric aggregation ─────────────────────────────────────────────

    def aggregate(
        self,
        values:   List[float],
        agg_type: AggregationType,
    ) -> float:
        """
        Apply ``agg_type`` aggregation to ``values``.

        Special case: RATE uses sum/count of the list as a proxy
        when called directly on raw values.
        """
        if agg_type == AggregationType.RATE:
            # Rate over raw values: average of values (each value is a rate)
            return MetricsCalculator.calculate_average(values)
        fn = _AGGREGATION_DISPATCH.get(agg_type)
        if fn is None:
            return MetricsCalculator.calculate_average(values)
        return fn(values)

    def aggregate_window(
        self,
        session_id:  str,
        metric_type: MetricType,
        window_size: WindowSize,
        agg_type:    AggregationType,
    ) -> float:
        """
        Collect windowed values for (session, metric) and apply ``agg_type``.
        """
        values = self._collector.collect_windowed(
            session_id, metric_type, window_size
        )
        return self.aggregate(values, agg_type)

    # ── All-metrics aggregation ───────────────────────────────────────────────

    def aggregate_all_windows(
        self,
        session_id:   str,
        metric_types: List[MetricType],
        windows:      Optional[List[WindowSize]] = None,
        agg_map:      Optional[Dict[MetricType, AggregationType]] = None,
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute aggregated values for each (window, metric_type) combination.

        Returns Dict[window_size.value → Dict[metric_type.value → float]].
        """
        from .constants import METRIC_DEFAULT_AGGREGATION  # avoid circular at module top

        if windows is None:
            windows = [WindowSize.ONE_MINUTE, WindowSize.FIVE_MINUTES,
                       WindowSize.FIFTEEN_MINUTES, WindowSize.ONE_HOUR]
        result: Dict[str, Dict[str, float]] = {}
        for window in windows:
            window_result: Dict[str, float] = {}
            for mt in metric_types:
                agg_type = (agg_map or {}).get(
                    mt, METRIC_DEFAULT_AGGREGATION.get(mt, AggregationType.AVERAGE)
                )
                window_result[mt.value] = self.aggregate_window(
                    session_id, mt, window, agg_type
                )
            result[window.value] = window_result
        return result

    def aggregate_all_session(
        self,
        session_id:   str,
        metric_types: List[MetricType],
        agg_map:      Optional[Dict[MetricType, AggregationType]] = None,
    ) -> Dict[str, float]:
        """
        Compute session-wide (all points) aggregated value for each metric.

        Returns Dict[metric_type.value → float].
        """
        from .constants import METRIC_DEFAULT_AGGREGATION

        result: Dict[str, float] = {}
        for mt in metric_types:
            agg_type = (agg_map or {}).get(
                mt, METRIC_DEFAULT_AGGREGATION.get(mt, AggregationType.AVERAGE)
            )
            values = self._collector.collect(session_id, mt)
            result[mt.value] = self.aggregate(values, agg_type)
        return result
