"""iios/execution/recovery/lifecycle/recovery_registry.py
==================================================
RecoveryRegistry — LifecycleAwareMixin session store for the recovery
lifecycle subsystem.

C7 Execution Recovery & Resilience — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    DEFAULT_MAX_SESSIONS,
    REGISTRY_SYSTEM_ID,
    RecoveryState,
    VERSION,
)
from .exceptions import (
    RecoveryNotRunningError,
    RecoverySessionAlreadyExistsError,
    RecoverySessionNotFoundError,
)
from .recovery_session import RecoverySession

_log = get_logger(__name__)


class RecoveryRegistry(LifecycleAwareMixin):
    """
    Thread-safe, lifecycle-aware in-memory store for RecoverySession objects.

    Sessions remain in the registry until explicitly archived or cleared.
    Archived sessions are moved to a separate archive store.
    """

    def __init__(self, max_sessions: int = DEFAULT_MAX_SESSIONS) -> None:
        super().__init__()
        self._max_sessions = max(1, max_sessions)
        self._sessions: Dict[str, RecoverySession]          = {}
        self._archive:  Dict[str, RecoverySession]          = {}
        self._lock = threading.RLock()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info(
            "RecoveryRegistry started.",
            system_id=REGISTRY_SYSTEM_ID,
            version=VERSION,
        )

    def _on_stop(self) -> None:
        with self._lock:
            active = len(self._sessions)
        _log.info(
            "RecoveryRegistry stopped.",
            system_id=REGISTRY_SYSTEM_ID,
            active_sessions=active,
        )

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise RecoveryNotRunningError()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def store(self, session: RecoverySession) -> None:
        self._assert_running()
        with self._lock:
            if session.session_id in self._sessions:
                raise RecoverySessionAlreadyExistsError(session.session_id)
            if len(self._sessions) >= self._max_sessions:
                # Evict oldest session to prevent unbounded growth
                oldest = next(iter(self._sessions))
                _log.warning(
                    "RecoveryRegistry capacity reached; evicting session.",
                    evicted_session_id=oldest,
                )
                del self._sessions[oldest]
            self._sessions[session.session_id] = session

    def get(self, session_id: str) -> RecoverySession:
        self._assert_running()
        with self._lock:
            s = self._sessions.get(session_id)
        if s is None:
            raise RecoverySessionNotFoundError(session_id)
        return s

    def find(self, session_id: str) -> Optional[RecoverySession]:
        with self._lock:
            return self._sessions.get(session_id)

    def archive(self, session_id: str) -> None:
        """Move a terminal session from active store to archive."""
        self._assert_running()
        with self._lock:
            s = self._sessions.get(session_id)
            if s is None:
                raise RecoverySessionNotFoundError(session_id)
            self._archive[session_id] = s
            del self._sessions[session_id]

    def find_archived(self, session_id: str) -> Optional[RecoverySession]:
        with self._lock:
            return self._archive.get(session_id)

    # ── Queries ───────────────────────────────────────────────────────────────

    def all(self) -> List[RecoverySession]:
        with self._lock:
            return list(self._sessions.values())

    def all_archived(self) -> List[RecoverySession]:
        with self._lock:
            return list(self._archive.values())

    def for_execution_session(self, execution_session_id: str) -> List[RecoverySession]:
        with self._lock:
            return [s for s in self._sessions.values() if s.execution_session_id == execution_session_id]

    def for_state(self, state: RecoveryState) -> List[RecoverySession]:
        with self._lock:
            return [s for s in self._sessions.values() if s.state == state]

    def active(self) -> List[RecoverySession]:
        from .constants import ACTIVE_STATES
        with self._lock:
            return [s for s in self._sessions.values() if s.state in ACTIVE_STATES]

    def terminal(self) -> List[RecoverySession]:
        from .constants import TERMINAL_STATES
        with self._lock:
            return [s for s in self._sessions.values() if s.state in TERMINAL_STATES]

    def contains(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._sessions)

    @property
    def active_count(self) -> int:
        from .constants import ACTIVE_STATES
        with self._lock:
            return sum(1 for s in self._sessions.values() if s.state in ACTIVE_STATES)

    @property
    def archive_count(self) -> int:
        with self._lock:
            return len(self._archive)

    def clear(self) -> None:
        self._assert_running()
        with self._lock:
            self._sessions.clear()
            self._archive.clear()
