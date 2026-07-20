"""
decision_history.py — iios.decision.lifecycle
===============================================
Thread-safe bounded history for decision lifecycle events and transitions.

C9 Decision Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from collections import deque
from typing import List, Optional

from .decision_events import DecisionEvent
from .decision_transition import DecisionTransition
from .constants import DEFAULT_MAX_HISTORY, DEFAULT_MAX_TRANSITIONS


class DecisionHistory:
    """
    Thread-safe, bounded history for decision lifecycle events and
    state transitions.

    Both queues evict the oldest entry automatically when at capacity
    (``collections.deque(maxlen=N)``).

    Parameters
    ----------
    max_events :      Maximum events to retain (default 1 000).
    max_transitions : Maximum transitions to retain (default 50 000).
    """

    def __init__(
        self,
        max_events:      int = DEFAULT_MAX_HISTORY,
        max_transitions: int = DEFAULT_MAX_TRANSITIONS,
    ) -> None:
        self._lock: threading.Lock          = threading.Lock()
        self._events:      deque[DecisionEvent]      = deque(maxlen=max_events)
        self._transitions: deque[DecisionTransition] = deque(maxlen=max_transitions)

    # ------------------------------------------------------------------
    # Record
    # ------------------------------------------------------------------
    def record_event(self, event: DecisionEvent) -> None:
        """Append *event* to the event history."""
        with self._lock:
            self._events.append(event)

    def record_transition(self, transition: DecisionTransition) -> None:
        """Append *transition* to the transition history."""
        with self._lock:
            self._transitions.append(transition)

    # ------------------------------------------------------------------
    # Query — events
    # ------------------------------------------------------------------
    def events(self) -> List[DecisionEvent]:
        """Return all retained events (oldest first)."""
        with self._lock:
            return list(self._events)

    def latest_event(self) -> Optional[DecisionEvent]:
        """Return the most recently recorded event, or ``None``."""
        with self._lock:
            return self._events[-1] if self._events else None

    def event_count(self) -> int:
        """Number of retained events."""
        with self._lock:
            return len(self._events)

    def events_for_session(self, session_id: str) -> List[DecisionEvent]:
        """Return all retained events matching *session_id*."""
        with self._lock:
            return [e for e in self._events if e.session_id == session_id]

    def events_for_decision(self, decision_id: str) -> List[DecisionEvent]:
        """Return all retained events matching *decision_id*."""
        with self._lock:
            return [e for e in self._events if e.decision_id == decision_id]

    def events_by_type(self, event_type_value: str) -> List[DecisionEvent]:
        """Return events whose ``event_type.value`` matches *event_type_value*."""
        with self._lock:
            return [e for e in self._events if e.event_type.value == event_type_value]

    # ------------------------------------------------------------------
    # Query — transitions
    # ------------------------------------------------------------------
    def transitions(self) -> List[DecisionTransition]:
        """Return all retained transitions (oldest first)."""
        with self._lock:
            return list(self._transitions)

    def latest_transition(self) -> Optional[DecisionTransition]:
        """Return the most recently recorded transition, or ``None``."""
        with self._lock:
            return self._transitions[-1] if self._transitions else None

    def transition_count(self) -> int:
        """Number of retained transitions."""
        with self._lock:
            return len(self._transitions)

    def transitions_for_session(self, session_id: str) -> List[DecisionTransition]:
        """Return all retained transitions for *session_id*."""
        with self._lock:
            return [t for t in self._transitions if t.session_id == session_id]

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------
    def clear(self) -> None:
        """Discard all retained history entries."""
        with self._lock:
            self._events.clear()
            self._transitions.clear()

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"DecisionHistory("
                f"events={len(self._events)}, "
                f"transitions={len(self._transitions)})"
            )
