"""
iios/execution/analytics/engine/analytics_session_manager.py
============================================================
AnalyticsSessionManager — manages analytics lifecycle sessions on behalf
of the Execution Analytics Engine.

Bridges the engine's request/pipeline model to the M1 AnalyticsLifecycle
session state machine.  Maintains a request_id → session_id mapping so the
engine can always locate the lifecycle session for any active request.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Dict, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from iios.execution.analytics.lifecycle import (
    AnalyticsLifecycle,
    AnalyticsMode,
    AnalyticsScope,
    AnalyticsSession,
    AnalyticsTrigger,
)

from .constants import (
    ACTOR_ENGINE,
    DEFAULT_MAX_SESSIONS,
    SESSION_MGR_SYSTEM_ID,
)
from .exceptions import AnalyticsEngineNotRunningError, AnalyticsSessionManagerError

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class AnalyticsSessionManager(LifecycleAwareMixin):
    """
    Manages AnalyticsSession objects via M1 AnalyticsLifecycle.

    Owns a single AnalyticsLifecycle instance and wraps every state
    transition method so that callers only need a request_id — never a
    raw session_id.

    Thread-safe.  Must be started before use.
    """

    def __init__(self, max_sessions: int = DEFAULT_MAX_SESSIONS) -> None:
        super().__init__()
        self._lifecycle             = AnalyticsLifecycle(max_sessions=max_sessions)
        self._request_to_session:   Dict[str, str] = {}
        self._lock                  = threading.RLock()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        self._lifecycle.start()
        _log.info("AnalyticsSessionManager started.", system_id=SESSION_MGR_SYSTEM_ID)

    def _on_stop(self) -> None:
        self._lifecycle.stop()
        _log.info("AnalyticsSessionManager stopped.", system_id=SESSION_MGR_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise AnalyticsEngineNotRunningError()

    # ── Session creation ──────────────────────────────────────────────────────

    def create_session(
        self,
        request_id:           str,
        execution_session_id: str,
        *,
        analytics_scope:    AnalyticsScope   = AnalyticsScope.EXECUTION,
        analytics_mode:     AnalyticsMode    = AnalyticsMode.ON_DEMAND,
        analytics_trigger:  AnalyticsTrigger = AnalyticsTrigger.AUTOMATIC,
        workflow_id:        str              = "",
        portfolio_id:       str              = "",
        strategy_id:        str              = "",
        actor:              str              = ACTOR_ENGINE,
    ) -> AnalyticsSession:
        """Create an analytics session and map request_id → session_id."""
        self._assert_running()
        session = self._lifecycle.create(
            execution_session_id,
            analytics_scope   = analytics_scope,
            analytics_mode    = analytics_mode,
            analytics_trigger = analytics_trigger,
            workflow_id       = workflow_id,
            portfolio_id      = portfolio_id,
            strategy_id       = strategy_id,
            actor             = actor,
        )
        with self._lock:
            self._request_to_session[request_id] = session.session_id
        return session

    # ── State transition wrappers ─────────────────────────────────────────────

    def initialize_session(self, request_id: str, *, actor: str = ACTOR_ENGINE) -> None:
        """CREATED → INITIALIZING."""
        self._lifecycle.initialize(self._sid(request_id), actor=actor)

    def collect_session(self, request_id: str, *, actor: str = ACTOR_ENGINE) -> None:
        """INITIALIZING / ANALYZING / RESUMING → COLLECTING."""
        self._lifecycle.collect(self._sid(request_id), actor=actor)

    def analyze_session(self, request_id: str, *, actor: str = ACTOR_ENGINE) -> None:
        """COLLECTING / ACTIVE / RESUMING → ANALYZING."""
        self._lifecycle.analyze(self._sid(request_id), actor=actor)

    def ready_session(self, request_id: str, *, actor: str = ACTOR_ENGINE) -> None:
        """ANALYZING / RESUMING → READY."""
        self._lifecycle.ready(self._sid(request_id), actor=actor)

    def activate_session(self, request_id: str, *, actor: str = ACTOR_ENGINE) -> None:
        """READY / RESUMING → ACTIVE."""
        self._lifecycle.activate(self._sid(request_id), actor=actor)

    def complete_session(self, request_id: str, *, actor: str = ACTOR_ENGINE) -> None:
        """ACTIVE → COMPLETED → ARCHIVED."""
        sid = self._sid(request_id)
        self._lifecycle.complete(sid, actor=actor)
        self._lifecycle.archive(sid, actor=actor)

    def fail_session(
        self,
        request_id: str,
        *,
        reason: str = "",
        actor:  str = ACTOR_ENGINE,
    ) -> None:
        """Any non-terminal state → FAILED."""
        self._lifecycle.fail(self._sid(request_id), reason=reason, actor=actor)

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_session(self, request_id: str) -> Optional[AnalyticsSession]:
        """Return the live session for request_id, or None if not found."""
        with self._lock:
            sid = self._request_to_session.get(request_id)
        if sid is None:
            return None
        return self._lifecycle.find(sid)

    def get_session_id(self, request_id: str) -> Optional[str]:
        """Return the session_id for request_id, or None."""
        with self._lock:
            return self._request_to_session.get(request_id)

    def remove_mapping(self, request_id: str) -> None:
        """Remove the request → session mapping (call after archiving)."""
        with self._lock:
            self._request_to_session.pop(request_id, None)

    # ── Listener forwarding ───────────────────────────────────────────────────

    def add_listener(self, listener) -> None:
        self._lifecycle.add_listener(listener)

    def remove_listener(self, listener) -> None:
        self._lifecycle.remove_listener(listener)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def active_session_count(self) -> int:
        with self._lock:
            return len(self._request_to_session)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _sid(self, request_id: str) -> str:
        with self._lock:
            sid = self._request_to_session.get(request_id)
        if sid is None:
            raise AnalyticsSessionManagerError(
                f"No session mapped for request_id={request_id!r}"
            )
        return sid
