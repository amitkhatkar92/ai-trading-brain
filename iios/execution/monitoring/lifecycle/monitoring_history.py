"""iios/execution/monitoring/lifecycle/monitoring_history.py
==================================================
MonitoringHistory — thread-safe bounded history of monitoring sessions,
transitions, and events.

C6 Execution Intelligence — Phase 6, Module 1
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Callable, List, Optional

from .constants import DEFAULT_MAX_HISTORY, MonitoringState


class MonitoringHistory:
    """
    Thread-safe bounded deque for monitoring sessions, transitions,
    and domain events.
    """

    def __init__(
        self,
        max_sessions:     int = DEFAULT_MAX_HISTORY,
        max_transitions:  int = DEFAULT_MAX_HISTORY,
        max_events:       int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._max_sessions    = max(1, max_sessions)
        self._max_transitions = max(1, max_transitions)
        self._max_events      = max(1, max_events)

        self._sessions:     deque = deque(maxlen=self._max_sessions)
        self._transitions:  deque = deque(maxlen=self._max_transitions)
        self._events:       deque = deque(maxlen=self._max_events)
        self._lock = threading.Lock()

    # ── Writers ───────────────────────────────────────────────────────────────

    def append_session(self, session) -> None:
        with self._lock:
            self._sessions.append(session)

    def append_transition(self, transition) -> None:
        with self._lock:
            self._transitions.append(transition)

    def append_event(self, event) -> None:
        with self._lock:
            self._events.append(event)

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._transitions.clear()
            self._events.clear()

    # ── Session queries ───────────────────────────────────────────────────────

    def sessions(self) -> list:
        with self._lock:
            return list(self._sessions)

    def latest_session(self):
        with self._lock:
            return self._sessions[-1] if self._sessions else None

    def sessions_by_portfolio(self, portfolio_id: str) -> list:
        with self._lock:
            return [s for s in self._sessions
                    if s.portfolio_id == portfolio_id]

    def sessions_by_execution(self, execution_session_id: str) -> list:
        with self._lock:
            return [s for s in self._sessions
                    if s.execution_session_id == execution_session_id]

    def active_sessions(self) -> list:
        with self._lock:
            return [s for s in self._sessions
                    if s.state == MonitoringState.ACTIVE]

    def failed_sessions(self) -> list:
        with self._lock:
            return [s for s in self._sessions
                    if s.state == MonitoringState.FAILED]

    def stopped_sessions(self) -> list:
        with self._lock:
            return [s for s in self._sessions
                    if s.state == MonitoringState.STOPPED]

    # ── Transition queries ────────────────────────────────────────────────────

    def transitions(self) -> list:
        with self._lock:
            return list(self._transitions)

    def latest_transition(self):
        with self._lock:
            return self._transitions[-1] if self._transitions else None

    def transitions_for_session(self, session_id: str) -> list:
        with self._lock:
            return [t for t in self._transitions if t.session_id == session_id]

    # ── Event queries ─────────────────────────────────────────────────────────

    def events(self) -> list:
        with self._lock:
            return list(self._events)

    def latest_event(self):
        with self._lock:
            return self._events[-1] if self._events else None

    def events_for_session(self, session_id: str) -> list:
        with self._lock:
            return [e for e in self._events if e.session_id == session_id]

    def events_matching(self, predicate: Callable) -> list:
        with self._lock:
            return [e for e in self._events if predicate(e)]

    # ── State ─────────────────────────────────────────────────────────────────

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
