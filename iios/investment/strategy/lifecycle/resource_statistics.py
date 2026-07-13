"""iios/investment/strategy/lifecycle/resource_statistics.py
Runtime resource usage snapshots and rolling statistics.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, List, Optional


@dataclass
class ResourceSnapshot:
    """Point-in-time resource utilisation reading."""

    thread_count: int = 0
    active_strategies: int = 0
    queued_strategies: int = 0
    total_workers: int = 0
    cpu_weight_used: float = 0.0
    memory_estimate_mb: float = 0.0
    captured_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def thread_utilization(self) -> float:
        if self.total_workers == 0:
            return 0.0
        return min(self.thread_count / self.total_workers, 1.0)

    def to_dict(self) -> dict:
        return {
            "thread_count": self.thread_count,
            "active_strategies": self.active_strategies,
            "queued_strategies": self.queued_strategies,
            "total_workers": self.total_workers,
            "thread_utilization": round(self.thread_utilization, 3),
            "cpu_weight_used": round(self.cpu_weight_used, 3),
            "memory_estimate_mb": round(self.memory_estimate_mb, 1),
            "captured_at": self.captured_at.isoformat(),
        }


class ResourceStatistics:
    """
    Thread-safe rolling resource usage statistics.

    Keeps the last ``window`` snapshots for trend analysis.
    """

    def __init__(self, window: int = 100) -> None:
        self._window = window
        self._lock = threading.Lock()
        self._snapshots: Deque[ResourceSnapshot] = deque(maxlen=window)

    def record(self, snapshot: ResourceSnapshot) -> None:
        with self._lock:
            self._snapshots.append(snapshot)

    def latest(self) -> Optional[ResourceSnapshot]:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    def history(self, n: int = 20) -> List[ResourceSnapshot]:
        with self._lock:
            return list(self._snapshots)[-n:]

    def average_thread_utilization(self, last_n: int = 10) -> float:
        snaps = self.history(last_n)
        if not snaps:
            return 0.0
        return sum(s.thread_utilization for s in snaps) / len(snaps)

    def peak_active_strategies(self) -> int:
        with self._lock:
            if not self._snapshots:
                return 0
            return max(s.active_strategies for s in self._snapshots)
