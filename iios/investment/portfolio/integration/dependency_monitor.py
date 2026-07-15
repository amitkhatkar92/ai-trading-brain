"""iios/investment/portfolio/integration/dependency_monitor.py

Monitors whether required upstream engines are healthy and available.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from iios.investment.portfolio.integration.engine_health import EngineHealthMonitor
from iios.investment.portfolio.integration.integration_types import (
    EngineId, HealthStatus, REQUIRED_ENGINES, now_utc,
)


@dataclass(frozen=True)
class DependencyStatus:
    portfolio_id:   str              = ""
    generated_at:   str              = field(default_factory=now_utc)
    all_available:  bool             = False
    degraded:       Tuple[str, ...]  = field(default_factory=tuple)
    unavailable:    Tuple[str, ...]  = field(default_factory=tuple)
    n_available:    int              = 0
    n_total:        int              = 0
    readiness_score: float           = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "all_available":   self.all_available,
            "readiness_score": round(self.readiness_score, 4),
            "degraded":        list(self.degraded),
            "unavailable":     list(self.unavailable),
            "n_available":     self.n_available,
            "n_total":         self.n_total,
        }


class DependencyMonitor:
    """Checks whether all required upstream engines are available."""

    def __init__(self, engine_health: Optional[EngineHealthMonitor] = None) -> None:
        self._health = engine_health or EngineHealthMonitor()

    def check(self, portfolio_id: str = "") -> DependencyStatus:
        degraded:    list = []
        unavailable: list = []
        available        = 0

        for eid in REQUIRED_ENGINES:
            s = self._health.status(eid)
            if s.health_status == HealthStatus.HEALTHY:
                available += 1
            elif s.health_status in (HealthStatus.DEGRADED, HealthStatus.CRITICAL):
                degraded.append(eid.value)
            else:
                unavailable.append(eid.value)

        n_total   = len(REQUIRED_ENGINES)
        readiness = available / n_total if n_total > 0 else 0.0

        return DependencyStatus(
            portfolio_id    = portfolio_id,
            all_available   = len(unavailable) == 0 and len(degraded) == 0,
            degraded        = tuple(degraded),
            unavailable     = tuple(unavailable),
            n_available     = available,
            n_total         = n_total,
            readiness_score = round(readiness, 4),
        )
