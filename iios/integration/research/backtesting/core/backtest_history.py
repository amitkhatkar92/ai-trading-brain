"""core/backtest_history.py — Thread-safe, capped audit log for backtest events."""
from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.backtesting.backtest_constants import BacktestEventType


@dataclass
class BacktestHistoryEntry:
    entity_type: str             = ""          # "backtest" | "simulation" | "order" | …
    entity_id:   str             = ""
    event_type:  BacktestEventType = BacktestEventType.BACKTEST_CREATED
    description: str             = ""
    extra:       dict[str, Any]  = field(default_factory=dict)
    entry_id:    str             = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp:   float           = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id":    self.entry_id,
            "entity_type": self.entity_type,
            "entity_id":   self.entity_id,
            "event_type":  self.event_type.value,
            "description": self.description,
            "timestamp":   self.timestamp,
            "extra":       dict(self.extra),
        }


class BacktestHistory:
    """FIFO audit log with optional capacity cap."""

    def __init__(self, max_entries: int = 100_000) -> None:
        self._max     = max_entries
        self._store: deque[BacktestHistoryEntry] = deque(maxlen=max_entries)
        self._lock    = threading.Lock()

    # ── Write ─────────────────────────────────────────────────────────────────

    def append(self, entry: BacktestHistoryEntry) -> None:
        with self._lock:
            self._store.append(entry)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    # ── Read ──────────────────────────────────────────────────────────────────

    def query(
        self,
        entity_id:   Optional[str]              = None,
        event_type:  Optional[BacktestEventType] = None,
        entity_type: Optional[str]              = None,
        limit:       int                         = 1_000,
    ) -> list[BacktestHistoryEntry]:
        with self._lock:
            results = list(self._store)

        if entity_id is not None:
            results = [e for e in results if e.entity_id == entity_id]
        if event_type is not None:
            results = [e for e in results if e.event_type == event_type]
        if entity_type is not None:
            results = [e for e in results if e.entity_type == entity_type]

        return results[-limit:]

    def latest(self, n: int = 10) -> list[BacktestHistoryEntry]:
        with self._lock:
            entries = list(self._store)
        return entries[-n:]

    def count(self) -> int:
        with self._lock:
            return len(self._store)
