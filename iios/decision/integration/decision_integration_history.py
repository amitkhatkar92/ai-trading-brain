"""
decision_integration_history.py — iios.decision.integration
============================================================
Bounded history of integration requests, responses, and events.

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, List, Optional

from .constants import DEFAULT_MAX_HISTORY, DEFAULT_MAX_EVENTS, IntegrationStatus


class DecisionIntegrationHistory:
    """
    Thread-safe bounded history of completed integration operations.

    Usage
    -----
    ::

        history = DecisionIntegrationHistory()
        history.record_response(response)
        latest = history.latest_response()
        by_decision = history.responses_for_decision("dec-001")

    Parameters
    ----------
    max_responses :  Maximum completed responses to retain.
    max_events :     Maximum integration events to retain.
    """

    def __init__(
        self,
        max_responses: int = DEFAULT_MAX_HISTORY,
        max_events:    int = DEFAULT_MAX_EVENTS,
    ) -> None:
        self._lock:      threading.Lock         = threading.Lock()
        self._responses: Deque                  = deque(maxlen=max_responses)
        self._events:    Deque                  = deque(maxlen=max_events)

    # ------------------------------------------------------------------
    # Response recording
    # ------------------------------------------------------------------

    def record_response(self, response: object) -> None:
        """Append a completed :class:`DecisionIntegrationResponse`."""
        with self._lock:
            self._responses.append(response)

    def responses(self) -> List:
        """Return all retained responses (oldest first)."""
        with self._lock:
            return list(self._responses)

    def latest_response(self) -> Optional[object]:
        """Return the most recent response, or None."""
        with self._lock:
            return self._responses[-1] if self._responses else None

    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    def responses_for_decision(self, decision_id: str) -> List:
        """Return all responses for a given decision_id."""
        with self._lock:
            return [
                r for r in self._responses
                if getattr(r, "decision_id", None) == decision_id
            ]

    def responses_for_session(self, session_id: str) -> List:
        """Return all responses for a given session_id."""
        with self._lock:
            return [
                r for r in self._responses
                if getattr(r, "session_id", None) == session_id
            ]

    def failed_responses(self) -> List:
        """Return all responses with a failure status."""
        with self._lock:
            return [
                r for r in self._responses
                if getattr(r, "is_failure", False)
            ]

    def successful_responses(self) -> List:
        """Return all responses with a success status."""
        with self._lock:
            return [
                r for r in self._responses
                if getattr(r, "is_success", False)
            ]

    # ------------------------------------------------------------------
    # Event recording
    # ------------------------------------------------------------------

    def record_event(self, event: object) -> None:
        """Append an integration event."""
        with self._lock:
            self._events.append(event)

    def events(self) -> List:
        """Return all retained events (oldest first)."""
        with self._lock:
            return list(self._events)

    def latest_event(self) -> Optional[object]:
        """Return the most recent event, or None."""
        with self._lock:
            return self._events[-1] if self._events else None

    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    def events_for_snapshot(self, snapshot_id: str) -> List:
        """Return all events for a given snapshot_id."""
        with self._lock:
            return [
                e for e in self._events
                if getattr(e, "snapshot_id", None) == snapshot_id
            ]

    def events_by_type(self, event_type) -> List:
        """Return all events of the given type."""
        with self._lock:
            return [
                e for e in self._events
                if getattr(e, "event_type", None) == event_type
            ]

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._responses.clear()
            self._events.clear()
