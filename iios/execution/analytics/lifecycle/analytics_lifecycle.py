"""
iios/execution/analytics/lifecycle/analytics_lifecycle.py
=========================================================
AnalyticsLifecycle — primary public API for C8 Execution Analytics
Lifecycle management.

Manages state transitions for AnalyticsSession objects.
Owns: registry, factory, validator, statistics, history, event dispatch.

RESPONSIBILITIES:
  - Create analytics sessions from context or parameters.
  - Enforce state transitions via a strict state machine.
  - Emit domain events to registered listeners.
  - Record terminated sessions in bounded history.
  - Accumulate runtime statistics.

DOES NOT:
  - Perform analytics calculations.
  - Compute performance metrics.
  - Execute predictive intelligence.
  - Generate reports.
  - Execute trades.

C8 Execution Analytics & Intelligence — Phase 1, Module 1
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
    VERSION,
    AnalyticsMode,
    AnalyticsScope,
    AnalyticsState,
    AnalyticsTrigger,
)
from .exceptions import (
    AnalyticsNotRunningError,
    AnalyticsSessionNotFoundError,
    AnalyticsValidationError,
)
from .analytics_context import AnalyticsContext, make_analytics_context
from .analytics_events import (
    AnalyticsEvent,
    _STATE_EVENT_FACTORY,
    make_analytics_archived,
    make_analytics_created,
    make_analytics_failed,
)
from .analytics_factory import AnalyticsFactory
from .analytics_history import AnalyticsHistory
from .analytics_registry import AnalyticsRegistry
from .analytics_session import AnalyticsSession
from .analytics_statistics import AnalyticsStatistics
from .analytics_validation import AnalyticsValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=LIFECYCLE_SYSTEM_ID)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class AnalyticsLifecycle(LifecycleAwareMixin):
    """
    Primary public API for analytics session lifecycle management.

    Usage::

        lc = AnalyticsLifecycle()
        lc.start()

        session = lc.create(
            execution_session_id = "exec-001",
            analytics_scope      = AnalyticsScope.EXECUTION,
        )
        lc.initialize(session.session_id)
        lc.collect(session.session_id)
        lc.analyze(session.session_id)
        lc.ready(session.session_id)
        lc.activate(session.session_id)
        lc.complete(session.session_id)
        lc.archive(session.session_id)

        lc.stop()

    Pause / resume::

        lc.pause(session.session_id)
        lc.resume(session.session_id)
        lc.collect(session.session_id)   # resume into collecting
    """

    def __init__(
        self,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
        max_history:  int = DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._registry  = AnalyticsRegistry(max_sessions=max_sessions)
        self._factory   = AnalyticsFactory()
        self._validator = AnalyticsValidator()
        self._stats     = AnalyticsStatistics()
        self._history   = AnalyticsHistory(
            max_sessions    = max_history,
            max_transitions = max_history * 10,
            max_events      = max_history * 10,
        )
        self._listeners:     List[Callable[[AnalyticsEvent], None]] = []
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
            "AnalyticsLifecycle started.",
            system_id = LIFECYCLE_SYSTEM_ID,
            version   = VERSION,
        )

    def _on_stop(self) -> None:
        self._registry.stop()
        self._factory.stop()
        _audit.log_lifecycle_event(
            LIFECYCLE_SYSTEM_ID,
            EngineState.RUNNING,
            EngineState.STOPPED,
            VERSION,
        )
        _log.info(
            "AnalyticsLifecycle stopped.",
            system_id = LIFECYCLE_SYSTEM_ID,
        )

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise AnalyticsNotRunningError()

    # ── Session creation ──────────────────────────────────────────────────────

    def create(
        self,
        execution_session_id: str,
        *,
        analytics_scope:    AnalyticsScope   = AnalyticsScope.EXECUTION,
        analytics_mode:     AnalyticsMode    = AnalyticsMode.ON_DEMAND,
        analytics_trigger:  AnalyticsTrigger = AnalyticsTrigger.AUTOMATIC,
        analytics_reason:   str              = "",
        workflow_id:        str              = "",
        portfolio_id:       str              = "",
        strategy_id:        str              = "",
        analytics_version:  int              = 1,
        actor:              str              = ACTOR_LIFECYCLE,
    ) -> AnalyticsSession:
        """
        Create a new analytics session and register it.

        The session starts in CREATED state.
        """
        self._assert_running()
        session = self._factory.create_from_params(
            execution_session_id = execution_session_id,
            analytics_scope      = analytics_scope,
            analytics_mode       = analytics_mode,
            analytics_trigger    = analytics_trigger,
            analytics_reason     = analytics_reason,
            workflow_id          = workflow_id,
            portfolio_id         = portfolio_id,
            strategy_id          = strategy_id,
            analytics_version    = analytics_version,
        )
        self._registry.store(session)
        self._stats.record_created()
        event = make_analytics_created(session.session_id, actor=actor)
        self._history.record_event(event)
        self._dispatch(event)
        _log.info(
            "Analytics session created.",
            session_id           = session.session_id,
            execution_session_id = execution_session_id,
        )
        return session

    def create_from_context(
        self,
        context: AnalyticsContext,
        *,
        actor: str = ACTOR_LIFECYCLE,
    ) -> AnalyticsSession:
        """
        Create a new analytics session from an AnalyticsContext.

        Validates context before creation.
        """
        self._assert_running()
        result = self._validator.validate_context(context)
        if not result.is_valid:
            raise AnalyticsValidationError(
                "Context validation failed.",
                errors=result.errors,
            )
        session = self._factory.create(context)
        self._registry.store(session)
        self._stats.record_created()
        event = make_analytics_created(session.session_id, actor=actor)
        self._history.record_event(event)
        self._dispatch(event)
        return session

    # ── State transition methods ───────────────────────────────────────────────

    def initialize(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> None:
        """Transition: CREATED → INITIALIZING."""
        self._transition(
            session_id,
            AnalyticsState.INITIALIZING,
            actor=actor, reason=reason,
        )

    def collect(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> None:
        """Transition: INITIALIZING / ANALYZING / RESUMING → COLLECTING."""
        self._transition(
            session_id,
            AnalyticsState.COLLECTING,
            actor=actor, reason=reason,
        )

    def analyze(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> None:
        """Transition: COLLECTING / ACTIVE / RESUMING → ANALYZING."""
        self._transition(
            session_id,
            AnalyticsState.ANALYZING,
            actor=actor, reason=reason,
        )

    def ready(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> None:
        """Transition: ANALYZING / RESUMING → READY."""
        self._transition(
            session_id,
            AnalyticsState.READY,
            actor=actor, reason=reason,
        )

    def activate(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> None:
        """Transition: READY / RESUMING → ACTIVE."""
        self._transition(
            session_id,
            AnalyticsState.ACTIVE,
            actor=actor, reason=reason,
        )

    def pause(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> None:
        """Transition: any active state → PAUSED."""
        self._transition(
            session_id,
            AnalyticsState.PAUSED,
            actor=actor, reason=reason,
        )

    def resume(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> None:
        """Transition: PAUSED → RESUMING."""
        self._transition(
            session_id,
            AnalyticsState.RESUMING,
            actor=actor, reason=reason,
        )

    def complete(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> None:
        """Transition: ACTIVE → COMPLETED."""
        self._transition(
            session_id,
            AnalyticsState.COMPLETED,
            actor=actor, reason=reason,
        )
        session = self._registry.get(session_id)
        self._stats.record_completed(
            duration_seconds=session.duration_seconds or 0.0
        )
        self._history.record_session(session)

    def fail(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> None:
        """Transition: any non-terminal state → FAILED."""
        session = self._registry.get(session_id)
        if reason:
            session.set_failure_reason(reason)
        self._transition(
            session_id,
            AnalyticsState.FAILED,
            actor=actor, reason=reason,
        )
        self._stats.record_failed()
        self._history.record_session(session)

    def archive(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> None:
        """Transition: COMPLETED / FAILED → ARCHIVED, then move to archive store."""
        self._transition(
            session_id,
            AnalyticsState.ARCHIVED,
            actor=actor, reason=reason,
        )
        self._registry.archive(session_id)
        self._stats.record_archived()
        event = make_analytics_archived(session_id, actor=actor, reason=reason)
        self._history.record_event(event)
        self._dispatch(event)

    # ── Query ─────────────────────────────────────────────────────────────────

    def get(self, session_id: str) -> AnalyticsSession:
        """Return active session or raise AnalyticsSessionNotFoundError."""
        self._assert_running()
        return self._registry.get(session_id)

    def find(self, session_id: str) -> Optional[AnalyticsSession]:
        """Return active session or None."""
        self._assert_running()
        return self._registry.find(session_id)

    def find_archived(self, session_id: str) -> Optional[AnalyticsSession]:
        """Return archived session or None."""
        self._assert_running()
        return self._registry.find_archived(session_id)

    def all_active(self) -> List[AnalyticsSession]:
        self._assert_running()
        return self._registry.all()

    def by_state(self, state: AnalyticsState) -> List[AnalyticsSession]:
        self._assert_running()
        return self._registry.by_state(state)

    def by_execution_session(
        self, execution_session_id: str
    ) -> List[AnalyticsSession]:
        self._assert_running()
        return self._registry.by_execution_session(execution_session_id)

    # ── Statistics / history ──────────────────────────────────────────────────

    def statistics(self) -> AnalyticsStatistics:
        """Return an independent copy of current statistics."""
        return self._stats.copy()

    def history(self) -> AnalyticsHistory:
        """Return the live history store."""
        return self._history

    # ── Event listener registration ───────────────────────────────────────────

    def add_listener(
        self, listener: Callable[[AnalyticsEvent], None]
    ) -> None:
        """Register a synchronous event listener."""
        with self._listeners_lock:
            self._listeners.append(listener)

    def remove_listener(
        self, listener: Callable[[AnalyticsEvent], None]
    ) -> None:
        with self._listeners_lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

    # ── Internal ─────────────────────────────────────────────────────────────

    def _transition(
        self,
        session_id:   str,
        target_state: AnalyticsState,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> None:
        self._assert_running()
        session = self._registry.get(session_id)
        transition = session.transition_to(
            target_state, actor=actor, reason=reason
        )
        self._stats.record_transition()
        self._history.record_transition(transition)

        factory = _STATE_EVENT_FACTORY.get(target_state)
        if factory:
            event = factory(session_id, actor=actor, reason=reason)  # type: ignore[call-arg]
            self._history.record_event(event)
            self._dispatch(event)

    def _dispatch(self, event: AnalyticsEvent) -> None:
        with self._listeners_lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:
                _log.warning(
                    "AnalyticsLifecycle listener raised.",
                    error=str(exc),
                )
