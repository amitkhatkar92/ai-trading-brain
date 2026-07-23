"""
market_snapshot_history.py — iios.market.snapshot
==================================================
Bounded ring-buffer history for market snapshots and events.

C12 Market Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY


class MarketSnapshotHistory:
    """Bounded ring-buffer of snapshot artefacts. Thread-safe."""

    def __init__(self, max_entries: int = DEFAULT_MAX_HISTORY) -> None:
        self._max       = max_entries
        self._lock      = threading.RLock()
        self._snapshots: Deque[Any] = deque(maxlen=max_entries)
        self._events:    Deque[Any] = deque(maxlen=max_entries)
        self._errors:    Deque[Any] = deque(maxlen=max_entries)

    def record_snapshot(self, snapshot: Any) -> None:
        with self._lock:
            self._snapshots.append(snapshot)

    def record_event(self, event: Any) -> None:
        with self._lock:
            self._events.append(event)

    def record_error(self, error: Any) -> None:
        with self._lock:
            self._errors.append(error)

    def recent_snapshots(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._snapshots)
        return items[-n:] if n < len(items) else items

    def recent_events(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._events)
        return items[-n:] if n < len(items) else items

    def recent_errors(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._errors)
        return items[-n:] if n < len(items) else items

    def counts(self) -> Dict[str, int]:
        with self._lock:
            return {
                "snapshots": len(self._snapshots),
                "events":    len(self._events),
                "errors":    len(self._errors),
            }

    def clear(self) -> None:
        with self._lock:
            self._snapshots.clear()
            self._events.clear()
            self._errors.clear()
