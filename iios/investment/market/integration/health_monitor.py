"""iios/investment/market/integration/health_monitor.py
Orchestrates all health monitoring sub-systems.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional, Set

from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.coverage_monitor import CoverageMonitor
from iios.investment.market.integration.dependency_monitor import DependencyMonitor
from iios.investment.market.integration.engine_health import EngineHealthTracker
from iios.investment.market.integration.models import EngineHealthRecord, HealthStatus


class HealthMonitor:
    """Unified health monitoring for the integration engine.

    Thread-safe — called from the main update loop.
    """

    def __init__(
        self,
        expected_engines:    List[str] = None,
        stale_threshold:     int = 5,
    ) -> None:
        self._lock         = threading.Lock()
        self._tracker      = EngineHealthTracker(stale_threshold)
        self._coverage     = CoverageMonitor(expected_engines)
        self._dependency   = DependencyMonitor()
        self._expected:    List[str] = expected_engines or []

        for engine in self._expected:
            self._tracker.register(engine)

    # ── public API ────────────────────────────────────────────────────────────

    def update(self, state: AggregationState) -> None:
        with self._lock:
            bar_index = state.bar_index
            ts        = state.timestamp

            # Age all registered engines
            self._tracker.advance_bar(bar_index)

            # Record successful updates
            for engine in state.engines_received:
                self._tracker.record_update(engine, bar_index, ts)

            # Coverage
            self._coverage.record(state.engines_received)

    def record_error(self, engine_name: str, error: str) -> None:
        with self._lock:
            self._tracker.record_error(engine_name, error)

    def all_health(self) -> Dict[str, EngineHealthRecord]:
        with self._lock:
            return self._tracker.all_records()

    def engine_health(self, engine_name: str) -> Optional[EngineHealthRecord]:
        with self._lock:
            return self._tracker.get(engine_name)

    def overall_health(self) -> HealthStatus:
        with self._lock:
            records = self._tracker.all_records()
            if not records:
                return HealthStatus.MISSING
            statuses = [r.status for r in records.values()]
            if any(s is HealthStatus.FAILED for s in statuses):
                return HealthStatus.FAILED
            if any(s is HealthStatus.STALE  for s in statuses):
                return HealthStatus.STALE
            if any(s is HealthStatus.DEGRADED for s in statuses):
                return HealthStatus.DEGRADED
            return HealthStatus.HEALTHY

    def degraded_engines(self) -> List[str]:
        with self._lock:
            return self._tracker.degraded_engines()

    def cascade_failures(self) -> Dict[str, List[str]]:
        with self._lock:
            records    = self._tracker.all_records()
            unhealthy  = {
                name for name, rec in records.items()
                if rec.status in (HealthStatus.STALE, HealthStatus.FAILED, HealthStatus.MISSING)
            }
            return self._dependency.cascade_affected(unhealthy)

    def coverage_report(self) -> Dict[str, float]:
        with self._lock:
            return self._coverage.coverage_report()

    def overall_coverage(self) -> float:
        with self._lock:
            return self._coverage.overall_coverage()

    def healthy_count(self) -> int:
        with self._lock:
            return self._tracker.healthy_count()
