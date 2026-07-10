"""iios/integration/research/core/research_history.py

Append-only audit log for all research framework state changes.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.research.research_constants import (
    DEFAULT_MAX_HISTORY_ENTRIES,
    ResearchEventType,
)


@dataclass
class ResearchHistoryEntry:
    """One audit-log entry."""
    entry_id:    str              = field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str              = ""    # "project" | "experiment" | "dataset" | "session"
    entity_id:   str              = ""
    event_type:  ResearchEventType = ResearchEventType.PROJECT_CREATED
    old_status:  str              = ""
    new_status:  str              = ""
    timestamp:   float            = field(default_factory=time.time)
    actor:       str              = "system"
    details:     dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id":    self.entry_id,
            "entity_type": self.entity_type,
            "entity_id":   self.entity_id,
            "event_type":  self.event_type.value,
            "old_status":  self.old_status,
            "new_status":  self.new_status,
            "timestamp":   self.timestamp,
            "actor":       self.actor,
        }


class ResearchHistory:
    """
    Thread-safe, append-only audit log.

    Stores up to ``max_entries``; older entries are dropped
    (FIFO) once the limit is reached.
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_HISTORY_ENTRIES) -> None:
        self._max     = max_entries
        self._lock    = threading.RLock()
        self._entries: list[ResearchHistoryEntry] = []

    def append(self, entry: ResearchHistoryEntry) -> None:
        with self._lock:
            if len(self._entries) >= self._max:
                self._entries.pop(0)
            self._entries.append(entry)

    def query(
        self,
        entity_id:   str | None = None,
        event_type:  ResearchEventType | None = None,
        entity_type: str | None = None,
        limit:       int = 100,
    ) -> list[ResearchHistoryEntry]:
        with self._lock:
            results = list(self._entries)
        if entity_id:
            results = [e for e in results if e.entity_id == entity_id]
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if entity_type:
            results = [e for e in results if e.entity_type == entity_type]
        return results[-limit:]

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def latest(self, n: int = 10) -> list[ResearchHistoryEntry]:
        with self._lock:
            return list(self._entries[-n:])
