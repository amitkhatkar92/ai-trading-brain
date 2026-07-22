"""
risk_history.py — iios.risk.lifecycle
========================================
Bounded history of risk lifecycle events and transitions.

C11 Risk Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, List, Optional

from .constants import DEFAULT_MAX_HISTORY, DEFAULT_MAX_TRANSITIONS, RiskEventType


class RiskHistory:
    """
    Thread-safe bounded history of lifecycle events and transitions.

    Usage
    -----
    ::

        history = RiskHistory()
        history.record_event(event)
        history.record_transition(transition)
        latest = history.latest_event()

    Parameters
    ----------
    max_events :      Maximum lifecycle events to retain.
    max_transitions : Maximum transition records to retain.
    """

    def __init__(
        self,
        max_events:      int = DEFAULT_MAX_HISTORY,
        max_transitions: int = DEFAULT_MAX_TRANSITIONS,
    ) -> None:
        self._lock:        threading.Lock = threading.Lock()
        self._events:      Deque          = deque(maxlen=max_events)
        self._transitions: Deque          = deque(maxlen=max_transitions)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def record_event(self, event: object) -> None:
        """Append a :class:`RiskEvent`."""
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

    def events_for_session(self, session_id: str) -> List:
        """Return all events for a given session_id."""
        with self._lock:
            return [e for e in self._events
                    if getattr(e, "session_id", None) == session_id]

    def events_for_portfolio(self, portfolio_id: str) -> List:
        """Return all events for a given portfolio_id."""
        with self._lock:
            return [e for e in self._events
                    if getattr(e, "portfolio_id", None) == portfolio_id]

    def events_by_type(self, event_type: RiskEventType) -> List:
        """Return all events of the given type."""
        with self._lock:
            return [e for e in self._events
                    if getattr(e, "event_type", None) == event_type]

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def record_transition(self, transition: object) -> None:
        """Append a :class:`RiskTransition`."""
        with self._lock:
            self._transitions.append(transition)

    def transitions(self) -> List:
        """Return all retained transitions (oldest first)."""
        with self._lock:
            return list(self._transitions)

    def latest_transition(self) -> Optional[object]:
        """Return the most recent transition, or None."""
        with self._lock:
            return self._transitions[-1] if self._transitions else None

    def transition_count(self) -> int:
        with self._lock:
            return len(self._transitions)

    def transitions_for_session(self, session_id: str) -> List:
        """Return all transitions for a given session_id."""
        with self._lock:
            return [t for t in self._transitions
                    if getattr(t, "session_id", None) == session_id]

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._transitions.clear()
