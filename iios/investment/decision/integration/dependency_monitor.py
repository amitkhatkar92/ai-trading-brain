"""iios/investment/decision/integration/dependency_monitor.py
DependencyMonitor — tracks update latency and freshness for each upstream engine.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from iios.investment.decision.integration.integration_constants import (
    COMPONENT_MAX_AGE_SECONDS,
    ComponentId,
)


@dataclass(frozen=True)
class DependencyStatus:
    component:      ComponentId
    last_received:  Optional[datetime]
    latency_ms:     Optional[float]     # time between request and delivery
    is_fresh:       bool
    age_seconds:    Optional[float]
    update_count:   int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component":     self.component.value,
            "last_received": self.last_received.isoformat() if self.last_received else None,
            "latency_ms":    round(self.latency_ms, 1) if self.latency_ms is not None else None,
            "is_fresh":      self.is_fresh,
            "age_seconds":   round(self.age_seconds, 1) if self.age_seconds is not None else None,
            "update_count":  self.update_count,
        }


class DependencyMonitor:
    """
    Tracks per-dependency update latency and freshness.
    Maintains a rolling window of latency samples.
    """

    def __init__(self, max_latency_samples: int = 50) -> None:
        self._lock    = threading.RLock()
        self._max_lat = max_latency_samples
        self._state:  Dict[ComponentId, _DepState] = {
            cid: _DepState(cid, max_latency_samples) for cid in ComponentId
        }

    def record_received(self, component: ComponentId, latency_ms: Optional[float] = None) -> None:
        with self._lock:
            self._state[component].on_received(latency_ms)

    def status(self, component: ComponentId) -> DependencyStatus:
        with self._lock:
            return self._state[component].to_status()

    def all_statuses(self) -> List[DependencyStatus]:
        with self._lock:
            return [s.to_status() for s in self._state.values()]

    def stale_components(self) -> List[ComponentId]:
        with self._lock:
            return [
                cid for cid, s in self._state.items()
                if not s.to_status().is_fresh
            ]

    def avg_latency_ms(self, component: ComponentId) -> Optional[float]:
        with self._lock:
            samples = list(self._state[component].latencies)
            if not samples:
                return None
            return sum(samples) / len(samples)


class _DepState:
    def __init__(self, component: ComponentId, max_lat: int) -> None:
        self.component      = component
        self.last_received: Optional[datetime] = None
        self.latencies:     Deque[float]        = deque(maxlen=max_lat)
        self.count          = 0

    def on_received(self, latency_ms: Optional[float]) -> None:
        self.last_received = datetime.now(timezone.utc)
        self.count        += 1
        if latency_ms is not None:
            self.latencies.append(latency_ms)

    def to_status(self) -> DependencyStatus:
        now        = datetime.now(timezone.utc)
        age        = None
        is_fresh   = False
        lat        = None

        if self.last_received is not None:
            age      = (now - self.last_received).total_seconds()
            is_fresh = age <= COMPONENT_MAX_AGE_SECONDS

        if self.latencies:
            lat = self.latencies[-1]

        return DependencyStatus(
            component     = self.component,
            last_received = self.last_received,
            latency_ms    = lat,
            is_fresh      = is_fresh,
            age_seconds   = age,
            update_count  = self.count,
        )
