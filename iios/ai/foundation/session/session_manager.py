"""
session_manager.py -- iios.ai.foundation.session
=================================================
:class:`AISessionManager` -- thread-safe session registry with TTL
expiry enforcement.

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional

from .ai_session       import AISession
from .session_factory  import SessionFactory
from .session_metadata import SessionMetadata
from .session_state    import SessionState, TERMINAL_SESSION_STATES
from ..exceptions      import (
    AISessionNotFoundError,
    AISessionLimitError,
    AISessionExpiredError,
)


class AISessionManager:
    """
    Manages the full lifecycle of :class:`AISession` objects.

    Responsibilities
    ----------------
    * Create sessions via the injected :class:`SessionFactory`.
    * Register and look up sessions by ID.
    * Enforce max-concurrent-session limit.
    * Detect and expire sessions whose TTL has elapsed.
    * Remove terminal sessions from the active registry.

    Parameters
    ----------
    factory :      :class:`SessionFactory` used to create sessions.
    max_sessions : Maximum number of concurrent non-terminal sessions.
    """

    def __init__(
        self,
        factory:      Optional[SessionFactory] = None,
        max_sessions: int                       = 500,
    ) -> None:
        self._factory:     SessionFactory            = factory or SessionFactory()
        self._max:         int                       = max_sessions
        self._lock:        threading.Lock            = threading.Lock()
        self._sessions:    Dict[str, AISession]      = {}
        self._closed:      Dict[str, AISession]      = {}   # bounded terminal store
        self._max_closed:  int                       = 1_000

    # ── Session creation ──────────────────────────────────────────────────────

    def create_session(
        self,
        module_id:  str,
        *,
        priority:   str   = "normal",
        user_id:    str   = "",
        ttl_s:      float = 300.0,
        capability: str   = "completion",
        trace_id:   str   = "",
        **tags: str,
    ) -> AISession:
        """
        Create, register, and activate a new session.

        Returns the session in ACTIVE state.

        Raises
        ------
        AISessionLimitError
            If the max concurrent session limit is reached.
        """
        with self._lock:
            self._expire_stale()
            active_count = len(self._sessions)
            if active_count >= self._max:
                raise AISessionLimitError(self._max)

        session = self._factory.create(
            module_id  = module_id,
            priority   = priority,
            user_id    = user_id,
            ttl_s      = ttl_s,
            capability = capability,
            trace_id   = trace_id,
            **tags,
        )
        session.activate()

        with self._lock:
            self._sessions[session.session_id] = session

        return session

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get_session(self, session_id: str) -> AISession:
        """
        Return the active session for ``session_id``.

        Raises
        ------
        AISessionNotFoundError
            If the session does not exist (or has been removed after termination).
        AISessionExpiredError
            If the session's TTL has elapsed.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise AISessionNotFoundError(session_id)
        if session.metadata.is_expired() and not session.is_terminal:
            session.expire()
            self._remove_session(session_id)
            raise AISessionExpiredError(session_id)
        return session

    def find_session(self, session_id: str) -> Optional[AISession]:
        """Return the session or ``None`` without raising."""
        try:
            return self.get_session(session_id)
        except (AISessionNotFoundError, AISessionExpiredError):
            return None

    # ── Session management ────────────────────────────────────────────────────

    def close_session(self, session_id: str) -> None:
        """Complete and remove a session from the active registry."""
        session = self.get_session(session_id)
        if not session.is_terminal:
            session.complete()
        self._remove_session(session_id)

    def cancel_session(self, session_id: str, reason: str = "") -> None:
        """Cancel a session."""
        session = self.get_session(session_id)
        if not session.is_terminal:
            session.cancel(reason)
        self._remove_session(session_id)

    def fail_session(self, session_id: str, reason: str) -> None:
        """Mark a session as failed."""
        session = self.get_session(session_id)
        if not session.is_terminal:
            session.fail(reason)
        self._remove_session(session_id)

    # ── Statistics ────────────────────────────────────────────────────────────

    def active_count(self) -> int:
        """Number of currently active (non-terminal) sessions."""
        with self._lock:
            return len(self._sessions)

    def all_sessions(self) -> List[AISession]:
        """Return a snapshot of all active sessions."""
        with self._lock:
            return list(self._sessions.values())

    def status(self) -> Dict:
        """Return a structured status dict."""
        with self._lock:
            return {
                "active_sessions": len(self._sessions),
                "closed_sessions": len(self._closed),
                "max_sessions":    self._max,
            }

    # ── Housekeeping ──────────────────────────────────────────────────────────

    def expire_stale(self) -> int:
        """Expire all sessions whose TTL has elapsed.  Returns eviction count."""
        with self._lock:
            return self._expire_stale()

    # ── Internals ─────────────────────────────────────────────────────────────

    def _expire_stale(self) -> int:
        expired_ids = [
            sid for sid, s in self._sessions.items()
            if s.metadata.is_expired() and not s.is_terminal
        ]
        for sid in expired_ids:
            self._sessions[sid].expire()
            self._archive(self._sessions.pop(sid))
        return len(expired_ids)

    def _remove_session(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                self._archive(session)

    def _archive(self, session: AISession) -> None:
        """Move session to the closed archive (bounded FIFO)."""
        self._closed[session.session_id] = session
        if len(self._closed) > self._max_closed:
            oldest_id = next(iter(self._closed))
            del self._closed[oldest_id]
