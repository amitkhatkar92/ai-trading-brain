"""
iios/execution/analytics/performance/performance_collector.py
=============================================================
PerformanceCollector — collects and normalises raw performance data from
execution subsystem snapshots and context metadata into a CollectedData
intermediate representation for the calculator.

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import CALC_SYSTEM_ID
from .exceptions import PerformanceEngineNotRunningError
from .performance_context import PerformanceContext

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


@dataclass
class CollectedData:
    """
    Mutable intermediate representation of all collected raw performance data.

    Populated by PerformanceCollector from context snapshots and historical
    data.  Consumed by PerformanceCalculator to compute KPI values.
    """

    # Execution counters
    total_executions:      int         = 0
    completed_executions:  int         = 0
    failed_executions:     int         = 0

    # Latency samples (milliseconds)
    execution_times_ms:    List[float] = field(default_factory=list)

    # Recovery counters
    total_recoveries:      int         = 0
    successful_recoveries: int         = 0
    recovery_times_ms:     List[float] = field(default_factory=list)

    # Availability metrics (seconds)
    gateway_uptime_s:      float       = 0.0
    gateway_total_s:       float       = 1.0   # prevent divide-by-zero
    broker_uptime_s:       float       = 0.0
    broker_total_s:        float       = 1.0
    monitoring_uptime_s:   float       = 0.0
    monitoring_total_s:    float       = 1.0

    # Queue/throughput metrics
    queue_depth:           int         = 0
    queue_capacity:        int         = 1000
    processed_items:       int         = 0
    window_seconds:        float       = 1.0   # prevent divide-by-zero

    # Order metrics
    total_orders:          int         = 0
    completed_orders:      int         = 0

    # Position metrics
    total_positions:       int         = 0
    accurate_positions:    int         = 0

    # Risk metrics
    risk_rules_evaluated:  int         = 0
    risk_rules_passed:     int         = 0

    # Portfolio / strategy metrics (returns, higher = better)
    portfolio_efficiency:  float       = 0.0   # pre-computed [0, 1]
    strategy_efficiency:   float       = 0.0   # pre-computed [0, 1]

    # Resource metrics
    cpu_utilization:       float       = 0.0   # ratio [0, 1]
    memory_utilization:    float       = 0.0   # ratio [0, 1]

    # Timestamp
    collected_at:          float       = field(default_factory=time.time)


class PerformanceCollector(LifecycleAwareMixin):
    """
    Collects raw performance data from a PerformanceContext.

    Extracts data from optional snapshots using safe ``getattr`` with
    sensible defaults.  All extraction is side-effect free.

    Thread-safe.  Must be started before use.
    """

    def _on_start(self) -> None:
        _log.info("PerformanceCollector started.", system_id=CALC_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("PerformanceCollector stopped.", system_id=CALC_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PerformanceEngineNotRunningError()

    def collect(self, context: PerformanceContext) -> CollectedData:
        """
        Extract all available performance data from the context.

        Returns a populated CollectedData object.
        """
        self._assert_running()
        data = CollectedData()
        self._collect_monitoring(context, data)
        self._collect_recovery(context, data)
        self._collect_gateway(context, data)
        self._collect_risk(context, data)
        self._collect_historical(context, data)
        self._collect_window(context, data)
        return data

    # ── Snapshot extraction methods ───────────────────────────────────────────

    def _collect_monitoring(
        self, context: PerformanceContext, data: CollectedData
    ) -> None:
        snap = context.monitoring_snapshot
        if snap is None:
            return
        data.completed_executions = int(getattr(snap, "completed_executions", 0))
        data.failed_executions    = int(getattr(snap, "failed_executions",    0))
        data.total_executions     = data.completed_executions + data.failed_executions

        total_fills = int(getattr(snap, "total_fills", 0))
        uptime_sec  = float(getattr(snap, "uptime_sec", 1.0))

        data.monitoring_uptime_s  = max(uptime_sec, 0.0)
        data.monitoring_total_s   = max(uptime_sec, 1.0)
        data.processed_items      = total_fills
        data.window_seconds       = max(uptime_sec, 1.0)

        active = int(getattr(snap, "active_executions", 0))
        data.queue_depth = active

    def _collect_recovery(
        self, context: PerformanceContext, data: CollectedData
    ) -> None:
        snap = context.recovery_snapshot
        if snap is None:
            return
        result = str(getattr(snap, "recovery_result", "") or "")
        duration_ms = float(getattr(snap, "recovery_duration_ms", 0.0) or 0.0)

        if result:
            data.total_recoveries = 1
            if result.lower() in ("success", "succeeded", "recovered", "completed"):
                data.successful_recoveries = 1
            if duration_ms > 0.0:
                data.recovery_times_ms = [duration_ms]

    def _collect_gateway(
        self, context: PerformanceContext, data: CollectedData
    ) -> None:
        snap = context.gateway_snapshot
        if snap is None:
            return
        uptime_s = float(getattr(snap, "uptime_seconds", 0.0) or 0.0)
        total_s  = float(getattr(snap, "total_seconds",  max(uptime_s, 1.0)) or 1.0)
        data.gateway_uptime_s = uptime_s
        data.gateway_total_s  = max(total_s, 1.0)

    def _collect_risk(
        self, context: PerformanceContext, data: CollectedData
    ) -> None:
        snap = context.risk_snapshot
        if snap is None:
            return
        data.risk_rules_evaluated = int(getattr(snap, "rules_evaluated", 0) or 0)
        data.risk_rules_passed    = int(getattr(snap, "rules_passed",    0) or 0)

    def _collect_historical(
        self, context: PerformanceContext, data: CollectedData
    ) -> None:
        raw = context.raw_sample_data
        if "execution_times_ms" in raw:
            data.execution_times_ms = list(raw["execution_times_ms"])
        if "recovery_times_ms" in raw:
            data.recovery_times_ms = list(raw["recovery_times_ms"])

        # Numeric overrides from raw_sample_data
        for attr, key in [
            ("total_orders",       "total_orders"),
            ("completed_orders",   "completed_orders"),
            ("total_positions",    "total_positions"),
            ("accurate_positions", "accurate_positions"),
            ("queue_capacity",     "queue_capacity"),
            ("processed_items",    "processed_items"),
        ]:
            if key in raw and raw[key]:
                setattr(data, attr, int(raw[key][0]))

        for attr, key in [
            ("portfolio_efficiency", "portfolio_efficiency"),
            ("strategy_efficiency",  "strategy_efficiency"),
            ("cpu_utilization",      "cpu_utilization"),
            ("memory_utilization",   "memory_utilization"),
            ("broker_uptime_s",      "broker_uptime_s"),
            ("broker_total_s",       "broker_total_s"),
        ]:
            if key in raw and raw[key]:
                setattr(data, attr, float(raw[key][0]))

    def _collect_window(
        self, context: PerformanceContext, data: CollectedData
    ) -> None:
        from .constants import WINDOW_SECONDS, AggregationWindow
        w = WINDOW_SECONDS.get(context.window, 0.0)
        if context.window == AggregationWindow.CUSTOM:
            w = context.custom_window_seconds
        if w > 0.0:
            data.window_seconds = w
