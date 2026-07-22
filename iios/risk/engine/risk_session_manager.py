"""
risk_session_manager.py — iios.risk.engine
=============================================
Thin orchestration wrapper around the M1 RiskLifecycle.

Drives lifecycle sessions through the prescribed sequence:
  create → initialize → collect → validate_session → mark_ready
       → start_assessment → [start_monitoring] → complete / fail

No business logic here.  Every method delegates to RiskLifecycle.

C11 Risk Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger
from iios.risk.lifecycle import RiskLifecycle, RiskSession, RiskType, RiskScope

from .exceptions import RiskSessionError

_log = get_logger(__name__)


class RiskSessionManager:
    """
    Manages lifecycle sessions for risk workflows.

    Wraps :class:`iios.risk.lifecycle.RiskLifecycle` and exposes the
    canonical transition sequence required by the Risk Engine.

    Parameters
    ----------
    lifecycle : Injected RiskLifecycle instance.
    """

    def __init__(self, lifecycle: Optional[RiskLifecycle] = None) -> None:
        self._lifecycle = lifecycle or RiskLifecycle()
        self._lock      = threading.Lock()
        self._active: Dict[str, RiskSession] = {}

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
            except Exception:  # noqa: BLE001
                pass
        try:
            self._lifecycle.stop()
        except Exception:  # noqa: BLE001
            pass
        _log.debug(f"RiskSessionManager stopped ({len(sessions)} sessions failed)")

    # ------------------------------------------------------------------
    # Session lifecycle methods
    # ------------------------------------------------------------------

    def create_session(
        self,
        risk_id:      str,
        portfolio_id: str,
        *,
        risk_type:  RiskType  = RiskType.CUSTOM,
        risk_scope: RiskScope = RiskScope.PORTFOLIO,
        metadata:   Optional[Dict[str, Any]] = None,
    ) -> RiskSession:
        """Create and register a new risk session."""
        try:
            session = self._lifecycle.create(
                risk_id      = risk_id,
                portfolio_id = portfolio_id,
                risk_type    = risk_type,
                risk_scope   = risk_scope,
                metadata     = dict(metadata or {}),
            )
            with self._lock:
                self._active[session.session_id] = session
            return session
        except Exception as exc:
            raise RiskSessionError(
                str(exc), session_id=f"risk:{risk_id}"
            ) from exc

    def initialize_session(self, session: RiskSession) -> RiskSession:
        """Transition session → INITIALIZING."""
        try:
            return self._lifecycle.initialize(session.session_id)
        except Exception as exc:
            raise RiskSessionError(str(exc), session_id=session.session_id) from exc

    def collect_session(self, session: RiskSession) -> RiskSession:
        """Transition session → COLLECTING."""
        try:
            return self._lifecycle.collect(session.session_id)
        except Exception as exc:
            raise RiskSessionError(str(exc), session_id=session.session_id) from exc

    def validate_session(self, session: RiskSession) -> RiskSession:
        """Transition session → VALIDATING."""
        try:
            return self._lifecycle.validate_session(session.session_id)
        except Exception as exc:
            raise RiskSessionError(str(exc), session_id=session.session_id) from exc

    def ready_session(self, session: RiskSession) -> RiskSession:
        """Transition session → READY."""
        try:
            return self._lifecycle.mark_ready(session.session_id)
        except Exception as exc:
            raise RiskSessionError(str(exc), session_id=session.session_id) from exc

    def start_assessment_session(self, session: RiskSession) -> RiskSession:
        """Transition session → ASSESSING."""
        try:
            return self._lifecycle.start_assessment(session.session_id)
        except Exception as exc:
            raise RiskSessionError(str(exc), session_id=session.session_id) from exc

    def start_monitoring_session(self, session: RiskSession) -> RiskSession:
        """Transition session → MONITORING (optional phase)."""
        try:
            return self._lifecycle.start_monitoring(session.session_id)
        except Exception as exc:
            raise RiskSessionError(str(exc), session_id=session.session_id) from exc

    def complete_session(self, session: RiskSession) -> RiskSession:
        """Transition session → COMPLETED."""
        try:
            completed = self._lifecycle.complete(session.session_id)
            with self._lock:
                self._active.pop(session.session_id, None)
            return completed
        except Exception as exc:
            raise RiskSessionError(str(exc), session_id=session.session_id) from exc

    def fail_session(
        self,
        session: RiskSession,
        error:   str = "",
    ) -> RiskSession:
        """Transition session → FAILED."""
        try:
            failed = self._lifecycle.fail(session.session_id, reason=error)
            with self._lock:
                self._active.pop(session.session_id, None)
            return failed
        except Exception as exc:
            raise RiskSessionError(str(exc), session_id=session.session_id) from exc

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_session(self, session_id: str) -> Optional[RiskSession]:
        with self._lock:
            return self._active.get(session_id)

    def active_session_count(self) -> int:
        with self._lock:
            return len(self._active)
