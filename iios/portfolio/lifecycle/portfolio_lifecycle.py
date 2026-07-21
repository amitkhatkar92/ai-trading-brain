"""
portfolio_lifecycle.py — iios.portfolio.lifecycle
==================================================
Primary public interface of the Portfolio Lifecycle subsystem.

:class:`PortfolioLifecycle` is the ONLY interface external callers use to
manage portfolio session lifecycle.

Responsibilities
----------------
* Session creation
* State-transition orchestration (initialize → load → validate → activate
  → rebalance → pause → resume → complete → fail → archive)
* Event dispatch to registered listeners
* History and statistics accumulation
* Structural integrity validation

Non-Responsibilities (intentional exclusions)
---------------------------------------------
* Portfolio optimisation
* Capital allocation
* Rebalancing calculation
* Execution routing

C10 Portfolio Intelligence — Phase 1, Module 1
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
    PortfolioObjective,
    PortfolioScope,
    PortfolioState,
    PortfolioStatus,
    PortfolioType,
)
from .exceptions import (
    PortfolioLifecycleError,
    PortfolioLifecycleNotRunningError,
    PortfolioSessionNotFoundError,
    PortfolioValidationError,
)
from .portfolio_events import (
    PortfolioEvent,
    make_portfolio_activated,
    make_portfolio_archived,
    make_portfolio_completed,
    make_portfolio_created,
    make_portfolio_failed,
    make_portfolio_initialized,
    make_portfolio_loaded,
    make_portfolio_paused,
    make_portfolio_rebalancing,
    make_portfolio_resumed,
    make_portfolio_validated,
)
from .portfolio_factory import PortfolioFactory
from .portfolio_history import PortfolioHistory
from .portfolio_registry import PortfolioRegistry
from .portfolio_session import PortfolioSession
from .portfolio_statistics import PortfolioStatistics
from .portfolio_validation import PortfolioValidationResult, PortfolioValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=LIFECYCLE_SYSTEM_ID)


class PortfolioLifecycle(LifecycleAwareMixin):
    """
    Institutional portfolio lifecycle engine.

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

        lc = PortfolioLifecycle()
        lc.start()
        session = lc.create("pf-001", portfolio_name="Growth Fund")
        lc.initialize(session.session_id)
        lc.load(session.session_id)
        lc.validate_session(session.session_id)
        lc.activate(session.session_id)
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
        self._factory   = PortfolioFactory()
        self._registry  = PortfolioRegistry(
            max_active_sessions   = max_active_sessions,
            max_archived_sessions = max_archived_sessions,
        )
        self._history    = PortfolioHistory(
            max_events      = max_history,
            max_transitions = max_transitions,
        )
        self._stats      = PortfolioStatistics()
        self._validator  = PortfolioValidator()
        self._listeners: List[Callable[[PortfolioEvent], None]] = []
        self._listener_lock = threading.Lock()

    # ==================================================================
    # LifecycleAwareMixin hooks
    # ==================================================================

    def _on_start(self) -> None:
        _log.info(
            "PortfolioLifecycle starting",
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
            "PortfolioLifecycle stopping",
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
        portfolio_id: str,
        *,
        session_id:           Optional[str]          = None,
        portfolio_name:       str                    = "",
        portfolio_type:       PortfolioType           = PortfolioType.CUSTOM,
        portfolio_scope:      PortfolioScope          = PortfolioScope.INSTITUTIONAL,
        portfolio_objective:  PortfolioObjective      = PortfolioObjective.CUSTOM,
        portfolio_currency:   str                    = "INR",
        portfolio_status:     PortfolioStatus         = PortfolioStatus.INACTIVE,
        metadata:             Optional[Dict[str, Any]] = None,
        actor:                str                    = ACTOR_LIFECYCLE,
    ) -> PortfolioSession:
        """
        Create a new portfolio session in CREATED state.

        Parameters
        ----------
        portfolio_id :        Portfolio identifier.
        session_id :          Optional explicit session ID.
        portfolio_name :      Human-readable name.
        portfolio_type :      Asset-composition classification.
        portfolio_scope :     Institutional scope.
        portfolio_objective : Investment objective.
        portfolio_currency :  Base currency (ISO 4217).
        portfolio_status :    Initial operational status.
        metadata :            Supplementary metadata dict.
        actor :               Requesting actor identifier.

        Returns
        -------
        PortfolioSession
        """
        self._assert_running()
        session = self._factory.create(
            portfolio_id,
            session_id           = session_id,
            portfolio_name       = portfolio_name,
            portfolio_type       = portfolio_type,
            portfolio_scope      = portfolio_scope,
            portfolio_objective  = portfolio_objective,
            portfolio_currency   = portfolio_currency,
            portfolio_status     = portfolio_status,
            metadata             = metadata,
        )
        self._registry.add(session)
        self._stats.record_session_created()
        event = make_portfolio_created(
            session.session_id, session.portfolio_id, payload={"actor": actor}
        )
        self._history.record_event(event)
        self._dispatch(event)
        _log.debug(f"Portfolio session created: {session.session_id} → {portfolio_id}")
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
    ) -> PortfolioSession:
        """Transition a CREATED session to INITIALIZING."""
        return self._transition(
            session_id, PortfolioState.INITIALIZING,
            actor=actor, reason=reason,
            event_fn=make_portfolio_initialized,
        )

    def load(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> PortfolioSession:
        """Transition an INITIALIZING or VALIDATING session to LOADING."""
        return self._transition(
            session_id, PortfolioState.LOADING,
            actor=actor, reason=reason,
            event_fn=make_portfolio_loaded,
        )

    def validate_session(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> PortfolioSession:
        """Transition a LOADING session to VALIDATING."""
        return self._transition(
            session_id, PortfolioState.VALIDATING,
            actor=actor, reason=reason,
            event_fn=make_portfolio_validated,
        )

    def activate(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> PortfolioSession:
        """Transition a READY session to ACTIVE."""
        return self._transition(
            session_id, PortfolioState.ACTIVE,
            actor=actor, reason=reason,
            event_fn=make_portfolio_activated,
        )

    def ready(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> PortfolioSession:
        """Transition a VALIDATING or RESUMING session to READY."""
        return self._transition(
            session_id, PortfolioState.READY,
            actor=actor, reason=reason,
            event_fn=None,
        )

    def pause(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> PortfolioSession:
        """Transition a READY/ACTIVE/REBALANCING session to PAUSED."""
        return self._transition(
            session_id, PortfolioState.PAUSED,
            actor=actor, reason=reason,
            event_fn=make_portfolio_paused,
        )

    def resume(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> PortfolioSession:
        """Transition a PAUSED session to RESUMING."""
        return self._transition(
            session_id, PortfolioState.RESUMING,
            actor=actor, reason=reason,
            event_fn=make_portfolio_resumed,
        )

    def rebalance(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> PortfolioSession:
        """Transition an ACTIVE or RESUMING session to REBALANCING."""
        return self._transition(
            session_id, PortfolioState.REBALANCING,
            actor=actor, reason=reason,
            event_fn=make_portfolio_rebalancing,
        )

    def complete(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> PortfolioSession:
        """Transition an ACTIVE or REBALANCING session to COMPLETED."""
        session = self._transition(
            session_id, PortfolioState.COMPLETED,
            actor=actor, reason=reason,
            event_fn=make_portfolio_completed,
        )
        dur = session.duration_s() or 0.0
        self._stats.record_session_completed(duration_s=dur)
        return session

    def fail(
        self,
        session_id: str,
        reason:     str = "",
        *,
        actor:  str = ACTOR_LIFECYCLE,
    ) -> PortfolioSession:
        """Transition any non-terminal session to FAILED."""
        session = self._registry.get_active(session_id)
        session.fail(reason=reason, actor=actor)
        self._stats.record_session_failed()
        self._stats.record_transition()

        transition = session.transitions[-1] if session.transitions else None
        if transition is not None:
            self._history.record_transition(transition)

        event = make_portfolio_failed(
            session_id, session.portfolio_id, reason=reason,
        )
        self._history.record_event(event)
        self._dispatch(event)
        return session

    def archive(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> PortfolioSession:
        """Transition a COMPLETED or FAILED session to ARCHIVED, then archive."""
        session = self._transition(
            session_id, PortfolioState.ARCHIVED,
            actor=actor, reason=reason,
            event_fn=make_portfolio_archived,
        )
        self._registry.archive(session_id)
        self._stats.record_session_archived()
        return session

    # ==================================================================
    # Structural validation
    # ==================================================================

    def validate(self, session_id: str) -> PortfolioValidationResult:
        """
        Run structural integrity validation on a session.

        Returns
        -------
        PortfolioValidationResult
        """
        self._assert_running()
        session = self._registry.get(session_id)
        return self._validator.validate(session)

    # ==================================================================
    # Query methods
    # ==================================================================

    def get_session(self, session_id: str) -> PortfolioSession:
        """
        Return a session by ID.

        Raises
        ------
        PortfolioSessionNotFoundError
        """
        self._assert_running()
        return self._registry.get(session_id)

    def find_session(self, session_id: str) -> Optional[PortfolioSession]:
        """Return a session by ID, or None if not found."""
        self._assert_running()
        return self._registry.find(session_id)

    def sessions_for_portfolio(self, portfolio_id: str) -> List[PortfolioSession]:
        """Return all sessions (active + archived) for a portfolio."""
        self._assert_running()
        return self._registry.sessions_for_portfolio(portfolio_id)

    def history(self) -> Dict[str, Any]:
        """Return a snapshot of recent history (events + transitions)."""
        self._assert_running()
        return {
            "events":      [e.to_dict() for e in self._history.events()],
            "transitions": [t.to_dict() for t in self._history.transitions()],
        }

    def statistics(self) -> Dict[str, Any]:
        """Return a statistics snapshot."""
        self._assert_running()
        snap = self._stats.snapshot()
        snap["active_sessions"]   = self._registry.active_count()
        snap["archived_sessions"] = self._registry.archived_count()
        return snap

    # ==================================================================
    # Event listeners
    # ==================================================================

    def add_listener(self, listener: Callable[[PortfolioEvent], None]) -> None:
        """Register a callable to receive portfolio lifecycle events."""
        with self._listener_lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[PortfolioEvent], None]) -> None:
        """Deregister a previously registered event listener."""
        with self._listener_lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

    # ==================================================================
    # Internal helpers
    # ==================================================================

    def _assert_running(self) -> None:
        """Guard: raise if the engine is not in RUNNING state."""
        if self.lifecycle_state().value != "running":
            raise PortfolioLifecycleNotRunningError()

    def _transition(
        self,
        session_id: str,
        to_state:   PortfolioState,
        *,
        actor:    str,
        reason:   str,
        event_fn: Optional[Callable],
    ) -> PortfolioSession:
        """Internal helper — apply a state transition and dispatch event."""
        self._assert_running()
        session = self._registry.get_active(session_id)
        session.transition_to(to_state, actor=actor, reason=reason)
        self._stats.record_transition()

        # Record latest transition in history
        if session.transitions:
            self._history.record_transition(session.transitions[-1])

        if event_fn is not None:
            event = event_fn(session_id, session.portfolio_id)
            self._history.record_event(event)
            self._dispatch(event)
        return session

    def _dispatch(self, event: PortfolioEvent) -> None:
        """Deliver an event to all registered listeners (errors are absorbed)."""
        with self._listener_lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:  # noqa: BLE001
                _log.warning(f"Portfolio lifecycle listener error: {exc}")
