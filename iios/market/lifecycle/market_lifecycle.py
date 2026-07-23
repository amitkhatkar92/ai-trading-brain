"""
market_lifecycle.py — iios.market.lifecycle
=============================================
Primary public interface of the Market Lifecycle subsystem.

:class:`MarketLifecycle` is the ONLY interface external callers use to
manage market session lifecycle.

Responsibilities
----------------
* Session creation
* State-transition orchestration (initialize → collect → validate → ready →
  analyze → monitor → pause → resume → complete → fail → archive)
* Event dispatch to registered listeners
* History and statistics accumulation
* Structural integrity validation

Non-Responsibilities (intentional exclusions)
---------------------------------------------
* Market analysis / calculations
* Policy evaluation
* Portfolio management
* Execution routing

C12 Market Intelligence — Phase 1, Module 1
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
    MarketPriority,
    MarketScope,
    MarketState,
    MarketTimeframe,
    MarketType,
)
from .exceptions import (
    MarketLifecycleError,
    MarketLifecycleNotRunningError,
    MarketSessionNotFoundError,
    MarketValidationError,
)
from .market_events import (
    MarketEvent,
    make_market_archived,
    make_market_analysis_started,
    make_market_collected,
    make_market_completed,
    make_market_created,
    make_market_failed,
    make_market_initialized,
    make_market_monitoring_started,
    make_market_paused,
    make_market_resumed,
    make_market_validated,
)
from .market_factory import MarketFactory
from .market_history import MarketHistory
from .market_registry import MarketRegistry
from .market_session import MarketSession
from .market_statistics import MarketStatistics
from .market_validation import MarketValidationResult, MarketValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class MarketLifecycle(LifecycleAwareMixin):
    """
    Institutional market lifecycle engine.

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

        lc = MarketLifecycle()
        lc.start()
        session = lc.create("mkt-analysis-001")
        lc.initialize(session.session_id)
        lc.collect(session.session_id)
        lc.validate_session(session.session_id)
        lc.mark_ready(session.session_id)
        lc.start_analysis(session.session_id)
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
        self._factory   = MarketFactory()
        self._registry  = MarketRegistry(
            max_active_sessions   = max_active_sessions,
            max_archived_sessions = max_archived_sessions,
        )
        self._history   = MarketHistory(
            max_events      = max_history,
            max_transitions = max_transitions,
        )
        self._stats      = MarketStatistics()
        self._validator  = MarketValidator()
        self._listeners: List[Callable[[MarketEvent], None]] = []
        self._listener_lock = threading.Lock()

    # ==================================================================
    # LifecycleAwareMixin hooks
    # ==================================================================

    def _on_start(self) -> None:
        _log.info(
            f"MarketLifecycle starting — {LIFECYCLE_SYSTEM_ID}",
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
            f"MarketLifecycle stopping — {LIFECYCLE_SYSTEM_ID}",
        )
        _audit.log_lifecycle_event(
            engine_id  = LIFECYCLE_SYSTEM_ID,
            from_state = "RUNNING",
            to_state   = "STOPPED",
            version    = VERSION,
            actor      = ACTOR_LIFECYCLE,
        )

    # ==================================================================
    # Guard
    # ==================================================================

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise MarketLifecycleNotRunningError()

    # ==================================================================
    # Session creation
    # ==================================================================

    def create(
        self,
        market_analysis_id: str,
        *,
        session_id:       Optional[str]            = None,
        workflow_id:      str                       = "",
        exchange:         str                       = "",
        market_scope:     MarketScope               = MarketScope.DOMESTIC,
        market_type:      MarketType                = MarketType.CUSTOM,
        market_priority:  MarketPriority            = MarketPriority.MEDIUM,
        timeframe:        MarketTimeframe            = MarketTimeframe.D1,
        market_version:   int                       = 1,
        metadata:         Optional[Dict[str, Any]]  = None,
        actor:            str                       = ACTOR_LIFECYCLE,
    ) -> MarketSession:
        """
        Create a new market session in CREATED state.

        Parameters
        ----------
        market_analysis_id : Market analysis correlation identifier.
        session_id :         Optional explicit session ID.
        workflow_id :        Workflow routing context.
        exchange :           Exchange or venue identifier.
        market_scope :       Scope of the market analysis.
        market_type :        Type of market being analysed.
        market_priority :    Priority level.
        timeframe :          Analysis timeframe.
        market_version :     Initial version counter.
        metadata :           Supplementary metadata.
        actor :              Requesting actor identifier.

        Returns
        -------
        MarketSession
        """
        self._assert_running()
        session = self._factory.create(
            market_analysis_id,
            session_id      = session_id,
            workflow_id     = workflow_id,
            exchange        = exchange,
            market_scope    = market_scope,
            market_type     = market_type,
            market_priority = market_priority,
            timeframe       = timeframe,
            market_version  = market_version,
            metadata        = metadata,
        )
        self._registry.add(session)
        self._stats.record_session_created()
        event = make_market_created(
            session.session_id,
            session.market_analysis_id,
            session.exchange,
            payload={"actor": actor},
        )
        self._history.record_event(event)
        self._dispatch(event)
        _log.debug(
            f"Market session created: {session.session_id} → "
            f"{market_analysis_id}/{exchange or 'n/a'}"
        )
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
    ) -> MarketSession:
        """Transition a CREATED session to INITIALIZING."""
        return self._transition(
            session_id, MarketState.INITIALIZING,
            actor=actor, reason=reason,
            event_fn=make_market_initialized,
        )

    def collect(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> MarketSession:
        """Transition an INITIALIZING (or VALIDATING) session to COLLECTING."""
        return self._transition(
            session_id, MarketState.COLLECTING,
            actor=actor, reason=reason,
            event_fn=make_market_collected,
        )

    def validate_session(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> MarketSession:
        """Transition a COLLECTING session to VALIDATING."""
        return self._transition(
            session_id, MarketState.VALIDATING,
            actor=actor, reason=reason,
            event_fn=make_market_validated,
        )

    def mark_ready(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> MarketSession:
        """Transition a VALIDATING session to READY."""
        return self._transition(
            session_id, MarketState.READY,
            actor=actor, reason=reason,
            event_fn=None,
        )

    def start_analysis(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> MarketSession:
        """Transition a READY (or RESUMING) session to ANALYZING."""
        return self._transition(
            session_id, MarketState.ANALYZING,
            actor=actor, reason=reason,
            event_fn=make_market_analysis_started,
        )

    def start_monitoring(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> MarketSession:
        """Transition an ANALYZING (or RESUMING) session to MONITORING."""
        return self._transition(
            session_id, MarketState.MONITORING,
            actor=actor, reason=reason,
            event_fn=make_market_monitoring_started,
        )

    def pause(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> MarketSession:
        """Transition an active session to PAUSED."""
        return self._transition(
            session_id, MarketState.PAUSED,
            actor=actor, reason=reason,
            event_fn=make_market_paused,
        )

    def resume(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> MarketSession:
        """Transition a PAUSED session to RESUMING."""
        return self._transition(
            session_id, MarketState.RESUMING,
            actor=actor, reason=reason,
            event_fn=make_market_resumed,
        )

    def complete(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> MarketSession:
        """Transition to COMPLETED."""
        return self._transition(
            session_id, MarketState.COMPLETED,
            actor=actor, reason=reason,
            event_fn=make_market_completed,
        )

    def fail(
        self,
        session_id: str,
        *,
        reason: str = "",
        actor:  str = ACTOR_LIFECYCLE,
    ) -> MarketSession:
        """Transition to FAILED and record the failure reason."""
        session = self._registry.get_active(session_id)
        session.mark_failed(reason=reason, actor=actor)
        self._stats.record_session_failed()
        self._stats.record_transition()
        transition = session.transitions[-1]
        self._history.record_transition(transition)
        event = make_market_failed(
            session.session_id,
            session.market_analysis_id,
            session.exchange,
            payload={"actor": actor, "reason": reason},
        )
        self._history.record_event(event)
        self._dispatch(event)
        _log.debug(f"Market session failed: {session_id} — {reason}")
        return session

    def archive(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> MarketSession:
        """Transition a COMPLETED or FAILED session to ARCHIVED."""
        session = self._registry.get_active(session_id)
        session.transition_to(MarketState.ARCHIVED, actor=actor, reason=reason)
        self._registry.archive(session_id)
        self._stats.record_session_archived()
        self._stats.record_transition()
        transition = session.transitions[-1]
        self._history.record_transition(transition)
        event = make_market_archived(
            session.session_id,
            session.market_analysis_id,
            session.exchange,
            payload={"actor": actor},
        )
        self._history.record_event(event)
        self._dispatch(event)
        _log.debug(f"Market session archived: {session_id}")
        return session

    # ==================================================================
    # Query
    # ==================================================================

    def get_session(self, session_id: str) -> MarketSession:
        """Return a session by ID (active or archived)."""
        return self._registry.get(session_id)

    def find_session(self, session_id: str) -> Optional[MarketSession]:
        """Return a session by ID or None."""
        return self._registry.find(session_id)

    def active_sessions(self) -> List[MarketSession]:
        """Return all active sessions."""
        return self._registry.active_sessions()

    def sessions_by_state(self, state: MarketState) -> List[MarketSession]:
        """Return active sessions in the given state."""
        return self._registry.sessions_by_state(state)

    def sessions_by_exchange(self, exchange: str) -> List[MarketSession]:
        """Return active sessions for the given exchange."""
        return self._registry.sessions_by_exchange(exchange)

    # ==================================================================
    # Validation
    # ==================================================================

    def validate(self, session_id: str) -> MarketValidationResult:
        """Validate structural integrity of a session."""
        session = self._registry.get(session_id)
        return self._validator.validate(session)

    # ==================================================================
    # Statistics / History
    # ==================================================================

    def statistics(self) -> Dict[str, Any]:
        """Return a snapshot of lifecycle statistics."""
        return self._stats.snapshot()

    def events(self) -> List[MarketEvent]:
        """Return all retained lifecycle events."""
        return self._history.events()   # type: ignore[return-value]

    def recent_events(self, n: int = 20) -> List[MarketEvent]:
        """Return the *n* most recent lifecycle events."""
        all_events = self._history.events()
        return all_events[-n:] if n < len(all_events) else all_events

    def transitions(self) -> List:
        """Return all retained transition records."""
        return self._history.transitions()

    # ==================================================================
    # Listeners
    # ==================================================================

    def add_listener(self, fn: Callable[[MarketEvent], None]) -> None:
        """Register a callable to receive lifecycle events."""
        with self._listener_lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable[[MarketEvent], None]) -> None:
        """De-register a listener."""
        with self._listener_lock:
            if fn in self._listeners:
                self._listeners.remove(fn)

    def _dispatch(self, event: MarketEvent) -> None:
        with self._listener_lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception as exc:
                _log.warning(f"MarketLifecycle listener error: {exc}")

    # ==================================================================
    # Internal transition helper
    # ==================================================================

    def _transition(
        self,
        session_id: str,
        to_state:   MarketState,
        *,
        actor:    str,
        reason:   str,
        event_fn: Optional[Callable],
    ) -> MarketSession:
        session    = self._registry.get_active(session_id)
        transition = session.transition_to(to_state, actor=actor, reason=reason)
        self._stats.record_transition()
        self._history.record_transition(transition)

        if event_fn is not None:
            event = event_fn(
                session.session_id,
                session.market_analysis_id,
                session.exchange,
                payload={"actor": actor, "reason": reason},
            )
            self._history.record_event(event)
            self._dispatch(event)

        # Record terminal statistics
        if to_state == MarketState.COMPLETED:
            duration = session.duration_s or 0.0
            self._stats.record_session_completed(duration_s=duration)

        _log.debug(f"Market session {session_id}: → {to_state.value}")
        return session
