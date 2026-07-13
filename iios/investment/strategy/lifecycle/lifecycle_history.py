"""iios/investment/strategy/lifecycle/lifecycle_history.py
Lifecycle event records and per-strategy event buffer.
"""
from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from iios.investment.strategy.strategy_constants import LifecycleEvent, StrategyStatus


@dataclass
class LifecycleHistoryEntry:
    """Record of a single lifecycle transition for a strategy."""

    entry_id:    str           = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str           = ""
    from_status: StrategyStatus = StrategyStatus.DRAFT
    to_status:   StrategyStatus = StrategyStatus.DRAFT
    event:       LifecycleEvent = LifecycleEvent.CREATED
    reason:      str            = ""
    actor:       str            = "system"
    timestamp:   float          = field(default_factory=time.time)
    metadata:    dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id":    self.entry_id,
            "strategy_id": self.strategy_id,
            "from_status": self.from_status.value,
            "to_status":   self.to_status.value,
            "event":       self.event.value,
            "reason":      self.reason,
            "actor":       self.actor,
            "timestamp":   self.timestamp,
            "metadata":    self.metadata,
        }


class LifecycleHistory:
    """Thread-safe per-strategy ring buffer of LifecycleHistoryEntry objects."""

    def __init__(self, max_per_strategy: int = 200) -> None:
        self._lock  = threading.RLock()
        self._max   = max_per_strategy
        self._store: dict[str, deque[LifecycleHistoryEntry]] = {}

    def record(self, entry: LifecycleHistoryEntry) -> None:
        with self._lock:
            buf = self._store.setdefault(
                entry.strategy_id, deque(maxlen=self._max)
            )
            buf.append(entry)

    def get(self, strategy_id: str, n: int = 20) -> list[LifecycleHistoryEntry]:
        with self._lock:
            buf = self._store.get(strategy_id, deque())
            items = list(buf)
            return items[-n:] if len(items) >= n else items

    def latest(self, strategy_id: str) -> LifecycleHistoryEntry | None:
        with self._lock:
            buf = self._store.get(strategy_id)
            return buf[-1] if buf else None

    def count(self, strategy_id: str) -> int:
        with self._lock:
            return len(self._store.get(strategy_id, []))

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "strategies":     len(self._store),
                "total_events":   sum(len(b) for b in self._store.values()),
                "max_per_strategy": self._max,
            }
