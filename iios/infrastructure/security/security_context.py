"""
iios/infrastructure/security/security_context.py
==================================================
Thread-local security context — tracks the currently authenticated principal
and active session for the executing thread.  Similar in spirit to the
CacheContext but scoped to security state.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator, Optional

from .security_constants import ANONYMOUS_PRINCIPAL_ID, SYSTEM_PRINCIPAL_ID
from .security_models import PrincipalRecord, SessionRecord

__all__ = [
    "SecurityContext",
    "get_security_context",
    "reset_security_context",
    "current_principal_id",
    "current_session_id",
    "security_scope",
    "system_scope",
]

_context_lock = threading.Lock()
_context: Optional["SecurityContext"] = None

_thread_local = threading.local()


# ── Thread-local helpers ─────────────────────────────────────────────────────

def _get_tl() -> threading.local:
    return _thread_local


def current_principal_id() -> str:
    """Return the principal_id of the currently authenticated principal on this thread."""
    return getattr(_thread_local, "principal_id", ANONYMOUS_PRINCIPAL_ID)


def current_session_id() -> Optional[str]:
    """Return the active session_id for this thread, or None."""
    return getattr(_thread_local, "session_id", None)


@contextmanager
def security_scope(
    principal_id: str,
    session_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> Generator[None, None, None]:
    """Context manager that sets the security context for the current thread.

    Usage::

        with security_scope("user:alice", session_id="sess-123"):
            # code runs as alice
            assert current_principal_id() == "user:alice"
    """
    old_principal = getattr(_thread_local, "principal_id", ANONYMOUS_PRINCIPAL_ID)
    old_session = getattr(_thread_local, "session_id", None)
    old_meta = getattr(_thread_local, "metadata", {})

    _thread_local.principal_id = principal_id
    _thread_local.session_id = session_id
    _thread_local.metadata = metadata or {}
    try:
        yield
    finally:
        _thread_local.principal_id = old_principal
        _thread_local.session_id = old_session
        _thread_local.metadata = old_meta


@contextmanager
def system_scope() -> Generator[None, None, None]:
    """Elevate to the IIOS system principal for internal operations."""
    with security_scope(SYSTEM_PRINCIPAL_ID):
        yield


# ── SecurityContext singleton ─────────────────────────────────────────────────

class SecurityContext:
    """Thread-safe singleton that provides security state accessors.

    Most callers should use the module-level convenience functions
    ``current_principal_id()`` and ``security_scope()`` instead.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._principals: dict[str, PrincipalRecord] = {}
        self._sessions: dict[str, SessionRecord] = {}

    # ── Principal cache ───────────────────────────────────────────────────────

    def cache_principal(self, record: PrincipalRecord) -> None:
        with self._lock:
            self._principals[record.principal_id] = record

    def get_principal(self, principal_id: str) -> Optional[PrincipalRecord]:
        with self._lock:
            return self._principals.get(principal_id)

    def remove_principal(self, principal_id: str) -> bool:
        with self._lock:
            return self._principals.pop(principal_id, None) is not None

    # ── Session cache ─────────────────────────────────────────────────────────

    def cache_session(self, session: SessionRecord) -> None:
        with self._lock:
            self._sessions[session.session_id] = session

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        with self._lock:
            return self._sessions.get(session_id)

    def remove_session(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    # ── Thread-local accessors ────────────────────────────────────────────────

    @property
    def principal_id(self) -> str:
        return current_principal_id()

    @property
    def session_id(self) -> Optional[str]:
        return current_session_id()

    @property
    def metadata(self) -> dict[str, Any]:
        return dict(getattr(_thread_local, "metadata", {}))

    def reset(self) -> None:
        with self._lock:
            self._principals.clear()
            self._sessions.clear()


# ── Singleton accessors ───────────────────────────────────────────────────────

def get_security_context() -> SecurityContext:
    global _context
    with _context_lock:
        if _context is None:
            _context = SecurityContext()
        return _context


def reset_security_context() -> None:
    global _context
    with _context_lock:
        if _context is not None:
            _context.reset()
        _context = None
