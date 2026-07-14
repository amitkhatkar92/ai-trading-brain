"""iios/investment/decision/integration/health_monitor.py
IntegrationHealthMonitor — aggregates engine health, dependency status,
and coverage into a single IntegrationHealthReport.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.decision.integration.coverage_monitor import CoverageMonitor, CoverageReport
from iios.investment.decision.integration.dependency_monitor import (
    DependencyMonitor,
    DependencyStatus,
)
from iios.investment.decision.integration.engine_health import (
    EngineHealthMonitor,
    EngineHealthRecord,
)
from iios.investment.decision.integration.integration_constants import (
    ComponentId,
    HealthStatus,
    IntegrationStatus,
)


@dataclass(frozen=True)
class IntegrationHealthReport:
    integration_status:  IntegrationStatus
    engine_status:       HealthStatus
    total_sessions:      int
    successful:          int
    failed:              int
    consecutive_failures: int
    avg_duration_ms:     float
    engine_health:       List[EngineHealthRecord]
    dependency_statuses: List[DependencyStatus]

    @property
    def is_healthy(self) -> bool:
        return self.integration_status.is_operational and (
            self.engine_status != HealthStatus.UNHEALTHY
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integration_status":  self.integration_status.value,
            "engine_status":       self.engine_status.value,
            "is_healthy":          self.is_healthy,
            "total_sessions":      self.total_sessions,
            "successful":          self.successful,
            "failed":              self.failed,
            "consecutive_failures":self.consecutive_failures,
            "avg_duration_ms":     round(self.avg_duration_ms, 1),
            "engine_health":       [h.to_dict() for h in self.engine_health],
            "dependency_statuses": [d.to_dict() for d in self.dependency_statuses],
        }


class IntegrationHealthMonitor:
    """
    Thread-safe aggregate health monitor for the integration engine.
    Composes EngineHealthMonitor, DependencyMonitor, and CoverageMonitor.
    """

    def __init__(self) -> None:
        self._lock         = threading.RLock()
        self._status       = IntegrationStatus.INITIALIZING
        self._engine_health= EngineHealthMonitor()
        self._dep_monitor  = DependencyMonitor()
        self._cov_monitor  = CoverageMonitor()
        self._total        = 0
        self._successful   = 0
        self._failed       = 0
        self._consec_fail  = 0
        self._dur_sum      = 0.0

    def set_status(self, status: IntegrationStatus) -> None:
        with self._lock:
            self._status = status

    def record_success(self, duration_ms: float) -> None:
        with self._lock:
            self._total      += 1
            self._successful += 1
            self._consec_fail = 0
            self._dur_sum    += duration_ms

    def record_failure(self) -> None:
        with self._lock:
            self._total      += 1
            self._failed     += 1
            self._consec_fail += 1

    def record_component_update(self, component: ComponentId, latency_ms: Optional[float] = None) -> None:
        self._engine_health.record_update(component)
        self._dep_monitor.record_received(component, latency_ms)

    def record_component_failure(self, component: ComponentId, error: Optional[str] = None) -> None:
        self._engine_health.record_failure(component, error)

    def report(self) -> IntegrationHealthReport:
        with self._lock:
            n_ok     = max(1, self._successful)
            avg_dur  = self._dur_sum / n_ok
            status   = self._status
            total    = self._total
            succ     = self._successful
            fail     = self._failed
            consec   = self._consec_fail

        return IntegrationHealthReport(
            integration_status   = status,
            engine_status        = self._engine_health.overall_status(),
            total_sessions       = total,
            successful           = succ,
            failed               = fail,
            consecutive_failures = consec,
            avg_duration_ms      = avg_dur,
            engine_health        = self._engine_health.all_health(),
            dependency_statuses  = self._dep_monitor.all_statuses(),
        )

    @property
    def coverage_monitor(self) -> CoverageMonitor:
        return self._cov_monitor

    @property
    def engine_health_monitor(self) -> EngineHealthMonitor:
        return self._engine_health

    @property
    def dependency_monitor(self) -> DependencyMonitor:
        return self._dep_monitor

    def reset(self) -> None:
        with self._lock:
            self._total = self._successful = self._failed = self._consec_fail = 0
            self._dur_sum = 0.0
