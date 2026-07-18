"""
iios/execution/recovery/integration/recovery_integration_history.py
===================================================================
IntegrationHistory — bounded, thread-safe history of integration
requests, responses, and events.

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from collections import deque
from typing import List, Optional, TYPE_CHECKING

from .constants import DEFAULT_MAX_HISTORY

if TYPE_CHECKING:
    from .recovery_integration_request import IntegrationRequest
    from .recovery_integration_response import IntegrationResponse
    from .recovery_integration_events import IntegrationEvent


class IntegrationHistory:
    """
    Bounded, thread-safe history of integration operations.

    Supports access to recent requests, responses, and events with
    filtering by execution session ID.
    """

    def __init__(
        self,
        max_requests:  int = DEFAULT_MAX_HISTORY,
        max_responses: int = DEFAULT_MAX_HISTORY,
        max_events:    int = DEFAULT_MAX_HISTORY * 2,
    ) -> None:
        self._lock = threading.Lock()
        self._requests:  deque["IntegrationRequest"]  = deque(maxlen=max_requests)
        self._responses: deque["IntegrationResponse"] = deque(maxlen=max_responses)
        self._events:    deque["IntegrationEvent"]    = deque(maxlen=max_events)

    # ── Append ────────────────────────────────────────────────────────────────

    def append_request(self, request: "IntegrationRequest") -> None:
        with self._lock:
            self._requests.append(request)

    def append_response(self, response: "IntegrationResponse") -> None:
        with self._lock:
            self._responses.append(response)

    def append_event(self, event: "IntegrationEvent") -> None:
        with self._lock:
            self._events.append(event)

    # ── Read ──────────────────────────────────────────────────────────────────

    def requests(self) -> List["IntegrationRequest"]:
        with self._lock:
            return list(self._requests)

    def responses(self) -> List["IntegrationResponse"]:
        with self._lock:
            return list(self._responses)

    def events(self) -> List["IntegrationEvent"]:
        with self._lock:
            return list(self._events)

    def latest_request(self) -> Optional["IntegrationRequest"]:
        with self._lock:
            return self._requests[-1] if self._requests else None

    def latest_response(self) -> Optional["IntegrationResponse"]:
        with self._lock:
            return self._responses[-1] if self._responses else None

    # ── Filtered ──────────────────────────────────────────────────────────────

    def responses_for_session(
        self, execution_session_id: str
    ) -> List["IntegrationResponse"]:
        with self._lock:
            # Match via request_id cross-reference
            request_ids = {
                r.request_id
                for r in self._requests
                if r.execution_session_id == execution_session_id
            }
            return [r for r in self._responses if r.request_id in request_ids]

    def responses_for_request(self, request_id: str) -> List["IntegrationResponse"]:
        with self._lock:
            return [r for r in self._responses if r.request_id == request_id]

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

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._responses.clear()
            self._events.clear()
