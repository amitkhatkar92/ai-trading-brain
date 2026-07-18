"""
iios/execution/analytics/lifecycle/analytics_history.py
=======================================================
AnalyticsHistory — bounded, thread-safe history of completed analytics
sessions, transitions, and events.

C8 Execution Analytics & Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from collections import deque
from typing import List, Optional, TYPE_CHECKING

from .constants import DEFAULT_MAX_HISTORY

if TYPE_CHECKING:
    from .analytics_session import AnalyticsSession
    from .analytics_transition import AnalyticsTransition
    from .analytics_events import AnalyticsEvent


class AnalyticsHistory:
    """
    Bounded, thread-safe store of terminated analytics sessions,
    their transitions, and emitted events.
    """

    def __init__(
        self,
        max_sessions:    int = DEFAULT_MAX_HISTORY,
        max_transitions: int = DEFAULT_MAX_HISTORY * 10,
        max_events:      int = DEFAULT_MAX_HISTORY * 10,
    ) -> None:
        self._lock        = threading.Lock()
        self._sessions:    deque["AnalyticsSession"]   = deque(maxlen=max_sessions)
        self._transitions: deque["AnalyticsTransition"] = deque(maxlen=max_transitions)
        self._events:      deque["AnalyticsEvent"]      = deque(maxlen=max_events)

    # ── Append ────────────────────────────────────────────────────────────────

    def record_session(self, session: "AnalyticsSession") -> None:
        with self._lock:
            self._sessions.append(session)

    def record_transition(self, transition: "AnalyticsTransition") -> None:
        with self._lock:
            self._transitions.append(transition)

    def record_event(self, event: "AnalyticsEvent") -> None:
        with self._lock:
            self._events.append(event)

    # ── Read ──────────────────────────────────────────────────────────────────

    def sessions(self) -> List["AnalyticsSession"]:
        with self._lock:
            return list(self._sessions)

    def transitions(self) -> List["AnalyticsTransition"]:
        with self._lock:
            return list(self._transitions)

    def events(self) -> List["AnalyticsEvent"]:
        with self._lock:
            return list(self._events)

    def latest_session(self) -> Optional["AnalyticsSession"]:
        with self._lock:
            return self._sessions[-1] if self._sessions else None

    def latest_event(self) -> Optional["AnalyticsEvent"]:
        with self._lock:
            return self._events[-1] if self._events else None

    # ── Filtered queries ──────────────────────────────────────────────────────

    def sessions_for_execution(
        self, execution_session_id: str
    ) -> List["AnalyticsSession"]:
        with self._lock:
            return [
                s for s in self._sessions
                if s.execution_session_id == execution_session_id
            ]

    def transitions_for_session(
        self, session_id: str
    ) -> List["AnalyticsTransition"]:
        with self._lock:
            return [t for t in self._transitions if t.session_id == session_id]

    def events_for_session(self, session_id: str) -> List["AnalyticsEvent"]:
        with self._lock:
            return [e for e in self._events if e.session_id == session_id]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def session_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    @property
    def transition_count(self) -> int:
        with self._lock:
            return len(self._transitions)

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._transitions.clear()
            self._events.clear()
