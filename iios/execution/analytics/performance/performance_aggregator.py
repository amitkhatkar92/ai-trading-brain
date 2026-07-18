"""
iios/execution/analytics/performance/performance_aggregator.py
==============================================================
PerformanceAggregator — applies window aggregation to KPI values.

Supports:
  - Rolling window aggregation (mean, min, max, latest)
  - Historical aggregation over time-series data
  - Incremental updates

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import collections
import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import CALC_SYSTEM_ID, AggregationWindow, KPIType, PerformanceDomain
from .exceptions import PerformanceAggregationError, PerformanceEngineNotRunningError
from .performance_kpi import KPIValue, make_kpi_value
from .performance_calculator import _safe_mean, _percentile

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class _RollingBuffer:
    """Bounded rolling buffer of float values for a single KPI."""

    def __init__(self, maxlen: int = 1000) -> None:
        self._buf: collections.deque[float] = collections.deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def push(self, value: float) -> None:
        with self._lock:
            self._buf.append(value)

    def values(self) -> List[float]:
        with self._lock:
            return list(self._buf)

    def mean(self) -> float:
        return _safe_mean(self.values())

    def minimum(self) -> float:
        v = self.values()
        return min(v) if v else 0.0

    def maximum(self) -> float:
        v = self.values()
        return max(v) if v else 0.0

    def latest(self) -> float:
        with self._lock:
            return self._buf[-1] if self._buf else 0.0

    def count(self) -> int:
        with self._lock:
            return len(self._buf)


class PerformanceAggregator(LifecycleAwareMixin):
    """
    Aggregates KPI values over configurable time windows.

    Maintains per-KPI rolling buffers for window aggregation.
    Thread-safe.  Must be started before use.
    """

    def __init__(self, rolling_window_size: int = 1_000) -> None:
        super().__init__()
        self._rolling_window_size = rolling_window_size
        self._buffers: Dict[str, _RollingBuffer] = {}
        self._lock = threading.RLock()

    def _on_start(self) -> None:
        _log.info("PerformanceAggregator started.", system_id=CALC_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("PerformanceAggregator stopped.", system_id=CALC_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PerformanceEngineNotRunningError()

    # ── Public API ────────────────────────────────────────────────────────────

    def push(self, kpi_type: KPIType, value: float) -> None:
        """Push a new KPI value into the rolling buffer."""
        self._assert_running()
        key = kpi_type.value
        with self._lock:
            if key not in self._buffers:
                self._buffers[key] = _RollingBuffer(self._rolling_window_size)
        self._buffers[key].push(value)

    def aggregate(
        self,
        kpi_values:  Dict[KPIType, KPIValue],
        window:      AggregationWindow,
        domain:      PerformanceDomain,
    ) -> Dict[KPIType, KPIValue]:
        """
        Aggregate a set of current KPI values using the rolling buffer.

        For REAL_TIME window, the raw value is returned unchanged.
        For all other windows, the rolling mean is used.
        """
        self._assert_running()
        if window == AggregationWindow.REAL_TIME:
            return dict(kpi_values)

        result: Dict[KPIType, KPIValue] = {}
        for kpi_type, kv in kpi_values.items():
            self.push(kpi_type, kv.value)
            buf = self._buffers.get(kpi_type.value)
            if buf is None or buf.count() == 0:
                result[kpi_type] = kv
                continue
            aggregated_value = buf.mean()
            result[kpi_type] = make_kpi_value(
                kpi_type,
                aggregated_value,
                domain       = domain,
                window       = window,
                sample_count = buf.count(),
            )
        return result

    def aggregate_historical(
        self,
        historical_data: Dict[str, List[float]],
        domain:          PerformanceDomain,
        window:          AggregationWindow,
    ) -> Dict[KPIType, KPIValue]:
        """
        Aggregate historical KPI time-series data into a single KPI value per type.

        Input: {kpi_type_value_string: [float, ...]}
        Output: {KPIType: KPIValue}
        """
        self._assert_running()
        result: Dict[KPIType, KPIValue] = {}
        for kpi_str, values in historical_data.items():
            try:
                kpi_type = KPIType(kpi_str)
            except ValueError:
                continue
            if not values:
                continue
            agg_value = _safe_mean(values)
            result[kpi_type] = make_kpi_value(
                kpi_type,
                agg_value,
                domain       = domain,
                window       = window,
                sample_count = len(values),
            )
        return result

    def rolling_mean(self, kpi_type: KPIType) -> float:
        """Return the rolling mean for a KPI, or 0.0 if no data."""
        buf = self._buffers.get(kpi_type.value)
        return buf.mean() if buf else 0.0

    def rolling_min(self, kpi_type: KPIType) -> float:
        buf = self._buffers.get(kpi_type.value)
        return buf.minimum() if buf else 0.0

    def rolling_max(self, kpi_type: KPIType) -> float:
        buf = self._buffers.get(kpi_type.value)
        return buf.maximum() if buf else 0.0

    def rolling_latest(self, kpi_type: KPIType) -> float:
        buf = self._buffers.get(kpi_type.value)
        return buf.latest() if buf else 0.0

    def sample_count(self, kpi_type: KPIType) -> int:
        buf = self._buffers.get(kpi_type.value)
        return buf.count() if buf else 0

    def clear(self) -> None:
        with self._lock:
            self._buffers.clear()
