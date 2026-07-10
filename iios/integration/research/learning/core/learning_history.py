"""core/learning_history.py — Thread-safe audit log for the Learning Framework."""
from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import DEFAULT_HISTORY_MAX_ENTRIES


@dataclass
class LearningHistoryEntry:
    """A single immutable audit-log entry."""
    entry_id:    str
    entity_type: str   # "job" | "model" | "experiment" | "deployment" | ...
    entity_id:   str
    event_type:  str   # "created" | "started" | "completed" | "failed" | ...
    timestamp:   float
    data:        dict[str, Any]

    @classmethod
    def create(
        cls,
        entity_type: str,
        entity_id:   str,
        event_type:  str,
        data:        Optional[dict] = None,
    ) -> "LearningHistoryEntry":
        return cls(
            entry_id    = f"lh_{uuid.uuid4().hex[:8]}",
            entity_type = entity_type,
            entity_id   = entity_id,
            event_type  = event_type,
            timestamp   = time.time(),
            data        = data or {},
        )


class LearningHistory:
    """Thread-safe circular audit log."""

    def __init__(self, max_entries: int = DEFAULT_HISTORY_MAX_ENTRIES) -> None:
        self._entries:   deque[LearningHistoryEntry] = deque(maxlen=max_entries)
        self._lock       = threading.RLock()

    def append(self, entry: LearningHistoryEntry) -> None:
        with self._lock:
            self._entries.append(entry)

    def query(
        self,
        *,
        entity_id:   Optional[str] = None,
        event_type:  Optional[str] = None,
        entity_type: Optional[str] = None,
        limit:       int            = 100,
    ) -> list[LearningHistoryEntry]:
        with self._lock:
            result = list(self._entries)
        if entity_id is not None:
            result = [e for e in result if e.entity_id == entity_id]
        if event_type is not None:
            result = [e for e in result if e.event_type == event_type]
        if entity_type is not None:
            result = [e for e in result if e.entity_type == entity_type]
        return result[-limit:]

    def latest(self, n: int = 10) -> list[LearningHistoryEntry]:
        with self._lock:
            return list(self._entries)[-n:]

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
