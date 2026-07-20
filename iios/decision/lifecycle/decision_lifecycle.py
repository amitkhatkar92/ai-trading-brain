"""
decision_lifecycle.py — iios.decision.lifecycle
================================================
PRIMARY PUBLIC INTERFACE for the Institutional Decision Lifecycle subsystem.

:class:`DecisionLifecycle` manages the complete lifecycle of institutional
decision sessions.  It is the sole entry point for all lifecycle operations.

This module is responsible for:
  * Creating decision sessions
  * Managing state transitions
  * Tracking decision state
  * Maintaining lifecycle history
  * Publishing lifecycle events
  * Validating transitions

It performs NO policy evaluation, NO optimization, NO execution, and
NO broker communication.

C9 Decision Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger

from .constants import (
    ACTOR_LIFECYCLE,
    ACTOR_SYSTEM,
    LIFECYCLE_SYSTEM_ID,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_MAX_ARCHIVED,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_TRANSITIONS,
    VERSION,
    ACTIVE_STATES,
    TERMINAL_STATES,
    DecisionEventType,
    DecisionPriority,
    DecisionScope,
    DecisionState,
    DecisionTrigger,
    DecisionType,
)
from .decision_session import DecisionSession
from .decision_registry import DecisionRegistry
from .decision_factory import DecisionFactory
from .decision_history import DecisionHistory
from .decision_statistics import DecisionStatistics
from .decision_validation import DecisionValidator, DecisionValidationResult
from .decision_events import (
    DecisionEvent,
    make_decision_created,
    make_decision_initialized,
    make_decision_started,
    make_decision_paused,
    make_decision_resumed,
    make_decision_completed,
    make_decision_failed,
    make_decision_archived,
)
from .exceptions import (
    DecisionLifecycleNotRunningError,
    DecisionSessionNotFoundError,
    DecisionInvalidTransitionError,
)

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=LIFECYCLE_SYSTEM_ID)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class DecisionLifecycle(LifecycleAwareMixin):
    """
    Primary public interface for institutional decision session lifecycle.

    Usage
    -----
    ::

        lc = DecisionLifecycle()
        lc.start()

        session = lc.create("decision-001")

        lc.initialize(session.session_id)
        lc.collect(session.session_id)
        lc.evaluate(session.session_id)
        lc.ready(session.session_id)
        lc.activate(session.session_id)
        lc.complete(session.session_id)
        lc.archive(session.session_id)

        lc.stop()

    Pause / resume::

        lc.pause(session.session_id)
        lc.resume(session.session_id)    # → RESUMING
        lc.collect(session.session_id)   # back to collecting

    Failure::

        lc.fail(session.session_id, reason="market closed")
        lc.archive(session.session_id)

    Parameters
    ----------
    max_active_sessions :   Maximum simultaneous in-flight sessions.
    max_archived_sessions : Maximum archived sessions retained in memory.
    max_history :           Maximum lifecycle events retained.
    max_transitions :       Maximum transitions retained in history.
    """

    def __init__(
        self,
        max_active_sessions:   int = DEFAULT_MAX_SESSIONS,
        max_archived_sessions: int = DEFAULT_MAX_ARCHIVED,
        max_history:           int = DEFAULT_MAX_HISTORY,
        max_transitions:       int = DEFAULT_MAX_TRANSITIONS,
    ) -> None:
        super().__init__()
        self._lock = threading.RLock()

        self._registry  = DecisionRegistry(
            max_active_sessions   = max_active_sessions,
            max_archived_sessions = max_archived_sessions,
        )
        self._factory   = DecisionFactory()
        self._history   = DecisionHistory(
            max_events      = max_history,
            max_transitions = max_transitions,
        )
        self._statistics = DecisionStatistics()
        self._validator  = DecisionValidator()

        self._listeners: List[Callable[[DecisionEvent], None]] = []

    # ==================================================================
    # LifecycleAwareMixin hooks
    # ==================================================================

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            engine_id  = LIFECYCLE_SYSTEM_ID,
            from_state = "stopped",
            to_state   = "running",
            version    = VERSION,
            actor      = ACTOR_SYSTEM,
        )
        _log.info("DecisionLifecycle: started")

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            engine_id  = LIFECYCLE_SYSTEM_ID,
            from_state = "running",
            to_state   = "stopped",
            version    = VERSION,
            actor      = ACTOR_SYSTEM,
        )
        _log.info("DecisionLifecycle: stopped")

    # ==================================================================
    # Session creation
    # ==================================================================

    def create(
        self,
        decision_id: str,
        *,
        session_id:        Optional[str]          = None,
        workflow_id:       str                    = "",
        portfolio_id:      str                    = "",
        strategy_id:       str                    = "",
        decision_scope:    DecisionScope           = DecisionScope.ORDER,
        decision_type:     DecisionType            = DecisionType.ORDER,
        decision_priority: DecisionPriority        = DecisionPriority.MEDIUM,
        decision_trigger:  DecisionTrigger         = DecisionTrigger.AUTOMATIC,
        decision_reason:   str                    = "",
        metadata:          Optional[Dict[str, Any]] = None,
        actor:             str                    = ACTOR_LIFECYCLE,
    ) -> DecisionSession:
        """
        Create a new decision session in CREATED state and register it.

        Parameters
        ----------
        decision_id :        Caller-supplied identifier for the decision.
        session_id :         Optional explicit session ID; UUID auto-generated
                             if omitted.
        workflow_id :        Workflow routing context.
        portfolio_id :       Portfolio routing context.
        strategy_id :        Strategy routing context.
        decision_scope :     Scope of the decision.
        decision_type :      Type of the decision.
        decision_priority :  Scheduling priority.
        decision_trigger :   What triggered the decision.
        decision_reason :    Human-readable purpose.
        metadata :           Supplementary session metadata.
        actor :              Actor identifier for audit purposes.

        Returns
        -------
        DecisionSession
            A new session in CREATED state.

        Raises
        ------
        DecisionLifecycleNotRunningError
            When the lifecycle has not been started.
        """
        self._assert_running()

        session = self._factory.create(
            decision_id,
            session_id        = session_id,
            workflow_id       = workflow_id,
            portfolio_id      = portfolio_id,
            strategy_id       = strategy_id,
            decision_scope    = decision_scope,
            decision_type     = decision_type,
            decision_priority = decision_priority,
            decision_trigger  = decision_trigger,
            decision_reason   = decision_reason,
            metadata          = metadata,
        )

        with self._lock:
            self._registry.add(session)
            self._statistics.record_session_created()

        event = make_decision_created(
            session.session_id, session.decision_id, payload={"actor": actor}
        )
        self._dispatch(event)
        _log.debug(
            f"DecisionLifecycle: created session {session.session_id} "
            f"for decision {decision_id!r}"
        )
        return session

    # ==================================================================
    # State transition methods
    # ==================================================================

    def initialize(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> DecisionSession:
        """Advance session from CREATED → INITIALIZING."""
        return self._transition(
            session_id, DecisionState.INITIALIZING,
            actor=actor, reason=reason,
            event_fn=make_decision_initialized,
        )

    def collect(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> DecisionSession:
        """Advance session to COLLECTING state."""
        return self._transition(
            session_id, DecisionState.COLLECTING,
            actor=actor, reason=reason,
        )

    def evaluate(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> DecisionSession:
        """Advance session to EVALUATING state."""
        return self._transition(
            session_id, DecisionState.EVALUATING,
            actor=actor, reason=reason,
        )

    def ready(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> DecisionSession:
        """Advance session to READY state."""
        return self._transition(
            session_id, DecisionState.READY,
            actor=actor, reason=reason,
        )

    def activate(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> DecisionSession:
        """Advance session from READY → ACTIVE."""
        return self._transition(
            session_id, DecisionState.ACTIVE,
            actor=actor, reason=reason,
            event_fn=make_decision_started,
        )

    def pause(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> DecisionSession:
        """Pause an in-flight session (→ PAUSED)."""
        return self._transition(
            session_id, DecisionState.PAUSED,
            actor=actor, reason=reason,
            event_fn=lambda sid, did, **kw: make_decision_paused(sid, did, reason=reason, **kw),
        )

    def resume(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> DecisionSession:
        """Resume a paused session (→ RESUMING)."""
        return self._transition(
            session_id, DecisionState.RESUMING,
            actor=actor, reason=reason,
            event_fn=lambda sid, did, **kw: make_decision_resumed(
                sid, did, resumed_to=DecisionState.RESUMING, **kw
            ),
        )

    def complete(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> DecisionSession:
        """Complete an ACTIVE session (→ COMPLETED)."""
        session = self._transition(
            session_id, DecisionState.COMPLETED,
            actor=actor, reason=reason,
            event_fn=lambda sid, did, **kw: make_decision_completed(
                sid, did,
                duration_s=self._registry.find_any(sid).duration_s,
                **kw,
            ),
        )
        dur = session.duration_s or 0.0
        self._statistics.record_session_completed(dur)
        # Move to archive
        with self._lock:
            self._registry.move_to_archive(session_id)
        return session

    def fail(
        self,
        session_id: str,
        *,
        reason: str = "",
        actor:  str = ACTOR_LIFECYCLE,
    ) -> DecisionSession:
        """
        Transition any non-terminal session to FAILED.

        Parameters
        ----------
        session_id : Session to fail.
        reason :     Human-readable failure reason (recommended).
        actor :      Actor identifier.
        """
        session = self._transition(
            session_id, DecisionState.FAILED,
            actor=actor, reason=reason,
            event_fn=lambda sid, did, **kw: make_decision_failed(
                sid, did, reason=reason, **kw
            ),
        )
        self._statistics.record_session_failed()
        with self._lock:
            self._registry.move_to_archive(session_id)
        return session

    def archive(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> DecisionSession:
        """Archive a terminal (COMPLETED or FAILED) session."""
        session = self._transition(
            session_id, DecisionState.ARCHIVED,
            actor=actor, reason=reason,
            event_fn=make_decision_archived,
        )
        self._statistics.record_session_archived()
        # Ensure the session is in the archive (may already be there)
        with self._lock:
            self._registry.move_to_archive(session_id)
        return session

    # ==================================================================
    # Query methods
    # ==================================================================

    def get(self, session_id: str) -> DecisionSession:
        """
        Return the session for *session_id* (active only).

        Raises
        ------
        DecisionLifecycleNotRunningError
        DecisionSessionNotFoundError
        """
        self._assert_running()
        session = self._registry.find_any(session_id)
        if session is None:
            raise DecisionSessionNotFoundError(session_id)
        return session

    def find(self, session_id: str) -> Optional[DecisionSession]:
        """Return the active session for *session_id*, or ``None``."""
        self._assert_running()
        return self._registry.find_any(session_id)

    def find_archived(self, session_id: str) -> Optional[DecisionSession]:
        """Search the archived store for *session_id*."""
        self._assert_running()
        return self._registry.find_archived(session_id)

    def all_active(self) -> List[DecisionSession]:
        """Return all currently active (in-flight) sessions."""
        self._assert_running()
        return self._registry.all_active()

    def by_state(self, state: DecisionState) -> List[DecisionSession]:
        """Return all active sessions in the given *state*."""
        self._assert_running()
        return self._registry.by_state(state)

    def by_decision(self, decision_id: str) -> List[DecisionSession]:
        """Return all active sessions for *decision_id*."""
        self._assert_running()
        return self._registry.by_decision(decision_id)

    # ==================================================================
    # Observability
    # ==================================================================

    def statistics(self) -> DecisionStatistics:
        """Return the shared :class:`DecisionStatistics` instance."""
        return self._statistics

    def history(self) -> DecisionHistory:
        """Return the :class:`DecisionHistory` instance."""
        return self._history

    def validate(self, session_id: str) -> DecisionValidationResult:
        """
        Run all five validation checks on the session identified by
        *session_id*.

        Returns :class:`DecisionValidationResult`.

        Raises
        ------
        DecisionSessionNotFoundError
        """
        self._assert_running()
        session = self._registry.find_any(session_id)
        if session is None:
            raise DecisionSessionNotFoundError(session_id)
        return self._validator.validate(session)

    # ==================================================================
    # Event listener API
    # ==================================================================

    def add_listener(self, listener: Callable[[DecisionEvent], None]) -> None:
        """
        Register a synchronous event listener.

        The listener is called from within the transition lock; it must
        not call back into :class:`DecisionLifecycle`.
        """
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[DecisionEvent], None]) -> None:
        """Deregister an event listener."""
        with self._lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

    # ==================================================================
    # Internal helpers
    # ==================================================================

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise DecisionLifecycleNotRunningError("DecisionLifecycle")

    def _transition(
        self,
        session_id: str,
        to_state:   DecisionState,
        *,
        actor:    str = ACTOR_LIFECYCLE,
        reason:   str = "",
        metadata: Optional[Dict[str, Any]] = None,
        event_fn: Optional[Any] = None,
    ) -> DecisionSession:
        """
        Shared transition executor used by all public transition methods.

        Looks up the session (active first, then archived for ARCHIVED
        transitions), executes the transition, records it in history,
        updates statistics, dispatches an event.
        """
        self._assert_running()

        with self._lock:
            # Look up session — archived transitions need the archived store
            session = self._registry.find(session_id)
            if session is None:
                # Might be in archive (e.g. archiving a completed session)
                session = self._registry.find_archived(session_id)
            if session is None:
                raise DecisionSessionNotFoundError(session_id)

            # Execute the transition (raises on invalid)
            session.transition_to(
                to_state,
                actor    = actor,
                reason   = reason,
                metadata = metadata,
            )

            # Record the transition in history
            if session.transitions:
                self._history.record_transition(session.transitions[-1])

            self._statistics.record_transition()

        # Build and dispatch the event
        if event_fn is not None:
            try:
                event = event_fn(session.session_id, session.decision_id)
            except Exception:
                event = None
        else:
            event = None

        if event is not None:
            self._dispatch(event)

        _log.debug(
            f"DecisionLifecycle: session {session_id} → {to_state.value}"
        )
        return session

    def _dispatch(self, event: DecisionEvent) -> None:
        """Record the event in history and call all registered listeners."""
        self._history.record_event(event)
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:
                _log.warning(
                    f"DecisionLifecycle: listener error for "
                    f"{event.event_type.value}: {exc}"
                )

    def __repr__(self) -> str:
        state = self.lifecycle_state()
        state_str = state.value if hasattr(state, "value") else str(state)
        return (
            f"DecisionLifecycle("
            f"state={state_str!r}, "
            f"active_sessions={self._registry.active_count()}, "
            f"version={VERSION!r})"
        )
