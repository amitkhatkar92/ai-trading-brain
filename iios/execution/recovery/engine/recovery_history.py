"""
iios/execution/recovery/engine/recovery_history.py
==================================================
Bounded history store for the Execution Recovery Engine.

Stores requests, responses, events, and snapshots in thread-safe bounded
deques.

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY
from .recovery_events import RecoveryEngineEvent
from .recovery_request import RecoveryRequest
from .recovery_response import RecoveryResponse
from .recovery_snapshot import RecoverySnapshot


class RecoveryEngineHistory:
    """
    Thread-safe bounded history for requests, responses, events, and snapshots.

    When a deque reaches its limit the oldest entry is silently evicted.
    """

    def __init__(
        self,
        max_requests:  int = DEFAULT_MAX_HISTORY,
        max_responses: int = DEFAULT_MAX_HISTORY,
        max_events:    int = DEFAULT_MAX_HISTORY * 10,
        max_snapshots: int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._max_requests  = max(1, max_requests)
        self._max_responses = max(1, max_responses)
        self._max_events    = max(1, max_events)
        self._max_snapshots = max(1, max_snapshots)

        self._requests:  Deque[RecoveryRequest]  = deque(maxlen=self._max_requests)
        self._responses: Deque[RecoveryResponse] = deque(maxlen=self._max_responses)
        self._events:    Deque[RecoveryEngineEvent] = deque(maxlen=self._max_events)
        self._snapshots: Deque[RecoverySnapshot] = deque(maxlen=self._max_snapshots)

        self._lock = threading.Lock()

    # ── Append ────────────────────────────────────────────────────────────────

    def append_request(self, request: RecoveryRequest) -> None:
        with self._lock:
            self._requests.append(request)

    def append_response(self, response: RecoveryResponse) -> None:
        with self._lock:
            self._responses.append(response)

    def append_event(self, event: RecoveryEngineEvent) -> None:
        with self._lock:
            self._events.append(event)

    def append_snapshot(self, snapshot: RecoverySnapshot) -> None:
        with self._lock:
            self._snapshots.append(snapshot)

    # ── Reads — requests ─────────────────────────────────────────────────────

    def requests(self) -> List[RecoveryRequest]:
        with self._lock:
            return list(self._requests)

    def latest_request(self) -> Optional[RecoveryRequest]:
        with self._lock:
            return self._requests[-1] if self._requests else None

    def requests_for_subsystem(self, subsystem_id: str) -> List[RecoveryRequest]:
        with self._lock:
            return [r for r in self._requests if r.subsystem_id == subsystem_id]

    def requests_for_session(self, execution_session_id: str) -> List[RecoveryRequest]:
        with self._lock:
            return [r for r in self._requests if r.execution_session_id == execution_session_id]

    # ── Reads — responses ────────────────────────────────────────────────────

    def responses(self) -> List[RecoveryResponse]:
        with self._lock:
            return list(self._responses)

    def latest_response(self) -> Optional[RecoveryResponse]:
        with self._lock:
            return self._responses[-1] if self._responses else None

    def responses_for_request(self, request_id: str) -> List[RecoveryResponse]:
        with self._lock:
            return [r for r in self._responses if r.request_id == request_id]

    def successful_responses(self) -> List[RecoveryResponse]:
        from .constants import RecoveryResponseStatus
        with self._lock:
            return [r for r in self._responses if r.status == RecoveryResponseStatus.SUCCESS]

    def failed_responses(self) -> List[RecoveryResponse]:
        from .constants import RecoveryResponseStatus
        with self._lock:
            return [r for r in self._responses if r.status == RecoveryResponseStatus.FAILED]

    # ── Reads — events ────────────────────────────────────────────────────────

    def events(self) -> List[RecoveryEngineEvent]:
        with self._lock:
            return list(self._events)

    def latest_event(self) -> Optional[RecoveryEngineEvent]:
        with self._lock:
            return self._events[-1] if self._events else None

    def events_for_request(self, request_id: str) -> List[RecoveryEngineEvent]:
        with self._lock:
            return [e for e in self._events if e.request_id == request_id]

    def events_for_session(self, session_id: str) -> List[RecoveryEngineEvent]:
        with self._lock:
            return [e for e in self._events if e.session_id == session_id]

    def events_matching(
        self, predicate: Callable[[RecoveryEngineEvent], bool]
    ) -> List[RecoveryEngineEvent]:
        with self._lock:
            return [e for e in self._events if predicate(e)]

    # ── Reads — snapshots ─────────────────────────────────────────────────────

    def snapshots(self) -> List[RecoverySnapshot]:
        with self._lock:
            return list(self._snapshots)

    def latest_snapshot(self) -> Optional[RecoverySnapshot]:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    def snapshots_for_session(self, session_id: str) -> List[RecoverySnapshot]:
        with self._lock:
            return [s for s in self._snapshots if s.session_id == session_id]

    def snapshots_for_request(self, request_id: str) -> List[RecoverySnapshot]:
        with self._lock:
            return [s for s in self._snapshots if s.request_id == request_id]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

    @property
    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    @property
    def snapshot_count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    # ── Management ────────────────────────────────────────────────────────────

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._responses.clear()
            self._events.clear()
            self._snapshots.clear()
