"""iios/execution/oms/order_queue/queue_history.py
==================================================
QueueHistory — append-only, bounded history of terminal QueueEntries.

C6 Execution Intelligence — Phase 2, Module 4
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Iterator

from iios.execution.oms.order_queue.constants import DEFAULT_MAX_HISTORY, QueueEntryState
from iios.execution.oms.order_queue.queue_entry import QueueEntry


class QueueHistory:
    """
    Thread-safe, bounded append-only store of completed QueueEntry objects.

    Entries are stored once they reach a terminal state (DISPATCHED, FAILED,
    EXPIRED, REMOVED).  When the deque is full, the oldest entry is evicted.
    """

    __slots__ = ("_max_size", "_entries", "_total", "_evicted", "_lock")

    def __init__(self, max_size: int = DEFAULT_MAX_HISTORY) -> None:
        if max_size < 1:
            raise ValueError(f"max_size must be ≥ 1, got {max_size!r}")
        self._max_size = max_size
        self._entries: deque[QueueEntry] = deque(maxlen=max_size)
        self._total   = 0
        self._evicted = 0
        self._lock    = threading.RLock()

    # ── Mutators ──────────────────────────────────────────────────────────────

    def append(self, entry: QueueEntry) -> None:
        with self._lock:
            if len(self._entries) == self._max_size:
                self._evicted += 1
            self._entries.append(entry)
            self._total += 1

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def total(self) -> int:
        with self._lock:
            return self._total

    @property
    def evicted(self) -> int:
        with self._lock:
            return self._evicted

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._entries)

    def latest(self, n: int = 10) -> list[QueueEntry]:
        with self._lock:
            snapshot = list(self._entries)
        return snapshot[-n:]

    def for_order(self, order_id: str) -> list[QueueEntry]:
        with self._lock:
            snapshot = list(self._entries)
        return [e for e in snapshot if e.order_id == order_id]

    def dispatched(self) -> list[QueueEntry]:
        with self._lock:
            snapshot = list(self._entries)
        return [e for e in snapshot if e.state == QueueEntryState.DISPATCHED]

    def failed(self) -> list[QueueEntry]:
        with self._lock:
            snapshot = list(self._entries)
        return [e for e in snapshot if e.state == QueueEntryState.FAILED]

    def expired(self) -> list[QueueEntry]:
        with self._lock:
            snapshot = list(self._entries)
        return [e for e in snapshot if e.state == QueueEntryState.EXPIRED]

    def __iter__(self) -> Iterator[QueueEntry]:
        with self._lock:
            snapshot = list(self._entries)
        return iter(snapshot)

    def __len__(self) -> int:
        return self.size

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_size": self._max_size,
            "size":     self.size,
            "total":    self.total,
            "evicted":  self.evicted,
        }
