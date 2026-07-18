"""
iios/execution/recovery/engine/recovery_session_manager.py
==========================================================
RecoverySessionManager — bridges M2 engine requests with M1 lifecycle
sessions.

Owns a RecoveryLifecycle instance and exposes engine-level operations
(create_session, initialize, detect, assess, ready, begin_recovery,
verify, complete, fail, abort, archive) that drive M1 state transitions.

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from iios.execution.recovery.lifecycle import (
    RecoveryLifecycle,
    RecoverySession,
    RecoveryState,
    RecoveryTrigger,
)

from .constants import ACTOR_MANAGER, SESSION_MGR_ID, VERSION
from .exceptions import RecoveryEngineNotRunningError, RecoverySessionManagerError
from .recovery_context import RecoveryContext
from .recovery_request import RecoveryRequest

_log = get_logger(__name__)


class RecoverySessionManager(LifecycleAwareMixin):
    """
    Manages M1 RecoverySession objects on behalf of the Recovery Engine.

    Maintains a mapping of request_id → session_id so that engine-layer
    operations can look up the correct M1 session.
    """

    def __init__(self, lifecycle: Optional[RecoveryLifecycle] = None) -> None:
        super().__init__()
        self._lifecycle      = lifecycle or RecoveryLifecycle()
        self._owns_lifecycle = lifecycle is None
        # request_id → session_id
        self._request_sessions: Dict[str, str] = {}
        self._lock = threading.RLock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        if self._owns_lifecycle:
            self._lifecycle.start()
        _log.info("RecoverySessionManager started.", system_id=SESSION_MGR_ID)

    def _on_stop(self) -> None:
        if self._owns_lifecycle:
            self._lifecycle.stop()
        _log.info("RecoverySessionManager stopped.", system_id=SESSION_MGR_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise RecoveryEngineNotRunningError()

    # ── Trigger mapping ───────────────────────────────────────────────────────

    @staticmethod
    def _map_trigger(request: RecoveryRequest) -> RecoveryTrigger:
        from .constants import RecoveryRequestType
        _map = {
            RecoveryRequestType.MANUAL:       RecoveryTrigger.MANUAL,
            RecoveryRequestType.AUTOMATIC:    RecoveryTrigger.AUTOMATIC,
            RecoveryRequestType.SCHEDULED:    RecoveryTrigger.MANUAL,
            RecoveryRequestType.EVENT_DRIVEN: RecoveryTrigger.AUTOMATIC,
            RecoveryRequestType.PRIORITY:     RecoveryTrigger.MANUAL,
        }
        return _map.get(request.request_type, RecoveryTrigger.AUTOMATIC)

    # ── Session operations ────────────────────────────────────────────────────

    def create_session(
        self,
        request: RecoveryRequest,
        context: RecoveryContext,
    ) -> RecoverySession:
        """Create an M1 RecoverySession for the given request."""
        self._assert_running()
        trigger = self._map_trigger(request)
        session = self._lifecycle.create(
            execution_session_id = request.execution_session_id,
            subsystem_id         = request.subsystem_id,
            recovery_trigger     = trigger,
            recovery_reason      = request.recovery_reason,
            workflow_id          = context.workflow_id,
            failure_id           = context.failure_id,
            recovery_plan_id     = context.recovery_plan_id,
        )
        with self._lock:
            self._request_sessions[request.request_id] = session.session_id
        _log.info(
            "Recovery session created.",
            request_id = request.request_id,
            session_id = session.session_id,
        )
        return session

    def _get_session(self, request_id: str) -> RecoverySession:
        with self._lock:
            session_id = self._request_sessions.get(request_id)
        if session_id is None:
            raise RecoverySessionManagerError(
                f"No session found for request_id={request_id!r}"
            )
        return self._lifecycle.get_session(session_id)

    def initialize(self, request_id: str, *, actor: str = ACTOR_MANAGER) -> None:
        session = self._get_session(request_id)
        self._lifecycle.initialize(session.session_id, actor=actor)

    def detect(self, request_id: str, *, actor: str = ACTOR_MANAGER) -> None:
        session = self._get_session(request_id)
        self._lifecycle.detect(session.session_id, actor=actor)

    def assess(self, request_id: str, *, actor: str = ACTOR_MANAGER) -> None:
        session = self._get_session(request_id)
        self._lifecycle.assess(session.session_id, actor=actor)

    def ready(self, request_id: str, *, actor: str = ACTOR_MANAGER) -> None:
        session = self._get_session(request_id)
        self._lifecycle.ready(session.session_id, actor=actor)

    def begin_recovery(self, request_id: str, *, actor: str = ACTOR_MANAGER) -> None:
        session = self._get_session(request_id)
        self._lifecycle.begin_recovery(session.session_id, actor=actor)

    def verify(self, request_id: str, *, actor: str = ACTOR_MANAGER) -> None:
        session = self._get_session(request_id)
        self._lifecycle.verify(session.session_id, actor=actor)

    def complete(self, request_id: str, *, actor: str = ACTOR_MANAGER) -> None:
        session = self._get_session(request_id)
        self._lifecycle.complete(session.session_id, actor=actor)

    def fail(self, request_id: str, reason: str, *, actor: str = ACTOR_MANAGER) -> None:
        try:
            session = self._get_session(request_id)
        except RecoverySessionManagerError:
            return  # session never created — nothing to fail
        try:
            self._lifecycle.fail(session.session_id, reason, actor=actor)
        except Exception as exc:
            _log.warning(
                "Failed to mark session as FAILED.",
                request_id=request_id,
                error=str(exc),
            )

    def abort(self, request_id: str, reason: str, *, actor: str = ACTOR_MANAGER) -> None:
        try:
            session = self._get_session(request_id)
        except RecoverySessionManagerError:
            return
        try:
            self._lifecycle.abort(session.session_id, reason, actor=actor)
        except Exception as exc:
            _log.warning(
                "Failed to mark session as ABORTED.",
                request_id=request_id,
                error=str(exc),
            )

    def archive(self, request_id: str, *, actor: str = ACTOR_MANAGER) -> None:
        try:
            session = self._get_session(request_id)
        except RecoverySessionManagerError:
            return
        try:
            self._lifecycle.archive(session.session_id)
        except Exception as exc:
            _log.warning(
                "Failed to archive session.",
                request_id=request_id,
                error=str(exc),
            )

    def get_session_for_request(self, request_id: str) -> Optional[RecoverySession]:
        """Return the M1 session for the given request, or None."""
        with self._lock:
            session_id = self._request_sessions.get(request_id)
        if session_id is None:
            return None
        return self._lifecycle.find_session(session_id)

    def active_sessions(self) -> List[RecoverySession]:
        return self._lifecycle.active_sessions()

    @property
    def lifecycle(self) -> RecoveryLifecycle:
        return self._lifecycle
