"""iios/execution/monitoring/integration/monitoring_integration_history.py
==================================================
IntegrationHistory — thread-safe bounded deque history for the
integration subsystem.

Stores: responses, snapshots, events, and error records.

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Callable, Deque, List, Optional, TypeVar

# forward references (typed at call sites)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .monitoring_integration_response import MonitoringIntegrationResponse
    from .monitoring_integration_snapshot import MonitoringIntegrationSnapshot
    from .monitoring_integration_events import IntegrationEvent

_T = TypeVar("_T")

_DEFAULT_MAX = 1_000


class IntegrationHistory:
    """
    Thread-safe bounded deque history for integration subsystem artifacts.

    Oldest entries are discarded when the deque is full.
    """

    def __init__(
        self,
        max_responses: int = _DEFAULT_MAX,
        max_snapshots: int = _DEFAULT_MAX,
        max_events:    int = _DEFAULT_MAX,
    ) -> None:
        self._max_responses = max(1, max_responses)
        self._max_snapshots = max(1, max_snapshots)
        self._max_events    = max(1, max_events)

        self._responses: Deque["MonitoringIntegrationResponse"] = deque(
            maxlen=self._max_responses
        )
        self._snapshots: Deque["MonitoringIntegrationSnapshot"] = deque(
            maxlen=self._max_snapshots
        )
        self._events: Deque["IntegrationEvent"] = deque(
            maxlen=self._max_events
        )
        self._lock = threading.Lock()

    # ── Writes ────────────────────────────────────────────────────────────────

    def append_response(self, response: "MonitoringIntegrationResponse") -> None:
        with self._lock:
            self._responses.append(response)

    def append_snapshot(self, snapshot: "MonitoringIntegrationSnapshot") -> None:
        with self._lock:
            self._snapshots.append(snapshot)

    def append_event(self, event: "IntegrationEvent") -> None:
        with self._lock:
            self._events.append(event)

    def clear(self) -> None:
        with self._lock:
            self._responses.clear()
            self._snapshots.clear()
            self._events.clear()

    # ── Response reads ────────────────────────────────────────────────────────

    def responses(self) -> List["MonitoringIntegrationResponse"]:
        with self._lock:
            return list(self._responses)

    def latest_response(self) -> Optional["MonitoringIntegrationResponse"]:
        with self._lock:
            return self._responses[-1] if self._responses else None

    def responses_for_session(self, session_id: str) -> List["MonitoringIntegrationResponse"]:
        with self._lock:
            return [r for r in self._responses if r.session_id == session_id]

    def responses_with_errors(self) -> List["MonitoringIntegrationResponse"]:
        with self._lock:
            return [r for r in self._responses if r.has_errors]

    def responses_with_alerts(self) -> List["MonitoringIntegrationResponse"]:
        with self._lock:
            return [r for r in self._responses if r.has_alerts]

    # ── Snapshot reads ────────────────────────────────────────────────────────

    def snapshots(self) -> List["MonitoringIntegrationSnapshot"]:
        with self._lock:
            return list(self._snapshots)

    def latest_snapshot(self) -> Optional["MonitoringIntegrationSnapshot"]:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    def snapshots_for_session(self, session_id: str) -> List["MonitoringIntegrationSnapshot"]:
        with self._lock:
            return [s for s in self._snapshots if s.session_id == session_id]

    # ── Event reads ───────────────────────────────────────────────────────────

    def events(self) -> List["IntegrationEvent"]:
        with self._lock:
            return list(self._events)

    def latest_event(self) -> Optional["IntegrationEvent"]:
        with self._lock:
            return self._events[-1] if self._events else None

    def events_for_session(self, session_id: str) -> List["IntegrationEvent"]:
        with self._lock:
            return [e for e in self._events if e.session_id == session_id]

    def events_matching(
        self, predicate: Callable[["IntegrationEvent"], bool]
    ) -> List["IntegrationEvent"]:
        with self._lock:
            return [e for e in self._events if predicate(e)]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    @property
    def snapshot_count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)
