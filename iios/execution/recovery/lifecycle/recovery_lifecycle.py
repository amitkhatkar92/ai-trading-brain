"""iios/execution/recovery/lifecycle/recovery_lifecycle.py
==================================================
RecoveryLifecycle — primary public API for the C7 Execution Recovery
Lifecycle.

Manages state transitions for RecoverySession objects.
Owns: registry, factory, validator, statistics, history, event dispatch.

RESPONSIBILITIES:
  - Create recovery sessions from context or parameters.
  - Enforce state transitions via the strict state machine.
  - Emit domain events to registered listeners.
  - Record terminated sessions in bounded history.
  - Accumulate runtime statistics.

DOES NOT:
  - Perform recovery actions.
  - Execute failover.
  - Communicate with brokers.
  - Execute trades.

C7 Execution Recovery & Resilience — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_LIFECYCLE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    LIFECYCLE_SYSTEM_ID,
    RecoveryState,
    RecoveryTrigger,
    VERSION,
)
from .exceptions import (
    RecoveryNotRunningError,
    RecoveryValidationError,
)
from .recovery_context import RecoveryContext, make_recovery_context
from .recovery_events import (
    RecoveryEvent,
    _STATE_EVENT_FACTORY,
    make_recovery_created,
)
from .recovery_factory import RecoveryFactory
from .recovery_history import RecoveryHistory
from .recovery_registry import RecoveryRegistry
from .recovery_session import RecoverySession
from .recovery_statistics import RecoveryStatistics
from .recovery_validation import RecoveryValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class RecoveryLifecycle(LifecycleAwareMixin):
    """
    Primary public API for execution recovery lifecycle management.

    Usage::

        lifecycle = RecoveryLifecycle()
        lifecycle.start()

        session = lifecycle.create(
            execution_session_id = "exec-001",
            subsystem_id         = "execution_gateway",
            recovery_trigger     = RecoveryTrigger.AUTOMATIC,
            recovery_reason      = "Gateway timeout exceeded threshold",
        )
        lifecycle.initialize(session.session_id)
        lifecycle.detect(session.session_id)
        lifecycle.assess(session.session_id)
        lifecycle.ready(session.session_id)
        lifecycle.begin_recovery(session.session_id)
        lifecycle.verify(session.session_id)
        lifecycle.complete(session.session_id)
        lifecycle.archive(session.session_id)

        lifecycle.stop()
    """

    def __init__(
        self,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
        max_history:  int = DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._registry  = RecoveryRegistry(max_sessions=max_sessions)
        self._factory   = RecoveryFactory()
        self._validator = RecoveryValidator()
        self._stats     = RecoveryStatistics()
        self._history   = RecoveryHistory(
            max_sessions    = max_history,
            max_transitions = max_history * 10,
            max_events      = max_history * 10,
        )
        self._listeners:       List[Callable[[RecoveryEvent], None]] = []
        self._listeners_lock   = threading.Lock()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        self._registry.start()
        self._factory.start()
        _audit.log_lifecycle_event(
            LIFECYCLE_SYSTEM_ID,
            EngineState.STOPPED,
            EngineState.RUNNING,
            VERSION,
        )
        _log.info(
            "RecoveryLifecycle started.",
            system_id=LIFECYCLE_SYSTEM_ID,
            version=VERSION,
        )

    def _on_stop(self) -> None:
        self._factory.stop()
        self._registry.stop()
        _audit.log_lifecycle_event(
            LIFECYCLE_SYSTEM_ID,
            EngineState.RUNNING,
            EngineState.STOPPED,
            VERSION,
        )
        _log.info(
            "RecoveryLifecycle stopped.",
            system_id=LIFECYCLE_SYSTEM_ID,
            active_sessions=self._registry.active_count,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise RecoveryNotRunningError()

    def _emit(self, event: RecoveryEvent) -> None:
        self._history.append_event(event)
        with self._listeners_lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:  # noqa: BLE001
                _log.warning(
                    "RecoveryEvent listener raised.",
                    event_type=event.event_type.value,
                    error=str(exc),
                )

    def _transition(
        self,
        session:   RecoverySession,
        new_state: RecoveryState,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> None:
        """
        Apply a validated state transition and record it.

        Validates via RecoveryValidator, applies via session.transition_to(),
        records the transition in history, updates statistics, and emits
        the corresponding domain event.
        """
        val = self._validator.validate_transition(session.state, new_state)
        if not val.is_valid:
            from .exceptions import RecoveryInvalidTransitionError
            raise RecoveryInvalidTransitionError(
                session.state.value, new_state.value, session.session_id
            )

        old_state = session.state
        session.transition_to(new_state, actor=actor, reason=reason)
        self._stats.record_transition()

        if session.transitions:
            self._history.append_transition(session.transitions[-1])

        _log.info(
            "RecoverySession transitioned.",
            session_id = session.session_id,
            from_state = old_state.value,
            to_state   = new_state.value,
            actor      = actor,
        )

        # Emit the matching domain event
        factory_fn = _STATE_EVENT_FACTORY.get(new_state)
        if factory_fn:
            self._emit(factory_fn(session.session_id))

        # Move terminated sessions to history
        if session.state in (
            RecoveryState.COMPLETED,
            RecoveryState.FAILED,
            RecoveryState.ABORTED,
        ):
            self._history.append_session(session)

    # ── Session creation ──────────────────────────────────────────────────────

    def create(
        self,
        execution_session_id: str,
        subsystem_id:         str,
        recovery_trigger:     RecoveryTrigger,
        recovery_reason:      str,
        *,
        workflow_id:       Optional[str]            = None,
        failure_id:        Optional[str]            = None,
        recovery_plan_id:  Optional[str]            = None,
        recovery_version:  int                      = 1,
        metadata:          Optional[Dict[str, Any]] = None,
    ) -> RecoverySession:
        """
        Create and register a new RecoverySession.

        Returns the session in CREATED state.

        Raises
        ------
        RecoveryNotRunningError
            If the lifecycle engine is not running.
        RecoveryValidationError
            If the context fails validation.
        """
        self._assert_running()
        context = make_recovery_context(
            execution_session_id = execution_session_id,
            subsystem_id         = subsystem_id,
            recovery_trigger     = recovery_trigger,
            recovery_reason      = recovery_reason,
            workflow_id          = workflow_id,
            failure_id           = failure_id,
            recovery_plan_id     = recovery_plan_id,
            recovery_version     = recovery_version,
            metadata             = metadata,
        )
        result = self._validator.validate_context(context)
        if not result.is_valid:
            raise RecoveryValidationError(
                "Context validation failed.",
                errors=tuple(result.errors),
            )
        session = self._factory.create(context)
        self._registry.store(session)
        self._stats.record_created()
        self._emit(make_recovery_created(session.session_id))
        return session

    def create_from_context(self, context: RecoveryContext) -> RecoverySession:
        """Create and register a session from a pre-built RecoveryContext."""
        self._assert_running()
        result = self._validator.validate_context(context)
        if not result.is_valid:
            raise RecoveryValidationError(
                "Context validation failed.",
                errors=tuple(result.errors),
            )
        session = self._factory.create(context)
        self._registry.store(session)
        self._stats.record_created()
        self._emit(make_recovery_created(session.session_id))
        return session

    # ── Lifecycle transition methods ──────────────────────────────────────────

    def initialize(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RecoverySession:
        """CREATED → INITIALIZING."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(session, RecoveryState.INITIALIZING, actor=actor, reason=reason)
        return session

    def detect(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RecoverySession:
        """INITIALIZING → DETECTING."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(session, RecoveryState.DETECTING, actor=actor, reason=reason)
        return session

    def assess(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RecoverySession:
        """DETECTING → ASSESSING."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(session, RecoveryState.ASSESSING, actor=actor, reason=reason)
        return session

    def ready(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RecoverySession:
        """ASSESSING → READY."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(session, RecoveryState.READY, actor=actor, reason=reason)
        return session

    def begin_recovery(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RecoverySession:
        """READY → RECOVERING.  Sets session start_time."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(session, RecoveryState.RECOVERING, actor=actor, reason=reason)
        return session

    def verify(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RecoverySession:
        """RECOVERING → VERIFYING."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(session, RecoveryState.VERIFYING, actor=actor, reason=reason)
        return session

    def retry_recovery(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "Retrying recovery after verification failure.",
    ) -> RecoverySession:
        """VERIFYING → RECOVERING (retry loop)."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(session, RecoveryState.RECOVERING, actor=actor, reason=reason)
        return session

    def complete(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RecoverySession:
        """VERIFYING → COMPLETED.  Sets session end_time."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(session, RecoveryState.COMPLETED, actor=actor, reason=reason)
        self._stats.record_completed(session.duration_ms)
        return session

    def fail(
        self,
        session_id: str,
        reason:     str = "",
        *,
        actor: str = ACTOR_LIFECYCLE,
    ) -> RecoverySession:
        """
        Any active state → FAILED.

        Sets session end_time and failure_reason.
        """
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(session, RecoveryState.FAILED, actor=actor, reason=reason)
        self._stats.record_failed()
        return session

    def abort(
        self,
        session_id: str,
        reason:     str = "",
        *,
        actor: str = ACTOR_LIFECYCLE,
    ) -> RecoverySession:
        """
        Any interruptible state → ABORTED.

        Sets session end_time and abort_reason.
        """
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(session, RecoveryState.ABORTED, actor=actor, reason=reason)
        self._stats.record_aborted()
        return session

    def archive(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RecoverySession:
        """
        COMPLETED / FAILED / ABORTED → ARCHIVED.

        Moves the session from the active registry to the archive.
        """
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(session, RecoveryState.ARCHIVED, actor=actor, reason=reason)
        self._registry.archive(session_id)
        self._stats.record_archived()
        return session

    # ── Query API ─────────────────────────────────────────────────────────────

    def get_session(self, session_id: str) -> RecoverySession:
        """Return the live session by ID.  Raises if not found."""
        self._assert_running()
        return self._registry.get(session_id)

    def find_session(self, session_id: str) -> Optional[RecoverySession]:
        """Return the session or None if not found."""
        return self._registry.find(session_id)

    def sessions_for_execution(
        self, execution_session_id: str
    ) -> List[RecoverySession]:
        self._assert_running()
        return self._registry.for_execution_session(execution_session_id)

    def sessions_in_state(self, state: RecoveryState) -> List[RecoverySession]:
        self._assert_running()
        return self._registry.for_state(state)

    def active_sessions(self) -> List[RecoverySession]:
        self._assert_running()
        return self._registry.active()

    def statistics(self) -> RecoveryStatistics:
        """Return a copy of the accumulated lifecycle statistics."""
        return self._stats.copy()

    def history(self) -> RecoveryHistory:
        """Return the lifecycle history."""
        return self._history

    def is_running(self) -> bool:
        return self.lifecycle_state() in (EngineState.RUNNING, "running")

    # ── Event dispatch ────────────────────────────────────────────────────────

    def add_event_listener(
        self, listener: Callable[[RecoveryEvent], None]
    ) -> None:
        with self._listeners_lock:
            self._listeners.append(listener)

    def remove_event_listener(
        self, listener: Callable[[RecoveryEvent], None]
    ) -> None:
        with self._listeners_lock:
            self._listeners = [l for l in self._listeners if l != listener]
