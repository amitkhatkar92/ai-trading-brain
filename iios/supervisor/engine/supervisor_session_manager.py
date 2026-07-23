"""
supervisor_session_manager.py — iios.supervisor.engine
-------------------------------------------------------
Thin orchestration wrapper around the M1 SupervisorLifecycle.

Drives lifecycle sessions through the prescribed sequence:
  create → initialize → discover → validate_session → mark_ready
       → start_supervising → [start_monitoring] → complete / fail

No business logic here. Every method delegates to SupervisorLifecycle.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger
from iios.supervisor.lifecycle import (
    SupervisorLifecycle,
    SupervisorSession,
    SupervisorType,
    SupervisorScope,
)

from .exceptions import SupervisorSessionError

_log = get_logger(__name__)


class SupervisorSessionManager:
    """
    Manages lifecycle sessions for supervisor workflows.

    Wraps :class:`iios.supervisor.lifecycle.SupervisorLifecycle` and exposes
    the canonical transition sequence required by the Supervisor Engine.

    Parameters
    ----------
    lifecycle : Injected SupervisorLifecycle instance.
    """

    def __init__(self, lifecycle: Optional[SupervisorLifecycle] = None) -> None:
        self._lifecycle = lifecycle or SupervisorLifecycle()
        self._lock      = threading.Lock()
        self._active: Dict[str, SupervisorSession] = {}

    # ------------------------------------------------------------------
    # Start / stop
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the underlying lifecycle (idempotent)."""
        state = self._lifecycle.lifecycle_state().value
        if state not in ("running",):
            self._lifecycle.start()

    def stop(self) -> None:
        """Fail all active sessions then stop the underlying lifecycle."""
        with self._lock:
            sessions = list(self._active.values())
            self._active.clear()
        for session in sessions:
            try:
                self._lifecycle.fail(session.session_id, reason="engine stopped")
            except Exception:   # noqa: BLE001
                pass
        try:
            self._lifecycle.stop()
        except Exception:       # noqa: BLE001
            pass
        _log.debug(
            f"SupervisorSessionManager stopped ({len(sessions)} sessions failed)"
        )

    # ------------------------------------------------------------------
    # Session lifecycle methods
    # ------------------------------------------------------------------

    def create_session(
        self,
        supervision_id: str,
        subsystem_id:   str,
        *,
        supervisor_type:  SupervisorType  = SupervisorType.GOVERNANCE,
        supervisor_scope: SupervisorScope = SupervisorScope.ENTERPRISE,
        metadata:         Optional[Dict[str, Any]] = None,
    ) -> SupervisorSession:
        """Create and register a new supervisor session."""
        try:
            session = self._lifecycle.create(
                supervision_id,
                supervisor_type  = supervisor_type,
                supervisor_scope = supervisor_scope,
                metadata         = dict(metadata or {}),
            )
            with self._lock:
                self._active[session.session_id] = session
            return session
        except Exception as exc:
            raise SupervisorSessionError(
                str(exc), session_id=f"supervisor:{supervision_id}"
            ) from exc

    def initialize_session(self, session: SupervisorSession) -> SupervisorSession:
        """Transition session → INITIALIZING."""
        try:
            return self._lifecycle.initialize(session.session_id)
        except Exception as exc:
            raise SupervisorSessionError(str(exc), session_id=session.session_id) from exc

    def discover_session(self, session: SupervisorSession) -> SupervisorSession:
        """Transition session → DISCOVERING."""
        try:
            return self._lifecycle.discover(session.session_id)
        except Exception as exc:
            raise SupervisorSessionError(str(exc), session_id=session.session_id) from exc

    def validate_session(self, session: SupervisorSession) -> SupervisorSession:
        """Transition session → VALIDATING."""
        try:
            return self._lifecycle.validate_session(session.session_id)
        except Exception as exc:
            raise SupervisorSessionError(str(exc), session_id=session.session_id) from exc

    def ready_session(self, session: SupervisorSession) -> SupervisorSession:
        """Transition session → READY."""
        try:
            return self._lifecycle.mark_ready(session.session_id)
        except Exception as exc:
            raise SupervisorSessionError(str(exc), session_id=session.session_id) from exc

    def supervise_session(self, session: SupervisorSession) -> SupervisorSession:
        """Transition session → SUPERVISING."""
        try:
            return self._lifecycle.start_supervising(session.session_id)
        except Exception as exc:
            raise SupervisorSessionError(str(exc), session_id=session.session_id) from exc

    def monitor_session(self, session: SupervisorSession) -> SupervisorSession:
        """Transition session → MONITORING."""
        try:
            return self._lifecycle.start_monitoring(session.session_id)
        except Exception as exc:
            raise SupervisorSessionError(str(exc), session_id=session.session_id) from exc

    def complete_session(self, session: SupervisorSession) -> SupervisorSession:
        """Transition session → COMPLETED."""
        try:
            s = self._lifecycle.complete(session.session_id)
            with self._lock:
                self._active.pop(session.session_id, None)
            return s
        except Exception as exc:
            raise SupervisorSessionError(str(exc), session_id=session.session_id) from exc

    def fail_session(
        self,
        session: SupervisorSession,
        *,
        error: str = "",
    ) -> SupervisorSession:
        """Transition session → FAILED."""
        try:
            s = self._lifecycle.fail(session.session_id, reason=error)
            with self._lock:
                self._active.pop(session.session_id, None)
            return s
        except Exception as exc:
            raise SupervisorSessionError(str(exc), session_id=session.session_id) from exc

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def active_session_count(self) -> int:
        with self._lock:
            return len(self._active)

    def active_sessions(self) -> list:
        with self._lock:
            return list(self._active.values())
