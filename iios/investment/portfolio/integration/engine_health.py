"""iios/investment/portfolio/integration/engine_health.py

Per-upstream-engine health monitoring: availability, latency, success rate.
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.integration.integration_types import (
    EngineId, HealthStatus, now_utc,
)


@dataclass(frozen=True)
class EngineHealthRecord:
    engine_id:   EngineId
    recorded_at: str
    responded:   bool
    latency_ms:  float = 0.0
    error:       Optional[str] = None


@dataclass(frozen=True)
class EngineHealthStatus:
    engine_id:       EngineId
    health_status:   HealthStatus
    success_rate:    float = 0.0
    avg_latency_ms:  float = 0.0
    last_success_at: Optional[str] = None
    last_error:      Optional[str] = None
    n_records:       int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_id":      self.engine_id.value,
            "health_status":  self.health_status.value,
            "success_rate":   round(self.success_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
        }


class EngineHealthMonitor:
    """Tracks availability and latency of each upstream portfolio engine."""

    HEALTHY_MIN_SUCCESS_RATE = 0.80

    def __init__(self, window: int = 50) -> None:
        self._window  = window
        self._lock    = threading.RLock()
        self._records: Dict[EngineId, deque] = {
            eid: deque(maxlen=window) for eid in EngineId
        }

    def record(
        self,
        engine_id:  EngineId,
        responded:  bool,
        latency_ms: float = 0.0,
        error:      Optional[str] = None,
    ) -> None:
        rec = EngineHealthRecord(
            engine_id   = engine_id,
            recorded_at = now_utc(),
            responded   = responded,
            latency_ms  = latency_ms,
            error       = error,
        )
        with self._lock:
            self._records[engine_id].appendleft(rec)

    def status(self, engine_id: EngineId) -> EngineHealthStatus:
        with self._lock:
            records = list(self._records[engine_id])
        if not records:
            return EngineHealthStatus(
                engine_id    = engine_id,
                health_status = HealthStatus.OFFLINE,
            )
        n            = len(records)
        successes    = sum(1 for r in records if r.responded)
        success_rate = successes / n
        avg_latency  = sum(r.latency_ms for r in records) / n
        last_success = next(
            (r.recorded_at for r in records if r.responded), None
        )
        last_error   = next(
            (r.error for r in records if r.error), None
        )

        if success_rate >= self.HEALTHY_MIN_SUCCESS_RATE:
            health = HealthStatus.HEALTHY
        elif success_rate >= 0.50:
            health = HealthStatus.DEGRADED
        elif success_rate > 0:
            health = HealthStatus.CRITICAL
        else:
            health = HealthStatus.OFFLINE

        return EngineHealthStatus(
            engine_id       = engine_id,
            health_status   = health,
            success_rate    = round(success_rate, 4),
            avg_latency_ms  = round(avg_latency, 2),
            last_success_at = last_success,
            last_error      = last_error,
            n_records       = n,
        )

    def all_statuses(self) -> List[EngineHealthStatus]:
        return [self.status(eid) for eid in EngineId]

    def unhealthy_engines(self) -> List[EngineId]:
        return [
            eid for eid in EngineId
            if self.status(eid).health_status != HealthStatus.HEALTHY
        ]
