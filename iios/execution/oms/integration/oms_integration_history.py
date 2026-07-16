"""iios/execution/oms/integration/oms_integration_history.py
==================================================
IntegrationHistory — append-only, thread-safe record of OMS integration events.

C6 Execution Intelligence — Phase 2, Module 6
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterator

from iios.execution.oms.integration.constants import (
    DEFAULT_MAX_HISTORY,
    IntegrationEventType,
    OMSState,
)


@dataclass(frozen=True)
class HistoryEntry:
    """
    Immutable record of one integration-level state change or event.
    """
    entry_id:   str   = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: IntegrationEventType = IntegrationEventType.OMS_STARTED
    oms_state:  OMSState = OMSState.RUNNING
    succeeded:  bool  = True
    detail:     str   = ""
    occurred_at: float = field(default_factory=time.time)
    metadata:   dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id":    self.entry_id,
            "event_type":  self.event_type.value,
            "oms_state":   self.oms_state.value,
            "succeeded":   self.succeeded,
            "detail":      self.detail,
            "occurred_at": self.occurred_at,
        }


class IntegrationHistory:
    """
    Thread-safe, bounded, append-only history of OMS integration events.

    Oldest entries are dropped when `max_entries` is reached.
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_HISTORY) -> None:
        self._max_entries = max_entries
        self._entries:    list[HistoryEntry] = []
        self._lock        = threading.RLock()

    def append(self, entry: HistoryEntry) -> None:
        """Add an entry; trim oldest if at capacity."""
        with self._lock:
            if len(self._entries) >= self._max_entries:
                self._entries.pop(0)
            self._entries.append(entry)

    def all(self) -> list[HistoryEntry]:
        with self._lock:
            return list(self._entries)

    def latest(self, n: int = 50) -> list[HistoryEntry]:
        with self._lock:
            return list(self._entries[-n:])

    def by_event_type(
        self, event_type: IntegrationEventType
    ) -> list[HistoryEntry]:
        with self._lock:
            return [e for e in self._entries if e.event_type == event_type]

    def by_oms_state(self, state: OMSState) -> list[HistoryEntry]:
        with self._lock:
            return [e for e in self._entries if e.oms_state == state]

    def failed(self) -> list[HistoryEntry]:
        with self._lock:
            return [e for e in self._entries if not e.succeeded]

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def to_dict(self) -> dict[str, Any]:
        return {
            "count":       self.count,
            "max_entries": self._max_entries,
        }

    def __len__(self) -> int:
        return self.count

    def __iter__(self) -> Iterator[HistoryEntry]:
        with self._lock:
            snapshot = list(self._entries)
        return iter(snapshot)
