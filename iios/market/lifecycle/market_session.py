"""
market_session.py — iios.market.lifecycle
===========================================
Core domain object representing a single market lifecycle session.

C12 Market Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    ACTOR_LIFECYCLE,
    VERSION,
    ACTIVE_STATES,
    TERMINAL_STATES,
    IMMUTABLE_STATES,
    SUCCESS_STATES,
    VALID_TRANSITIONS,
    MarketPriority,
    MarketScope,
    MarketState,
    MarketTimeframe,
    MarketType,
)
from .market_state import MarketStateRecord
from .market_transition import MarketTransition, make_transition
from .exceptions import (
    MarketInvalidTransitionError,
    MarketSessionTerminatedError,
)


class MarketSession:
    """
    Mutable domain object that carries the full lifecycle state of a single
    institutional market session.

    Create via :class:`MarketFactory` or :meth:`MarketLifecycle.create`.
    Do not construct directly in application code.

    Attributes
    ----------
    session_id :         Unique identifier for this lifecycle session.
    market_analysis_id : Market analysis correlation identifier.
    workflow_id :        Workflow routing context.
    exchange :           Exchange or venue identifier.
    market_scope :       Scope of the market analysis.
    market_type :        Type of market being analysed.
    timeframe :          Analysis timeframe.
    market_priority :    Priority level of this session.
    market_version :     Monotonically incrementing version counter.
    state :              Current :class:`MarketState`.
    failure_reason :     Non-empty when the session is in FAILED state.
    created_at :         Wall-clock creation time.
    updated_at :         Wall-clock time of the most recent state change.
    start_time :         Wall-clock time when the session entered ANALYZING.
    end_time :           Wall-clock time when the session terminated.
    """

    def __init__(
        self,
        *,
        session_id:         Optional[str]          = None,
        market_analysis_id: str,
        workflow_id:        str                    = "",
        exchange:           str                    = "",
        market_scope:       MarketScope            = MarketScope.DOMESTIC,
        market_type:        MarketType             = MarketType.CUSTOM,
        market_priority:    MarketPriority         = MarketPriority.MEDIUM,
        timeframe:          MarketTimeframe         = MarketTimeframe.D1,
        market_version:     int                    = 1,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> None:
        self._session_id         = session_id or str(uuid.uuid4())
        self._market_analysis_id = market_analysis_id
        self._workflow_id        = workflow_id
        self._exchange           = exchange
        self._market_scope       = market_scope
        self._market_type        = market_type
        self._market_priority    = market_priority
        self._timeframe          = timeframe
        self._market_version     = market_version
        self._metadata           = dict(metadata or {})

        now                                = time.time()
        self._state: MarketState            = MarketState.CREATED
        self._start_time: Optional[float]  = None
        self._end_time:   Optional[float]  = None
        self._failure_reason: str          = ""
        self._created_at: float            = now
        self._updated_at: float            = now

        self._state_history: List[MarketStateRecord] = [
            MarketStateRecord(
                state      = MarketState.CREATED,
                entered_at = now,
                actor      = ACTOR_LIFECYCLE,
            )
        ]
        self._transitions: List[MarketTransition] = []

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def market_analysis_id(self) -> str:
        return self._market_analysis_id

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def exchange(self) -> str:
        return self._exchange

    @property
    def market_scope(self) -> MarketScope:
        return self._market_scope

    @property
    def market_type(self) -> MarketType:
        return self._market_type

    @property
    def market_priority(self) -> MarketPriority:
        return self._market_priority

    @property
    def timeframe(self) -> MarketTimeframe:
        return self._timeframe

    @property
    def market_version(self) -> int:
        return self._market_version

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    @property
    def state(self) -> MarketState:
        return self._state

    @property
    def failure_reason(self) -> str:
        return self._failure_reason

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    @property
    def start_time(self) -> Optional[float]:
        return self._start_time

    @property
    def end_time(self) -> Optional[float]:
        return self._end_time

    @property
    def state_history(self) -> List[MarketStateRecord]:
        return list(self._state_history)

    @property
    def transitions(self) -> List[MarketTransition]:
        return list(self._transitions)

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """True when the session is in an active (non-terminal) state."""
        return self._state in ACTIVE_STATES

    @property
    def is_terminal(self) -> bool:
        """True when the session has reached a terminal state."""
        return self._state in TERMINAL_STATES

    @property
    def is_immutable(self) -> bool:
        """True when the session is in ARCHIVED (immutable) state."""
        return self._state in IMMUTABLE_STATES

    @property
    def is_successful(self) -> bool:
        """True when the session completed successfully."""
        return self._state in SUCCESS_STATES

    @property
    def duration_s(self) -> Optional[float]:
        """Session duration in seconds (None if not yet terminal)."""
        if self._start_time is None or self._end_time is None:
            return None
        return self._end_time - self._start_time

    # ------------------------------------------------------------------
    # State transition
    # ------------------------------------------------------------------

    def transition_to(
        self,
        to_state:  MarketState,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> MarketTransition:
        """
        Apply a state transition, record history, and return the
        :class:`MarketTransition` record.

        Raises
        ------
        MarketSessionTerminatedError
            When the session is in an immutable (ARCHIVED) state.
        MarketInvalidTransitionError
            When the requested transition is not valid.
        """
        if self._state in IMMUTABLE_STATES:
            raise MarketSessionTerminatedError(
                session_id=self._session_id,
                state=self._state.value,
            )

        allowed = VALID_TRANSITIONS.get(self._state, frozenset())
        if to_state not in allowed:
            raise MarketInvalidTransitionError(
                from_state = self._state,
                to_state   = to_state,
                session_id = self._session_id,
            )

        from_state = self._state
        now        = time.time()

        self._state      = to_state
        self._updated_at = now
        self._market_version += 1

        self._state_history.append(
            MarketStateRecord(
                state      = to_state,
                entered_at = now,
                actor      = actor,
                reason     = reason,
            )
        )

        # Track start/end timestamps
        if to_state == MarketState.ANALYZING and self._start_time is None:
            self._start_time = now
        if to_state in TERMINAL_STATES:
            self._end_time = now

        transition = make_transition(
            session_id = self._session_id,
            from_state = from_state,
            to_state   = to_state,
            actor      = actor,
            reason     = reason,
        )
        self._transitions.append(transition)
        return transition

    def mark_failed(
        self,
        reason: str = "",
        *,
        actor: str = ACTOR_LIFECYCLE,
    ) -> MarketTransition:
        """
        Convenience method — transition to FAILED and record the reason.
        """
        self._failure_reason = reason
        return self.transition_to(
            MarketState.FAILED,
            actor=actor,
            reason=reason,
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for logging or persistence."""
        return {
            "session_id":          self._session_id,
            "market_analysis_id":  self._market_analysis_id,
            "workflow_id":         self._workflow_id,
            "exchange":            self._exchange,
            "market_scope":        self._market_scope.value,
            "market_type":         self._market_type.value,
            "market_priority":     self._market_priority.value,
            "timeframe":           self._timeframe.value,
            "market_version":      self._market_version,
            "state":               self._state.value,
            "failure_reason":      self._failure_reason,
            "is_active":           self.is_active,
            "is_terminal":         self.is_terminal,
            "duration_s":          self.duration_s,
            "created_at":          self._created_at,
            "updated_at":          self._updated_at,
            "start_time":          self._start_time,
            "end_time":            self._end_time,
            "version":             VERSION,
        }

    def __repr__(self) -> str:
        return (
            f"MarketSession("
            f"session_id={self._session_id!r}, "
            f"market_analysis_id={self._market_analysis_id!r}, "
            f"exchange={self._exchange!r}, "
            f"state={self._state.value!r})"
        )
