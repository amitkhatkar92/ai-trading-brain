"""
ai_session.py -- iios.ai.foundation.session
=============================================
:class:`AISession` -- the primary session domain object.

An AISession represents a single bounded AI operation context with a
defined lifecycle, TTL, and state machine.

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

import time
import threading
from typing import Any, Callable, Dict, List, Optional

from .session_state    import (
    SessionState,
    TERMINAL_SESSION_STATES,
    VALID_SESSION_TRANSITIONS,
    can_session_transition,
)
from .session_metadata import SessionMetadata
from ..exceptions      import (
    AISessionExpiredError,
    AISessionStateError,
)


class AISession:
    """
    Thread-safe AI session with state machine lifecycle.

    Consumers obtain sessions via :class:`SessionFactory` and manage
    them via :class:`AISessionManager`.

    State machine
    -------------
    PENDING -> ACTIVE -> COMPLETED
                      -> FAILED
                      -> CANCELLED
                      -> EXPIRED
                      -> SUSPENDED -> ACTIVE

    Parameters
    ----------
    metadata : Immutable session descriptor (created by :class:`SessionFactory`).
    """

    def __init__(self, metadata: SessionMetadata) -> None:
        self._metadata:  SessionMetadata      = metadata
        self._state:     SessionState         = SessionState.PENDING
        self._lock:      threading.Lock       = threading.Lock()
        self._history:   List[Dict[str, Any]] = []
        self._error:     Optional[str]        = None
        self._context:   Dict[str, Any]       = {}
        self._callbacks: List[Callable[["AISession", SessionState, SessionState], None]] = []
        self._activated_at: Optional[float]   = None
        self._closed_at:    Optional[float]   = None

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def session_id(self) -> str:
        return self._metadata.session_id

    @property
    def module_id(self) -> str:
        return self._metadata.module_id

    @property
    def trace_id(self) -> str:
        return self._metadata.trace_id

    @property
    def metadata(self) -> SessionMetadata:
        return self._metadata

    @property
    def state(self) -> SessionState:
        with self._lock:
            return self._state

    @property
    def is_active(self) -> bool:
        return self.state == SessionState.ACTIVE

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_SESSION_STATES

    @property
    def error(self) -> Optional[str]:
        with self._lock:
            return self._error

    @property
    def duration_s(self) -> Optional[float]:
        """Elapsed wall-clock time from activation to close (or now)."""
        if self._activated_at is None:
            return None
        end = self._closed_at or time.time()
        return end - self._activated_at

    # ── State transitions ─────────────────────────────────────────────────────

    def activate(self) -> None:
        """Transition PENDING -> ACTIVE."""
        self._transition(SessionState.ACTIVE)
        with self._lock:
            self._activated_at = time.time()

    def suspend(self) -> None:
        """Transition ACTIVE -> SUSPENDED."""
        self._transition(SessionState.SUSPENDED)

    def resume(self) -> None:
        """Transition SUSPENDED -> ACTIVE."""
        self._transition(SessionState.ACTIVE)

    def complete(self) -> None:
        """Transition ACTIVE -> COMPLETED."""
        self._close(SessionState.COMPLETED)

    def cancel(self, reason: str = "") -> None:
        """Transition current -> CANCELLED."""
        with self._lock:
            if reason:
                self._error = reason
        self._close(SessionState.CANCELLED)

    def fail(self, reason: str) -> None:
        """Transition current -> FAILED."""
        with self._lock:
            self._error = reason
        self._close(SessionState.FAILED)

    def expire(self) -> None:
        """Transition current -> EXPIRED (called by TTL watchdog)."""
        self._close(SessionState.EXPIRED)

    # ── Context storage ───────────────────────────────────────────────────────

    def set(self, key: str, value: Any) -> None:
        """Store an arbitrary value in the session context dict."""
        with self._lock:
            self._context[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the session context dict."""
        with self._lock:
            return self._context.get(key, default)

    # ── Callbacks ────────────────────────────────────────────────────────────

    def on_state_change(
        self,
        callback: Callable[["AISession", SessionState, SessionState], None],
    ) -> None:
        """Register a callback invoked on every state transition."""
        with self._lock:
            self._callbacks.append(callback)

    # ── Observability ─────────────────────────────────────────────────────────

    def history(self) -> List[Dict[str, Any]]:
        """Return a copy of the state-change history."""
        with self._lock:
            return list(self._history)

    def status(self) -> Dict[str, Any]:
        """Return a structured status dict (safe for logging)."""
        return {
            "session_id":   self.session_id,
            "module_id":    self.module_id,
            "trace_id":     self.trace_id,
            "state":        self._state.value,
            "priority":     self._metadata.priority,
            "capability":   self._metadata.capability,
            "is_terminal":  self.is_terminal,
            "error":        self._error,
            "duration_s":   self.duration_s,
            "created_at":   self._metadata.created_at,
            "expires_at":   self._metadata.expires_at,
        }

    # ── Internals ─────────────────────────────────────────────────────────────

    def _transition(self, new_state: SessionState) -> None:
        with self._lock:
            self._check_expired()
            old = self._state
            if not can_session_transition(old, new_state):
                raise AISessionStateError(
                    self.session_id, old.value, f"transition to {new_state.value}"
                )
            self._state = new_state
            entry = {"from": old.value, "to": new_state.value, "at": time.time()}
            self._history.append(entry)
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb(self, old, new_state)
            except Exception:
                pass

    def _close(self, terminal: SessionState) -> None:
        with self._lock:
            old = self._state
            if old in TERMINAL_SESSION_STATES:
                return  # already closed; idempotent
            if not can_session_transition(old, terminal):
                # force close from any non-terminal state
                self._state = terminal
            else:
                self._state = terminal
            self._closed_at = time.time()
            entry = {"from": old.value, "to": terminal.value, "at": self._closed_at}
            self._history.append(entry)
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb(self, old, terminal)
            except Exception:
                pass

    def _check_expired(self) -> None:
        """Raise AISessionExpiredError if TTL has elapsed (called under lock)."""
        if self._metadata.is_expired() and self._state not in TERMINAL_SESSION_STATES:
            self._state = SessionState.EXPIRED
            raise AISessionExpiredError(self.session_id)

    def __repr__(self) -> str:
        return (
            f"<AISession id={self.session_id!r} "
            f"state={self._state.value!r} "
            f"module={self.module_id!r}>"
        )
