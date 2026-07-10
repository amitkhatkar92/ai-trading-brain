"""core/governance_history.py — Thread-safe governance event log."""
from __future__ import annotations

import threading
from collections import deque
from typing import Optional

from iios.integration.research.governance.governance_constants import DEFAULT_HISTORY_MAX_ENTRIES
from iios.integration.research.governance.core.governance_event import GovernanceEvent


class GovernanceHistory:
    """Thread-safe circular governance event log."""

    def __init__(self, max_entries: int = DEFAULT_HISTORY_MAX_ENTRIES) -> None:
        self._events: deque[GovernanceEvent] = deque(maxlen=max_entries)
        self._lock   = threading.RLock()

    def append(self, event: GovernanceEvent) -> None:
        with self._lock:
            self._events.append(event)

    def query(
        self,
        *,
        entity_id:   Optional[str] = None,
        entity_type: Optional[str] = None,
        event_type:  Optional[str] = None,
        actor:       Optional[str] = None,
        limit:       int           = 100,
    ) -> list[GovernanceEvent]:
        with self._lock:
            result = list(self._events)
        if entity_id is not None:
            result = [e for e in result if e.entity_id == entity_id]
        if entity_type is not None:
            result = [e for e in result if e.entity_type == entity_type]
        if event_type is not None:
            result = [e for e in result if e.event_type == event_type]
        if actor is not None:
            result = [e for e in result if e.actor == actor]
        return result[-limit:]

    def latest(self, n: int = 10) -> list[GovernanceEvent]:
        with self._lock:
            return list(self._events)[-n:]

    def count(self) -> int:
        with self._lock:
            return len(self._events)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
