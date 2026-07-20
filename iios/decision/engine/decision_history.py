"""
decision_history.py — iios.decision.engine
============================================
Thread-safe bounded history for decision engine events and responses.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from collections import deque
from typing import List, Optional

from .constants import DEFAULT_MAX_HISTORY
from .decision_events   import DecisionEngineEvent, DecisionEngineEventType
from .decision_response import DecisionResponse


class DecisionEngineHistory:
    """
    Thread-safe, bounded history for engine events and decision responses.

    Both queues evict the oldest entry automatically when at capacity.

    Parameters
    ----------
    max_events :    Maximum events to retain.
    max_responses : Maximum responses to retain.
    """

    def __init__(
        self,
        max_events:    int = DEFAULT_MAX_HISTORY,
        max_responses: int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._lock:      threading.Lock                      = threading.Lock()
        self._events:    deque[DecisionEngineEvent]          = deque(maxlen=max_events)
        self._responses: deque[DecisionResponse]             = deque(maxlen=max_responses)

    # ------------------------------------------------------------------
    # Record
    # ------------------------------------------------------------------
    def record_event(self, event: DecisionEngineEvent) -> None:
        """Append *event* to the engine event history."""
        with self._lock:
            self._events.append(event)

    def record_response(self, response: DecisionResponse) -> None:
        """Append *response* to the response history."""
        with self._lock:
            self._responses.append(response)

    # ------------------------------------------------------------------
    # Query — events
    # ------------------------------------------------------------------
    def events(self) -> List[DecisionEngineEvent]:
        """Return all retained events (oldest first)."""
        with self._lock:
            return list(self._events)

    def latest_event(self) -> Optional[DecisionEngineEvent]:
        """Return the most recently recorded event, or ``None``."""
        with self._lock:
            return self._events[-1] if self._events else None

    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    def events_for_session(self, session_id: str) -> List[DecisionEngineEvent]:
        with self._lock:
            return [e for e in self._events if e.session_id == session_id]

    def events_for_decision(self, decision_id: str) -> List[DecisionEngineEvent]:
        with self._lock:
            return [e for e in self._events if e.decision_id == decision_id]

    def events_by_type(
        self, event_type: DecisionEngineEventType
    ) -> List[DecisionEngineEvent]:
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]

    # ------------------------------------------------------------------
    # Query — responses
    # ------------------------------------------------------------------
    def responses(self) -> List[DecisionResponse]:
        """Return all retained responses (oldest first)."""
        with self._lock:
            return list(self._responses)

    def latest_response(self) -> Optional[DecisionResponse]:
        """Return the most recently recorded response, or ``None``."""
        with self._lock:
            return self._responses[-1] if self._responses else None

    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    def responses_for_decision(self, decision_id: str) -> List[DecisionResponse]:
        with self._lock:
            return [r for r in self._responses if r.decision_id == decision_id]

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------
    def clear(self) -> None:
        """Discard all retained events and responses."""
        with self._lock:
            self._events.clear()
            self._responses.clear()
