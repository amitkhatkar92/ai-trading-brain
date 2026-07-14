"""iios/investment/decision/integration/engine_health.py
Per-engine health tracking and EngineHealthMonitor.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.decision.integration.integration_constants import (
    HEALTH_CONSECUTIVE_FAIL_DEGRADED,
    HEALTH_CONSECUTIVE_FAIL_UNHEALTHY,
    ComponentId,
    HealthStatus,
)


@dataclass(frozen=True)
class EngineHealthRecord:
    component:            ComponentId
    status:               HealthStatus
    last_seen:            Optional[datetime]
    consecutive_failures: int
    total_updates:        int
    last_error:           Optional[str]

    @property
    def is_responsive(self) -> bool:
        return self.last_seen is not None

    @property
    def age_seconds(self) -> Optional[float]:
        if self.last_seen is None:
            return None
        return (datetime.now(timezone.utc) - self.last_seen).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component":            self.component.value,
            "status":               self.status.value,
            "is_responsive":        self.is_responsive,
            "last_seen":            self.last_seen.isoformat() if self.last_seen else None,
            "age_seconds":          round(self.age_seconds, 1) if self.age_seconds is not None else None,
            "consecutive_failures": self.consecutive_failures,
            "total_updates":        self.total_updates,
            "last_error":           self.last_error,
        }


class EngineHealthMonitor:
    """
    Tracks health of each upstream Decision Intelligence engine.
    Call `record_update()` when a new snapshot is received,
    `record_failure()` when an engine fails to deliver.
    """

    def __init__(self) -> None:
        self._lock  = threading.RLock()
        self._state: Dict[ComponentId, _EngineState] = {
            cid: _EngineState(cid) for cid in ComponentId
        }

    def record_update(self, component: ComponentId) -> None:
        with self._lock:
            self._state[component].on_update()

    def record_failure(self, component: ComponentId, error: Optional[str] = None) -> None:
        with self._lock:
            self._state[component].on_failure(error)

    def get_health(self, component: ComponentId) -> EngineHealthRecord:
        with self._lock:
            return self._state[component].to_record()

    def all_health(self) -> List[EngineHealthRecord]:
        with self._lock:
            return [s.to_record() for s in self._state.values()]

    def overall_status(self) -> HealthStatus:
        records = self.all_health()
        required = {r for r in records if r.component in ComponentId.required()}
        if any(r.status == HealthStatus.UNHEALTHY for r in required):
            return HealthStatus.UNHEALTHY
        if any(r.status == HealthStatus.DEGRADED for r in required):
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY


class _EngineState:
    def __init__(self, component: ComponentId) -> None:
        self.component       = component
        self.last_seen:   Optional[datetime] = None
        self.consec_fail  = 0
        self.total        = 0
        self.last_error:  Optional[str] = None

    def on_update(self) -> None:
        self.last_seen  = datetime.now(timezone.utc)
        self.consec_fail = 0
        self.total      += 1
        self.last_error  = None

    def on_failure(self, error: Optional[str]) -> None:
        self.consec_fail += 1
        self.last_error   = error

    def _status(self) -> HealthStatus:
        if self.consec_fail >= HEALTH_CONSECUTIVE_FAIL_UNHEALTHY:
            return HealthStatus.UNHEALTHY
        if self.consec_fail >= HEALTH_CONSECUTIVE_FAIL_DEGRADED:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def to_record(self) -> EngineHealthRecord:
        return EngineHealthRecord(
            component            = self.component,
            status               = self._status(),
            last_seen            = self.last_seen,
            consecutive_failures = self.consec_fail,
            total_updates        = self.total,
            last_error           = self.last_error,
        )
