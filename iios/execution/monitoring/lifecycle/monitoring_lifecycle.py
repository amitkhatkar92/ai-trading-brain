"""iios/execution/monitoring/lifecycle/monitoring_lifecycle.py
==================================================
MonitoringLifecycle — primary public API for the Execution Monitoring
Lifecycle.

Manages lifecycle state transitions for MonitoringSession objects,
owns the registry, factory, validator, statistics, and event dispatch.

C6 Execution Intelligence — Phase 6, Module 1
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_LIFECYCLE,
    LIFECYCLE_SYSTEM_ID,
    VERSION,
    MonitoringState,
)
from .exceptions import (
    MonitoringLifecycleNotRunningError,
    MonitoringValidationError,
)
from .monitoring_context import MonitoringContext, make_monitoring_context
from .monitoring_events import (
    MonitoringEvent,
    _STATE_EVENT_FACTORY,
    make_monitoring_archived,
    make_monitoring_created,
    make_monitoring_failed,
    make_monitoring_paused,
    make_monitoring_resumed,
    make_monitoring_started,
    make_monitoring_stopped,
)
from .monitoring_factory import MonitoringFactory
from .monitoring_history import MonitoringHistory
from .monitoring_registry import MonitoringRegistry
from .monitoring_session import MonitoringSession
from .monitoring_statistics import MonitoringStatistics
from .monitoring_validation import MonitoringValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class MonitoringLifecycle(LifecycleAwareMixin):
    """
    Primary public API for execution monitoring lifecycle management.

    Responsibilities:
    - Create monitoring sessions from context.
    - Enforce state transitions via the MonitoringSession domain object.
    - Persist sessions in MonitoringRegistry.
    - Accumulate metrics in MonitoringStatistics.
    - Emit domain events to registered listeners.
    - Record terminated sessions in MonitoringHistory.
    """

    def __init__(
        self,
        max_sessions: int = 5_000,
        max_history:  int = 1_000,
    ) -> None:
        super().__init__()
        self._registry  = MonitoringRegistry(max_sessions=max_sessions)
        self._factory   = MonitoringFactory()
        self._validator = MonitoringValidator()
        self._stats     = MonitoringStatistics()
        self._history   = MonitoringHistory(
            max_sessions=max_history,
            max_transitions=max_history,
            max_events=max_history,
        )
        self._listeners: List[Callable[[MonitoringEvent], None]] = []
        self._listeners_lock = threading.Lock()

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
            "MonitoringLifecycle started.",
            system_id=LIFECYCLE_SYSTEM_ID,
            version=VERSION,
        )

    def _on_stop(self) -> None:
        self._factory.stop()
        self._registry.stop()
        _log.info(
            "MonitoringLifecycle stopped.",
            system_id=LIFECYCLE_SYSTEM_ID,
            active=self._registry.active_count,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        state = self.lifecycle_state()
        if state not in (EngineState.RUNNING, "running"):
            raise MonitoringLifecycleNotRunningError()

    def _emit(self, event: MonitoringEvent) -> None:
        self._history.append_event(event)
        with self._listeners_lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:  # noqa: BLE001
                _log.warning(
                    "Event listener raised exception.",
                    event_type=event.event_type.value,
                    error=str(exc),
                )

    def _transition(
        self,
        session: MonitoringSession,
        new_state: MonitoringState,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> None:
        """Apply a transition and record it in history + stats."""
        old_state = session.state
        session.transition_to(new_state, actor=actor, reason=reason)
        self._stats.record_transition()
        if session.transitions:
            self._history.append_transition(session.transitions[-1])

        _log.info(
            "MonitoringSession transitioned.",
            session_id=session.session_id,
            from_state=old_state.value,
            to_state=new_state.value,
        )

    # ── Session creation ──────────────────────────────────────────────────────

    def create(
        self,
        execution_session_id: str,
        portfolio_id: str,
        *,
        gateway_id:         Optional[str] = None,
        workflow_id:        Optional[str] = None,
        strategy_id:        Optional[str] = None,
        order_id:           Optional[str] = None,
        monitoring_version: int = 1,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> MonitoringSession:
        """
        Create a new monitoring session and register it.

        Returns the session in CREATED state.
        """
        self._assert_running()
        context = make_monitoring_context(
            execution_session_id=execution_session_id,
            portfolio_id=portfolio_id,
            gateway_id=gateway_id,
            workflow_id=workflow_id,
            strategy_id=strategy_id,
            order_id=order_id,
            monitoring_version=monitoring_version,
            metadata=metadata,
        )
        result = self._validator.validate_context(context)
        if not result.is_valid:
            raise MonitoringValidationError(
                "Context validation failed.",
                errors=tuple(result.errors),
            )
        session = self._factory.create(context)
        self._registry.store(session)
        self._stats.record_created()
        self._emit(make_monitoring_created(session.session_id))
        return session

    def create_from_context(self, context: MonitoringContext) -> MonitoringSession:
        """Create a session from a pre-built MonitoringContext."""
        self._assert_running()
        result = self._validator.validate_context(context)
        if not result.is_valid:
            raise MonitoringValidationError(
                "Context validation failed.",
                errors=tuple(result.errors),
            )
        session = self._factory.create(context)
        self._registry.store(session)
        self._stats.record_created()
        self._emit(make_monitoring_created(session.session_id))
        return session

    # ── Lifecycle transition methods ──────────────────────────────────────────

    def initialize(
        self, session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: str = ""
    ) -> MonitoringSession:
        """CREATED → INITIALIZING."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(
            session, MonitoringState.INITIALIZING, actor=actor, reason=reason
        )
        return session

    def begin(
        self, session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: str = ""
    ) -> MonitoringSession:
        """INITIALIZING → STARTING."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(
            session, MonitoringState.STARTING, actor=actor, reason=reason
        )
        return session

    def mark_active(
        self, session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: str = ""
    ) -> MonitoringSession:
        """STARTING → ACTIVE.  Emits MONITORING_STARTED."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(
            session, MonitoringState.ACTIVE, actor=actor, reason=reason
        )
        self._stats.record_started()
        self._emit(make_monitoring_started(session_id))
        return session

    def pause(
        self, session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: str = ""
    ) -> MonitoringSession:
        """ACTIVE → PAUSED.  Emits MONITORING_PAUSED."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(
            session, MonitoringState.PAUSED, actor=actor, reason=reason
        )
        self._stats.record_paused()
        self._emit(make_monitoring_paused(session_id))
        return session

    def resume(
        self, session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: str = ""
    ) -> MonitoringSession:
        """PAUSED → RESUMING."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(
            session, MonitoringState.RESUMING, actor=actor, reason=reason
        )
        return session

    def mark_resumed(
        self, session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: str = ""
    ) -> MonitoringSession:
        """RESUMING → ACTIVE.  Emits MONITORING_RESUMED."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(
            session, MonitoringState.ACTIVE, actor=actor, reason=reason
        )
        self._stats.record_resumed()
        self._emit(make_monitoring_resumed(session_id))
        return session

    def cease(
        self, session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: str = ""
    ) -> MonitoringSession:
        """ACTIVE / PAUSED / RESUMING → STOPPING."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(
            session, MonitoringState.STOPPING, actor=actor, reason=reason
        )
        return session

    def mark_stopped(
        self, session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: str = ""
    ) -> MonitoringSession:
        """STOPPING → STOPPED.  Emits MONITORING_STOPPED."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(
            session, MonitoringState.STOPPED, actor=actor, reason=reason
        )
        duration = session.duration_ms
        self._stats.record_stopped(duration)
        self._history.append_session(session)
        self._emit(make_monitoring_stopped(session_id))
        return session

    def fail(
        self,
        session_id: str,
        reason: str = "",
        *,
        actor: str = ACTOR_LIFECYCLE,
    ) -> MonitoringSession:
        """Any non-terminal state → FAILED.  Emits MONITORING_FAILED."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(
            session, MonitoringState.FAILED, actor=actor, reason=reason
        )
        self._stats.record_failed()
        self._history.append_session(session)
        self._emit(make_monitoring_failed(session_id, reason=reason))
        return session

    def archive(
        self, session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: str = ""
    ) -> MonitoringSession:
        """STOPPED / FAILED → ARCHIVED.  Moves to archive store."""
        self._assert_running()
        session = self._registry.get(session_id)
        self._transition(
            session, MonitoringState.ARCHIVED, actor=actor, reason=reason
        )
        self._registry.archive(session_id)
        self._stats.record_archived()
        self._emit(make_monitoring_archived(session_id))
        return session

    # ── Query methods ─────────────────────────────────────────────────────────

    def get(self, session_id: str) -> MonitoringSession:
        self._assert_running()
        return self._registry.get(session_id)

    def all(self) -> List[MonitoringSession]:
        self._assert_running()
        return self._registry.all()

    def active(self) -> List[MonitoringSession]:
        self._assert_running()
        return self._registry.active()

    def failed(self) -> List[MonitoringSession]:
        self._assert_running()
        return self._registry.failed()

    def by_portfolio_id(self, portfolio_id: str) -> List[MonitoringSession]:
        self._assert_running()
        return self._registry.by_portfolio_id(portfolio_id)

    def by_execution_session_id(
        self, execution_session_id: str
    ) -> List[MonitoringSession]:
        self._assert_running()
        return self._registry.by_execution_session_id(execution_session_id)

    # ── Observability ─────────────────────────────────────────────────────────

    def statistics(self) -> MonitoringStatistics:
        return self._stats.copy()

    def history(self) -> MonitoringHistory:
        return self._history

    def validate_session(self, session_id: str):
        self._assert_running()
        session = self._registry.get(session_id)
        return self._validator.validate_session(session)

    # ── Event listeners ───────────────────────────────────────────────────────

    def add_event_listener(
        self, listener: Callable[[MonitoringEvent], None]
    ) -> None:
        with self._listeners_lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_event_listener(
        self, listener: Callable[[MonitoringEvent], None]
    ) -> None:
        with self._listeners_lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass
