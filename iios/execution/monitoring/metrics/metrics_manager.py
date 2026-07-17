"""iios/execution/monitoring/metrics/metrics_manager.py
==================================================
MetricsManager — LifecycleAwareMixin orchestrator for data collection
and metric computation.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    MANAGER_SYSTEM_ID,
    METRIC_DEFAULT_AGGREGATION,
    AggregationType,
    MetricType,
    WindowSize,
)
from .exceptions import MetricCalculationError, MetricsEngineNotRunningError
from .metrics_aggregator import MetricsAggregator
from .metrics_calculator import MetricsCalculator
from .metrics_collector import MetricPoint, MetricsCollector

_log = get_logger(__name__)


class MetricsManager(LifecycleAwareMixin):
    """
    Orchestrates raw data collection and metric computation.

    Owns a MetricsCollector (raw data) and a MetricsAggregator
    (window / cross-window computation).  No I/O, no events.
    """

    def __init__(
        self,
        max_points_per_series: int = 10_000,
    ) -> None:
        super().__init__()
        self._collector  = MetricsCollector(
            max_points_per_series=max_points_per_series
        )
        self._aggregator = MetricsAggregator(self._collector)

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("MetricsManager starting.", system_id=MANAGER_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info(
            "MetricsManager stopping.",
            system_id=MANAGER_SYSTEM_ID,
            total_points=self._collector.total_points(),
        )

    def _assert_running(self) -> None:
        state = self.lifecycle_state()
        if state not in (EngineState.RUNNING, "running"):
            raise MetricsEngineNotRunningError()

    # ── Data ingestion ────────────────────────────────────────────────────────

    def record(
        self,
        session_id:  str,
        metric_type: MetricType,
        value:       float,
        *,
        timestamp: Optional[float]         = None,
        tags:      Optional[Dict[str, str]] = None,
    ) -> MetricPoint:
        self._assert_running()
        return self._collector.record(
            session_id, metric_type, value,
            timestamp=timestamp, tags=tags
        )

    # ── Single metric computation ─────────────────────────────────────────────

    def compute_metric(
        self,
        session_id:  str,
        metric_type: MetricType,
        window_size: WindowSize,
        agg_type:    Optional[AggregationType] = None,
    ) -> float:
        self._assert_running()
        if agg_type is None:
            agg_type = METRIC_DEFAULT_AGGREGATION.get(
                metric_type, AggregationType.AVERAGE
            )
        try:
            return self._aggregator.aggregate_window(
                session_id, metric_type, window_size, agg_type
            )
        except Exception as exc:
            raise MetricCalculationError(
                metric_type.value, str(exc)
            ) from exc

    # ── All-metrics computation ───────────────────────────────────────────────

    def compute_all_session(
        self,
        session_id:   str,
        metric_types: Optional[List[MetricType]] = None,
    ) -> Dict[str, float]:
        """
        Compute session-wide aggregated value for each metric in
        ``metric_types`` (all known types if None).
        """
        self._assert_running()
        if metric_types is None:
            metric_types = list(MetricType)
        return self._aggregator.aggregate_all_session(session_id, metric_types)

    def compute_window_metrics(
        self,
        session_id:   str,
        metric_types: Optional[List[MetricType]] = None,
        windows:      Optional[List[WindowSize]]  = None,
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute per-window aggregated values for each metric.

        Returns Dict[window_size.value → Dict[metric_type.value → float]].
        """
        self._assert_running()
        if metric_types is None:
            metric_types = list(MetricType)
        return self._aggregator.aggregate_all_windows(
            session_id, metric_types, windows
        )

    def compute_point_counts(
        self,
        session_id:   str,
        metric_types: Optional[List[MetricType]] = None,
    ) -> Dict[str, int]:
        """Return raw point count per metric type."""
        self._assert_running()
        if metric_types is None:
            metric_types = list(MetricType)
        return {
            mt.value: self._collector.count(session_id, mt)
            for mt in metric_types
        }

    # ── Collector access ──────────────────────────────────────────────────────

    def raw_values(
        self,
        session_id:  str,
        metric_type: MetricType,
        *,
        limit: Optional[int] = None,
    ) -> List[float]:
        self._assert_running()
        return self._collector.collect(session_id, metric_type, limit=limit)

    def clear_session(self, session_id: str) -> None:
        self._assert_running()
        self._collector.remove_session(session_id)

    @property
    def total_points(self) -> int:
        return self._collector.total_points()

    @property
    def series_count(self) -> int:
        return self._collector.series_count()
