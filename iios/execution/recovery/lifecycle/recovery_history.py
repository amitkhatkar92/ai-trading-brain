"""iios/execution/recovery/lifecycle/recovery_history.py
==================================================
RecoveryHistory — thread-safe bounded deque history for the recovery
lifecycle subsystem.

Stores terminated recovery sessions, their transitions, and domain events.

C7 Execution Recovery & Resilience — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Callable, Deque, List, Optional

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .recovery_session    import RecoverySession
    from .recovery_transition import RecoveryTransition
    from .recovery_events     import RecoveryEvent

_DEFAULT_MAX = 1_000


class RecoveryHistory:
    """
    Thread-safe bounded deque history.

    Stores terminated ``RecoverySession`` objects, individual
    ``RecoveryTransition`` records, and ``RecoveryEvent`` domain events.
    Oldest entries are silently dropped when a deque reaches capacity.
    """

    def __init__(
        self,
        max_sessions:    int = _DEFAULT_MAX,
        max_transitions: int = _DEFAULT_MAX * 10,
        max_events:      int = _DEFAULT_MAX * 10,
    ) -> None:
        self._max_sessions    = max(1, max_sessions)
        self._max_transitions = max(1, max_transitions)
        self._max_events      = max(1, max_events)

        self._sessions:    Deque["RecoverySession"]    = deque(maxlen=self._max_sessions)
        self._transitions: Deque["RecoveryTransition"] = deque(maxlen=self._max_transitions)
        self._events:      Deque["RecoveryEvent"]      = deque(maxlen=self._max_events)
        self._lock = threading.Lock()

    # ── Writes ────────────────────────────────────────────────────────────────

    def append_session(self, session: "RecoverySession") -> None:
        with self._lock:
            self._sessions.append(session)

    def append_transition(self, transition: "RecoveryTransition") -> None:
        with self._lock:
            self._transitions.append(transition)

    def append_event(self, event: "RecoveryEvent") -> None:
        with self._lock:
            self._events.append(event)

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._transitions.clear()
            self._events.clear()

    # ── Session reads ─────────────────────────────────────────────────────────

    def sessions(self) -> List["RecoverySession"]:
        with self._lock:
            return list(self._sessions)

    def latest_session(self) -> Optional["RecoverySession"]:
        with self._lock:
            return self._sessions[-1] if self._sessions else None

    def sessions_for_execution(self, execution_session_id: str) -> List["RecoverySession"]:
        with self._lock:
            return [s for s in self._sessions if s.execution_session_id == execution_session_id]

    def sessions_for_subsystem(self, subsystem_id: str) -> List["RecoverySession"]:
        with self._lock:
            return [s for s in self._sessions if s.subsystem_id == subsystem_id]

    def completed_sessions(self) -> List["RecoverySession"]:
        from .constants import RecoveryState
        with self._lock:
            return [s for s in self._sessions if s.state == RecoveryState.COMPLETED]

    def failed_sessions(self) -> List["RecoverySession"]:
        from .constants import RecoveryState
        with self._lock:
            return [s for s in self._sessions if s.state == RecoveryState.FAILED]

    # ── Transition reads ──────────────────────────────────────────────────────

    def transitions(self) -> List["RecoveryTransition"]:
        with self._lock:
            return list(self._transitions)

    def transitions_for_session(self, session_id: str) -> List["RecoveryTransition"]:
        with self._lock:
            return [t for t in self._transitions if t.session_id == session_id]

    def latest_transition(self) -> Optional["RecoveryTransition"]:
        with self._lock:
            return self._transitions[-1] if self._transitions else None

    # ── Event reads ───────────────────────────────────────────────────────────

    def events(self) -> List["RecoveryEvent"]:
        with self._lock:
            return list(self._events)

    def events_for_session(self, session_id: str) -> List["RecoveryEvent"]:
        with self._lock:
            return [e for e in self._events if e.session_id == session_id]

    def latest_event(self) -> Optional["RecoveryEvent"]:
        with self._lock:
            return self._events[-1] if self._events else None

    def events_matching(
        self, predicate: Callable[["RecoveryEvent"], bool]
    ) -> List["RecoveryEvent"]:
        with self._lock:
            return [e for e in self._events if predicate(e)]

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
