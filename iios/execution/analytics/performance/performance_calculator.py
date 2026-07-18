"""
iios/execution/analytics/performance/performance_calculator.py
==============================================================
PerformanceCalculator — computes all 19 institutional KPIs from
CollectedData using pure-Python arithmetic.

NO external numeric libraries required.
NO predictive models.
NO machine learning.

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    CALC_SYSTEM_ID,
    AggregationWindow,
    KPIType,
    PerformanceDomain,
)
from .exceptions import PerformanceEngineNotRunningError
from .performance_collector import CollectedData
from .performance_kpi import KPIValue, make_kpi_value

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


# ── Pure-Python math helpers ──────────────────────────────────────────────────

def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return min(1.0, max(0.0, numerator / denominator))


def _safe_mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _safe_median(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2.0
    return s[mid]


def _percentile(values: List[float], p: float) -> float:
    """Compute the p-th percentile using linear interpolation."""
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p / 100.0
    lo = int(k)
    hi = lo + 1
    if hi >= len(s):
        return s[lo]
    frac = k - lo
    return s[lo] + frac * (s[hi] - s[lo])


def _std_dev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _safe_mean(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


# ── Calculator ────────────────────────────────────────────────────────────────

class PerformanceCalculator(LifecycleAwareMixin):
    """
    Computes all 19 institutional KPIs from a CollectedData object.

    All computations are pure-Python arithmetic — no external libraries,
    no predictive models, no machine learning.

    Thread-safe.  Must be started before use.
    """

    def _on_start(self) -> None:
        _log.info("PerformanceCalculator started.", system_id=CALC_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("PerformanceCalculator stopped.", system_id=CALC_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PerformanceEngineNotRunningError()

    # ── Public API ────────────────────────────────────────────────────────────

    def calculate(
        self,
        data:       CollectedData,
        domain:     PerformanceDomain,
        window:     AggregationWindow,
        kpi_types:  Optional[List[KPIType]] = None,
    ) -> Dict[KPIType, KPIValue]:
        """
        Compute KPI values from CollectedData.

        If kpi_types is None or empty, all 19 KPIs are computed.

        Returns dict mapping KPIType → KPIValue.
        """
        self._assert_running()
        targets = list(kpi_types) if kpi_types else list(KPIType)
        result: Dict[KPIType, KPIValue] = {}
        for kpi_type in targets:
            try:
                kv = self._compute(kpi_type, data, domain, window)
                if kv is not None:
                    result[kpi_type] = kv
            except Exception as exc:
                _log.warning(
                    "KPI computation failed; skipping.",
                    kpi_type = kpi_type.value,
                    error    = str(exc),
                )
        return result

    def calculate_single(
        self,
        kpi_type: KPIType,
        data:     CollectedData,
        domain:   PerformanceDomain,
        window:   AggregationWindow,
    ) -> Optional[KPIValue]:
        """Compute a single KPI. Returns None if computation is not possible."""
        self._assert_running()
        return self._compute(kpi_type, data, domain, window)

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def _compute(
        self,
        kpi_type: KPIType,
        data:     CollectedData,
        domain:   PerformanceDomain,
        window:   AggregationWindow,
    ) -> Optional[KPIValue]:
        _map = {
            KPIType.EXECUTION_SUCCESS_RATE:   self._execution_success_rate,
            KPIType.EXECUTION_FAILURE_RATE:   self._execution_failure_rate,
            KPIType.AVG_EXECUTION_TIME_MS:    self._avg_execution_time,
            KPIType.MEDIAN_EXECUTION_TIME_MS: self._median_execution_time,
            KPIType.P95_LATENCY_MS:           self._p95_latency,
            KPIType.P99_LATENCY_MS:           self._p99_latency,
            KPIType.RECOVERY_SUCCESS_RATE:    self._recovery_success_rate,
            KPIType.MEAN_TIME_TO_RECOVERY_MS: self._mean_time_to_recovery,
            KPIType.GATEWAY_AVAILABILITY:     self._gateway_availability,
            KPIType.BROKER_AVAILABILITY:      self._broker_availability,
            KPIType.MONITORING_AVAILABILITY:  self._monitoring_availability,
            KPIType.SYSTEM_THROUGHPUT:        self._system_throughput,
            KPIType.QUEUE_EFFICIENCY:         self._queue_efficiency,
            KPIType.ORDER_COMPLETION_RATE:    self._order_completion_rate,
            KPIType.POSITION_ACCURACY:        self._position_accuracy,
            KPIType.RISK_RULE_EFFECTIVENESS:  self._risk_rule_effectiveness,
            KPIType.PORTFOLIO_EFFICIENCY:     self._portfolio_efficiency,
            KPIType.STRATEGY_EFFICIENCY:      self._strategy_efficiency,
            KPIType.RESOURCE_UTILIZATION:     self._resource_utilization,
        }
        fn = _map.get(kpi_type)
        if fn is None:
            return None
        value, sample_count = fn(data)
        return make_kpi_value(
            kpi_type,
            value,
            domain       = domain,
            window       = window,
            sample_count = sample_count,
        )

    # ── KPI computation methods ───────────────────────────────────────────────

    def _execution_success_rate(self, d: CollectedData):
        return (
            _safe_rate(d.completed_executions, d.total_executions),
            d.total_executions,
        )

    def _execution_failure_rate(self, d: CollectedData):
        return (
            _safe_rate(d.failed_executions, d.total_executions),
            d.total_executions,
        )

    def _avg_execution_time(self, d: CollectedData):
        return _safe_mean(d.execution_times_ms), len(d.execution_times_ms)

    def _median_execution_time(self, d: CollectedData):
        return _safe_median(d.execution_times_ms), len(d.execution_times_ms)

    def _p95_latency(self, d: CollectedData):
        return _percentile(d.execution_times_ms, 95.0), len(d.execution_times_ms)

    def _p99_latency(self, d: CollectedData):
        return _percentile(d.execution_times_ms, 99.0), len(d.execution_times_ms)

    def _recovery_success_rate(self, d: CollectedData):
        return (
            _safe_rate(d.successful_recoveries, d.total_recoveries),
            d.total_recoveries,
        )

    def _mean_time_to_recovery(self, d: CollectedData):
        return _safe_mean(d.recovery_times_ms), len(d.recovery_times_ms)

    def _gateway_availability(self, d: CollectedData):
        return (
            _safe_rate(int(d.gateway_uptime_s * 1000), int(d.gateway_total_s * 1000)),
            1,
        )

    def _broker_availability(self, d: CollectedData):
        return (
            _safe_rate(int(d.broker_uptime_s * 1000), int(d.broker_total_s * 1000)),
            1,
        )

    def _monitoring_availability(self, d: CollectedData):
        return (
            _safe_rate(int(d.monitoring_uptime_s * 1000), int(d.monitoring_total_s * 1000)),
            1,
        )

    def _system_throughput(self, d: CollectedData):
        if d.window_seconds <= 0.0 or d.queue_capacity <= 0:
            return 0.0, 0
        tps = d.processed_items / d.window_seconds
        # Normalise against capacity (assume capacity means tps at 100%)
        capacity_tps = d.queue_capacity / max(d.window_seconds, 1.0)
        score = min(1.0, tps / capacity_tps) if capacity_tps > 0 else 0.0
        return score, d.processed_items

    def _queue_efficiency(self, d: CollectedData):
        if d.queue_capacity <= 0:
            return 1.0, 0
        used = max(0, d.queue_capacity - d.queue_depth)
        return _safe_rate(used, d.queue_capacity), 1

    def _order_completion_rate(self, d: CollectedData):
        return (
            _safe_rate(d.completed_orders, d.total_orders),
            d.total_orders,
        )

    def _position_accuracy(self, d: CollectedData):
        return (
            _safe_rate(d.accurate_positions, d.total_positions),
            d.total_positions,
        )

    def _risk_rule_effectiveness(self, d: CollectedData):
        return (
            _safe_rate(d.risk_rules_passed, d.risk_rules_evaluated),
            d.risk_rules_evaluated,
        )

    def _portfolio_efficiency(self, d: CollectedData):
        return min(1.0, max(0.0, d.portfolio_efficiency)), 1

    def _strategy_efficiency(self, d: CollectedData):
        return min(1.0, max(0.0, d.strategy_efficiency)), 1

    def _resource_utilization(self, d: CollectedData):
        # Mean of CPU and memory utilization
        utilization = (d.cpu_utilization + d.memory_utilization) / 2.0
        return min(1.0, max(0.0, utilization)), 2
