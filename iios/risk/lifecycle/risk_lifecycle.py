"""
risk_lifecycle.py — iios.risk.lifecycle
==========================================
Primary public interface of the Risk Lifecycle subsystem.

:class:`RiskLifecycle` is the ONLY interface external callers use to
manage risk session lifecycle.

Responsibilities
----------------
* Session creation
* State-transition orchestration (initialize → collect → validate → ready →
  assess → monitor → pause → resume → complete → fail → archive)
* Event dispatch to registered listeners
* History and statistics accumulation
* Structural integrity validation

Non-Responsibilities (intentional exclusions)
---------------------------------------------
* Risk calculations
* Policy evaluation
* Portfolio optimisation
* Execution routing

C11 Risk Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.errors.exceptions import IIOSError
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import (
    ACTOR_LIFECYCLE,
    DEFAULT_MAX_ARCHIVED,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_MAX_TRANSITIONS,
    LIFECYCLE_SYSTEM_ID,
    VERSION,
    RiskPriority,
    RiskScope,
    RiskState,
    RiskType,
)
from .exceptions import (
    RiskLifecycleError,
    RiskLifecycleNotRunningError,
    RiskSessionNotFoundError,
    RiskValidationError,
)
from .risk_events import (
    RiskEvent,
    make_risk_archived,
    make_risk_assessment_started,
    make_risk_collected,
    make_risk_completed,
    make_risk_created,
    make_risk_failed,
    make_risk_initialized,
    make_risk_monitoring_started,
    make_risk_paused,
    make_risk_resumed,
    make_risk_validated,
)
from .risk_factory import RiskFactory
from .risk_history import RiskHistory
from .risk_registry import RiskRegistry
from .risk_session import RiskSession
from .risk_statistics import RiskStatistics
from .risk_validation import RiskValidationResult, RiskValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=LIFECYCLE_SYSTEM_ID)


class RiskLifecycle(LifecycleAwareMixin):
    """
    Institutional risk lifecycle engine.

    This is the ONLY public interface external callers should use.

    Parameters
    ----------
    max_active_sessions :   Maximum concurrent in-flight sessions.
    max_archived_sessions : Maximum archived sessions kept in memory.
    max_history :           Maximum lifecycle events retained.
    max_transitions :       Maximum transition records retained.

    Examples
    --------
    ::

        lc = RiskLifecycle()
        lc.start()
        session = lc.create("risk-001", "pf-001")
        lc.initialize(session.session_id)
        lc.collect(session.session_id)
        lc.validate_session(session.session_id)
        lc.mark_ready(session.session_id)
        lc.start_assessment(session.session_id)
        lc.start_monitoring(session.session_id)
        lc.complete(session.session_id)
        lc.archive(session.session_id)
        lc.stop()
    """

    def __init__(
        self,
        max_active_sessions:   int = DEFAULT_MAX_SESSIONS,
        max_archived_sessions: int = DEFAULT_MAX_ARCHIVED,
        max_history:           int = DEFAULT_MAX_HISTORY,
        max_transitions:       int = DEFAULT_MAX_TRANSITIONS,
    ) -> None:
        super().__init__()
        self._factory   = RiskFactory()
        self._registry  = RiskRegistry(
            max_active_sessions   = max_active_sessions,
            max_archived_sessions = max_archived_sessions,
        )
        self._history   = RiskHistory(
            max_events      = max_history,
            max_transitions = max_transitions,
        )
        self._stats      = RiskStatistics()
        self._validator  = RiskValidator()
        self._listeners: List[Callable[[RiskEvent], None]] = []
        self._listener_lock = threading.Lock()

    # ==================================================================
    # LifecycleAwareMixin hooks
    # ==================================================================

    def _on_start(self) -> None:
        _log.info(
            "RiskLifecycle starting",
            extra={"system_id": LIFECYCLE_SYSTEM_ID, "version": VERSION},
        )
        _audit.log_lifecycle_event(
            engine_id  = LIFECYCLE_SYSTEM_ID,
            from_state = "STOPPED",
            to_state   = "RUNNING",
            version    = VERSION,
            actor      = ACTOR_LIFECYCLE,
        )

    def _on_stop(self) -> None:
        _log.info(
            "RiskLifecycle stopping",
            extra={"system_id": LIFECYCLE_SYSTEM_ID, "version": VERSION},
        )
        _audit.log_lifecycle_event(
            engine_id  = LIFECYCLE_SYSTEM_ID,
            from_state = "RUNNING",
            to_state   = "STOPPED",
            version    = VERSION,
            actor      = ACTOR_LIFECYCLE,
        )

    # ==================================================================
    # Session creation
    # ==================================================================

    def create(
        self,
        risk_id:      str,
        portfolio_id: str,
        *,
        session_id:    Optional[str]          = None,
        assessment_id: str                    = "",
        workflow_id:   str                    = "",
        strategy_id:   str                    = "",
        risk_scope:    RiskScope              = RiskScope.PORTFOLIO,
        risk_type:     RiskType               = RiskType.CUSTOM,
        risk_priority: RiskPriority           = RiskPriority.MEDIUM,
        risk_version:  int                    = 1,
        metadata:      Optional[Dict[str, Any]] = None,
        actor:         str                    = ACTOR_LIFECYCLE,
    ) -> RiskSession:
        """
        Create a new risk session in CREATED state.

        Parameters
        ----------
        risk_id :       Risk assessment identifier.
        portfolio_id :  Portfolio being assessed.
        session_id :    Optional explicit session ID.
        assessment_id : Assessment correlation identifier.
        workflow_id :   Workflow routing context.
        strategy_id :   Strategy being assessed.
        risk_scope :    Scope of the risk assessment.
        risk_type :     Type of risk being assessed.
        risk_priority : Priority level.
        risk_version :  Initial version counter.
        metadata :      Supplementary metadata.
        actor :         Requesting actor identifier.

        Returns
        -------
        RiskSession
        """
        self._assert_running()
        session = self._factory.create(
            risk_id,
            portfolio_id,
            session_id    = session_id,
            assessment_id = assessment_id,
            workflow_id   = workflow_id,
            strategy_id   = strategy_id,
            risk_scope    = risk_scope,
            risk_type     = risk_type,
            risk_priority = risk_priority,
            risk_version  = risk_version,
            metadata      = metadata,
        )
        self._registry.add(session)
        self._stats.record_session_created()
        event = make_risk_created(
            session.session_id, session.risk_id, session.portfolio_id,
            payload={"actor": actor},
        )
        self._history.record_event(event)
        self._dispatch(event)
        _log.debug(f"Risk session created: {session.session_id} → {risk_id}/{portfolio_id}")
        return session

    # ==================================================================
    # State-transition methods
    # ==================================================================

    def initialize(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RiskSession:
        """Transition a CREATED session to INITIALIZING."""
        return self._transition(
            session_id, RiskState.INITIALIZING,
            actor=actor, reason=reason,
            event_fn=make_risk_initialized,
        )

    def collect(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RiskSession:
        """Transition an INITIALIZING (or VALIDATING) session to COLLECTING."""
        return self._transition(
            session_id, RiskState.COLLECTING,
            actor=actor, reason=reason,
            event_fn=make_risk_collected,
        )

    def validate_session(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RiskSession:
        """Transition a COLLECTING session to VALIDATING."""
        return self._transition(
            session_id, RiskState.VALIDATING,
            actor=actor, reason=reason,
            event_fn=make_risk_validated,
        )

    def mark_ready(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RiskSession:
        """Transition a VALIDATING session to READY."""
        return self._transition(
            session_id, RiskState.READY,
            actor=actor, reason=reason,
            event_fn=None,   # no distinct READY event — use VALIDATED
        )

    def start_assessment(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RiskSession:
        """Transition a READY (or RESUMING/MONITORING) session to ASSESSING."""
        return self._transition(
            session_id, RiskState.ASSESSING,
            actor=actor, reason=reason,
            event_fn=make_risk_assessment_started,
        )

    def start_monitoring(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RiskSession:
        """Transition an ASSESSING (or RESUMING) session to MONITORING."""
        return self._transition(
            session_id, RiskState.MONITORING,
            actor=actor, reason=reason,
            event_fn=make_risk_monitoring_started,
        )

    def pause(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RiskSession:
        """Transition an active session to PAUSED."""
        return self._transition(
            session_id, RiskState.PAUSED,
            actor=actor, reason=reason,
            event_fn=make_risk_paused,
        )

    def resume(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RiskSession:
        """Transition a PAUSED session to RESUMING."""
        return self._transition(
            session_id, RiskState.RESUMING,
            actor=actor, reason=reason,
            event_fn=make_risk_resumed,
        )

    def complete(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RiskSession:
        """Transition an ASSESSING or MONITORING session to COMPLETED."""
        session = self._transition(
            session_id, RiskState.COMPLETED,
            actor=actor, reason=reason,
            event_fn=make_risk_completed,
        )
        duration = session.duration_s
        self._stats.record_session_completed(duration_s=duration)
        return session

    def fail(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RiskSession:
        """Transition any non-immutable session to FAILED."""
        session = self._transition(
            session_id, RiskState.FAILED,
            actor=actor, reason=reason,
            event_fn=make_risk_failed,
        )
        self._stats.record_session_failed()
        return session

    def archive(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> RiskSession:
        """
        Transition a COMPLETED or FAILED session to ARCHIVED and move it
        to the archived registry.
        """
        session = self._transition(
            session_id, RiskState.ARCHIVED,
            actor=actor, reason=reason,
            event_fn=make_risk_archived,
        )
        self._registry.archive(session_id)
        self._stats.record_session_archived()
        return session

    # ==================================================================
    # Validation
    # ==================================================================

    def validate(self, session_id: str) -> RiskValidationResult:
        """
        Validate the structural integrity of a session.

        Parameters
        ----------
        session_id : Session to validate.

        Returns
        -------
        RiskValidationResult
        """
        self._assert_running()
        session = self._registry.get(session_id)
        return self._validator.validate(session)

    # ==================================================================
    # Read-only queries
    # ==================================================================

    def get(self, session_id: str) -> RiskSession:
        """Return a session by ID (active or archived)."""
        return self._registry.get(session_id)

    def find(self, session_id: str) -> Optional[RiskSession]:
        """Return a session by ID or None."""
        return self._registry.find(session_id)

    def active_sessions(self) -> List[RiskSession]:
        """Return all currently active sessions."""
        return self._registry.active_sessions()

    def archived_sessions(self) -> List[RiskSession]:
        """Return all archived sessions."""
        return self._registry.archived_sessions()

    def sessions_for_portfolio(self, portfolio_id: str) -> List[RiskSession]:
        """Return all sessions for a portfolio_id."""
        return self._registry.sessions_for_portfolio(portfolio_id)

    def sessions_by_state(self, state: RiskState) -> List[RiskSession]:
        """Return all active sessions in a given state."""
        return self._registry.sessions_by_state(state)

    def history(self) -> RiskHistory:
        """Return the lifecycle history object."""
        return self._history

    def statistics(self) -> Dict[str, Any]:
        """Return a statistics snapshot."""
        return self._stats.snapshot()

    # ==================================================================
    # Event listeners
    # ==================================================================

    def add_listener(self, fn: Callable[[RiskEvent], None]) -> None:
        """Register a lifecycle event listener."""
        with self._listener_lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable[[RiskEvent], None]) -> None:
        """Unregister a lifecycle event listener."""
        with self._listener_lock:
            self._listeners = [l for l in self._listeners if l is not fn]

    # ==================================================================
    # Guard
    # ==================================================================

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise RiskLifecycleNotRunningError()

    # ==================================================================
    # Internal helpers
    # ==================================================================

    def _transition(
        self,
        session_id: str,
        to_state:   RiskState,
        *,
        actor:    str,
        reason:   str,
        event_fn: Optional[Callable],
    ) -> RiskSession:
        """Shared transition implementation."""
        self._assert_running()
        session = self._registry.get_active(session_id)
        session.transition_to(to_state, actor=actor, reason=reason)
        self._stats.record_transition()
        if session.transitions:
            self._history.record_transition(session.transitions[-1])
        if event_fn is not None:
            event = event_fn(
                session.session_id, session.risk_id, session.portfolio_id,
                payload={"actor": actor, "reason": reason},
            )
            self._history.record_event(event)
            self._dispatch(event)
        return session

    def _dispatch(self, event: RiskEvent) -> None:
        with self._listener_lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception:
                pass
