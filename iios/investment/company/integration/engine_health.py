"""iios/investment/company/integration/engine_health.py
Per-engine health records and status determination.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.company.integration.company_state import (
    EngineStatus, STALE_CRIT_SECONDS, STALE_WARN_SECONDS,
)


@dataclass
class EngineHealthRecord:
    """Current health state of a single upstream engine."""
    engine_name:  str
    status:       EngineStatus = EngineStatus.UNAVAILABLE
    last_update:  Optional[datetime] = None
    update_count: int = 0
    error_count:  int = 0
    latency_ms:   Optional[float] = None   # ms for the last successful update

    @property
    def staleness_seconds(self) -> float:
        if self.last_update is None:
            return float("inf")
        return (datetime.now(timezone.utc) - self.last_update).total_seconds()

    @property
    def is_healthy(self) -> bool:
        return self.status == EngineStatus.HEALTHY

    @property
    def is_available(self) -> bool:
        return self.status != EngineStatus.UNAVAILABLE

    def record_update(self, latency_ms: Optional[float] = None) -> None:
        self.last_update  = datetime.now(timezone.utc)
        self.update_count += 1
        self.latency_ms    = latency_ms
        self.status        = self._compute_status()

    def record_error(self) -> None:
        self.error_count += 1

    def refresh_status(self) -> None:
        self.status = self._compute_status()

    def _compute_status(self) -> EngineStatus:
        if self.last_update is None:
            return EngineStatus.UNAVAILABLE
        age = self.staleness_seconds
        if age >= STALE_CRIT_SECONDS:
            return EngineStatus.STALE
        if age >= STALE_WARN_SECONDS:
            return EngineStatus.DEGRADED
        return EngineStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_name":       self.engine_name,
            "status":            self.status.value,
            "last_update":       self.last_update.isoformat() if self.last_update else None,
            "staleness_seconds": round(self.staleness_seconds, 1) if self.staleness_seconds != float("inf") else None,
            "update_count":      self.update_count,
            "error_count":       self.error_count,
            "latency_ms":        round(self.latency_ms, 2) if self.latency_ms is not None else None,
        }


def compute_engine_status(age_seconds: float) -> EngineStatus:
    """Utility: determine EngineStatus from data age."""
    if age_seconds >= STALE_CRIT_SECONDS:
        return EngineStatus.STALE
    if age_seconds >= STALE_WARN_SECONDS:
        return EngineStatus.DEGRADED
    return EngineStatus.HEALTHY
