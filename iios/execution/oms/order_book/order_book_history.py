"""iios/execution/oms/order_book/order_book_history.py
==================================================
OrderBookHistory — append-only immutable history of Order Book
add/update/remove operations.

C6 Execution Intelligence — Phase 2, Module 2
"""
from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from iios.execution.oms.order_book.constants import BookEntryStatus


@dataclass(frozen=True)
class BookHistoryEntry:
    """Immutable record of one Order Book operation."""

    entry_id:   str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id:   str = ""
    operation:  str = ""   # "ADD" | "UPDATE" | "REMOVE"
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    old_state:  str = ""
    new_state:  str = ""
    actor:      str = "iios:system"
    reason:     str = ""
    occurred_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id":    self.entry_id,
            "order_id":    self.order_id,
            "operation":   self.operation,
            "old_status":  self.old_status,
            "new_status":  self.new_status,
            "old_state":   self.old_state,
            "new_state":   self.new_state,
            "actor":       self.actor,
            "reason":      self.reason,
            "occurred_at": self.occurred_at,
        }


class OrderBookHistory:
    """
    Append-only, thread-safe history of Order Book operations.
    Bounded by max_entries.
    """

    def __init__(self, max_entries: int = 10_000) -> None:
        self._entries: deque[BookHistoryEntry] = deque(maxlen=max_entries)
        self._lock     = threading.Lock()
        self._total:   int = 0
        self._evicted: int = 0

    def record(self, entry: BookHistoryEntry) -> None:
        with self._lock:
            if len(self._entries) == self._entries.maxlen:
                self._evicted += 1
            self._entries.append(entry)
            self._total += 1

    def entries(self) -> list[BookHistoryEntry]:
        with self._lock:
            return list(self._entries)

    def first(self) -> Optional[BookHistoryEntry]:
        with self._lock:
            return self._entries[0] if self._entries else None

    def last(self) -> Optional[BookHistoryEntry]:
        with self._lock:
            return self._entries[-1] if self._entries else None

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def for_order(self, order_id: str) -> list[BookHistoryEntry]:
        with self._lock:
            return [e for e in self._entries if e.order_id == order_id]

    def since(self, since_ts: float) -> list[BookHistoryEntry]:
        with self._lock:
            return [e for e in self._entries if e.occurred_at >= since_ts]

    @property
    def total_recorded(self) -> int:
        return self._total

    @property
    def evicted_count(self) -> int:
        return self._evicted

    def __iter__(self) -> Iterator[BookHistoryEntry]:
        with self._lock:
            entries = list(self._entries)
        return iter(entries)

    def __len__(self) -> int:
        return self.count()
