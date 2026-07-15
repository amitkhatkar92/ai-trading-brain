"""iios/investment/portfolio/integration/health_monitor.py

Aggregated integration engine health — combines per-engine health,
integration success rate, and active portfolio count.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from iios.investment.portfolio.integration.engine_health import EngineHealthMonitor
from iios.investment.portfolio.integration.integration_types import (
    EngineId, HealthStatus, now_utc,
)


@dataclass(frozen=True)
class IntegrationHealthReport:
    report_id:                str          = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at:             str          = field(default_factory=now_utc)
    overall_health:           HealthStatus = HealthStatus.DEGRADED
    n_healthy_engines:        int          = 0
    n_degraded_engines:       int          = 0
    n_offline_engines:        int          = 0
    n_active_portfolios:      int          = 0
    integration_success_rate: float        = 0.0
    avg_snapshot_latency_ms:  float        = 0.0
    total_integrations:       int          = 0
    unhealthy_engines:        Tuple[str, ...] = field(default_factory=tuple)

    def is_healthy(self) -> bool:
        return self.overall_health == HealthStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_health":           self.overall_health.value,
            "n_healthy_engines":        self.n_healthy_engines,
            "n_degraded_engines":       self.n_degraded_engines,
            "n_offline_engines":        self.n_offline_engines,
            "n_active_portfolios":      self.n_active_portfolios,
            "integration_success_rate": round(self.integration_success_rate, 4),
            "avg_snapshot_latency_ms":  round(self.avg_snapshot_latency_ms, 2),
            "total_integrations":       self.total_integrations,
            "unhealthy_engines":        list(self.unhealthy_engines),
            "is_healthy":               self.is_healthy(),
        }


class IntegrationHealthMonitor:
    """Monitors the overall health of the Portfolio Intelligence Integration Engine."""

    HEALTHY_MIN_SUCCESS_RATE = 0.80
    DEGRADED_MIN_SUCCESS_RATE = 0.50

    def __init__(self) -> None:
        self._lock       = threading.RLock()
        self._total      = 0
        self._successes  = 0
        self._total_dur  = 0.0
        self._engine_mon = EngineHealthMonitor()

    def record_integration(
        self,
        succeeded:   bool,
        duration_ms: float = 0.0,
    ) -> None:
        with self._lock:
            self._total     += 1
            self._total_dur += duration_ms
            if succeeded:
                self._successes += 1

    def record_engine_check(
        self,
        engine_id:  EngineId,
        responded:  bool,
        latency_ms: float = 0.0,
        error:      Optional[str] = None,
    ) -> None:
        self._engine_mon.record(engine_id, responded, latency_ms, error)

    def check(self, active_portfolios: int = 0) -> IntegrationHealthReport:
        with self._lock:
            sr      = self._successes / self._total if self._total else 1.0
            avg_dur = self._total_dur / self._total if self._total else 0.0
            total   = self._total

        statuses   = self._engine_mon.all_statuses()
        n_healthy  = sum(1 for s in statuses if s.health_status == HealthStatus.HEALTHY)
        n_degraded = sum(1 for s in statuses if s.health_status == HealthStatus.DEGRADED)
        n_offline  = sum(1 for s in statuses if s.health_status == HealthStatus.OFFLINE)
        unhealthy  = tuple(
            s.engine_id.value for s in statuses
            if s.health_status != HealthStatus.HEALTHY
        )

        if n_offline > 0 or sr < self.DEGRADED_MIN_SUCCESS_RATE:
            overall = HealthStatus.CRITICAL
        elif n_degraded > 2 or sr < self.HEALTHY_MIN_SUCCESS_RATE:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return IntegrationHealthReport(
            overall_health           = overall,
            n_healthy_engines        = n_healthy,
            n_degraded_engines       = n_degraded,
            n_offline_engines        = n_offline,
            n_active_portfolios      = active_portfolios,
            integration_success_rate = round(sr, 4),
            avg_snapshot_latency_ms  = round(avg_dur, 2),
            total_integrations       = total,
            unhealthy_engines        = unhealthy,
        )
