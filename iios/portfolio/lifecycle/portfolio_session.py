"""
portfolio_session.py — iios.portfolio.lifecycle
=================================================
Core domain object representing a single portfolio lifecycle session.

C10 Portfolio Intelligence — Phase 1, Module 1
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
    PortfolioObjective,
    PortfolioScope,
    PortfolioState,
    PortfolioStatus,
    PortfolioType,
)
from .portfolio_state import PortfolioStateRecord
from .portfolio_transition import PortfolioTransition, make_transition
from .exceptions import (
    PortfolioInvalidTransitionError,
    PortfolioSessionTerminatedError,
)


class PortfolioSession:
    """
    Mutable domain object that carries the full lifecycle state of a single
    institutional portfolio session.

    Create via :class:`PortfolioFactory` or :meth:`PortfolioLifecycle.create`.
    Do not construct directly in application code.

    Attributes
    ----------
    session_id :          Unique identifier for this lifecycle session.
    portfolio_id :        Identifier of the portfolio being managed.
    portfolio_version :   Monotonically incrementing version counter.
    portfolio_name :      Human-readable name.
    portfolio_type :      Asset-composition classification.
    portfolio_scope :     Institutional scope.
    portfolio_objective : Investment objective.
    portfolio_currency :  Base currency (ISO 4217).
    portfolio_status :    Operational status.
    state :               Current :class:`PortfolioState`.
    failure_reason :      Non-empty when the session is in FAILED state.
    created_at :          Wall-clock creation time.
    updated_at :          Wall-clock time of the most recent state change.
    start_time :          Wall-clock time when the session became ACTIVE.
    end_time :            Wall-clock time when the session terminated.
    """

    def __init__(
        self,
        *,
        session_id:           Optional[str]       = None,
        portfolio_id:         str,
        portfolio_version:    int                 = 1,
        portfolio_name:       str                 = "",
        portfolio_type:       PortfolioType        = PortfolioType.CUSTOM,
        portfolio_scope:      PortfolioScope       = PortfolioScope.INSTITUTIONAL,
        portfolio_objective:  PortfolioObjective   = PortfolioObjective.CUSTOM,
        portfolio_currency:   str                 = "INR",
        portfolio_status:     PortfolioStatus      = PortfolioStatus.INACTIVE,
        metadata:             Optional[Dict[str, Any]] = None,
    ) -> None:
        self._session_id          = session_id or str(uuid.uuid4())
        self._portfolio_id        = portfolio_id
        self._portfolio_version   = portfolio_version
        self._portfolio_name      = portfolio_name
        self._portfolio_type      = portfolio_type
        self._portfolio_scope     = portfolio_scope
        self._portfolio_objective = portfolio_objective
        self._portfolio_currency  = portfolio_currency
        self._portfolio_status    = portfolio_status
        self._metadata            = dict(metadata or {})

        now                               = time.time()
        self._state: PortfolioState        = PortfolioState.CREATED
        self._start_time: Optional[float]  = None
        self._end_time:   Optional[float]  = None
        self._failure_reason: str          = ""
        self._created_at: float            = now
        self._updated_at: float            = now

        self._state_history: List[PortfolioStateRecord] = [
            PortfolioStateRecord(
                state      = PortfolioState.CREATED,
                entered_at = now,
                actor      = ACTOR_LIFECYCLE,
                reason     = "session created",
            )
        ]
        self._transitions: List[PortfolioTransition] = []

    # ==================================================================
    # Read-only properties
    # ==================================================================

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def portfolio_version(self) -> int:
        return self._portfolio_version

    @property
    def portfolio_name(self) -> str:
        return self._portfolio_name

    @property
    def portfolio_type(self) -> PortfolioType:
        return self._portfolio_type

    @property
    def portfolio_scope(self) -> PortfolioScope:
        return self._portfolio_scope

    @property
    def portfolio_objective(self) -> PortfolioObjective:
        return self._portfolio_objective

    @property
    def portfolio_currency(self) -> str:
        return self._portfolio_currency

    @property
    def portfolio_status(self) -> PortfolioStatus:
        return self._portfolio_status

    @property
    def state(self) -> PortfolioState:
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
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    @property
    def state_history(self) -> List[PortfolioStateRecord]:
        return list(self._state_history)

    @property
    def transitions(self) -> List[PortfolioTransition]:
        return list(self._transitions)

    # ==================================================================
    # State queries
    # ==================================================================

    @property
    def is_active(self) -> bool:
        return self._state in ACTIVE_STATES

    @property
    def is_terminal(self) -> bool:
        return self._state in TERMINAL_STATES

    @property
    def is_completed(self) -> bool:
        return self._state in SUCCESS_STATES

    @property
    def is_failed(self) -> bool:
        return self._state == PortfolioState.FAILED

    @property
    def is_archived(self) -> bool:
        return self._state == PortfolioState.ARCHIVED

    @property
    def is_paused(self) -> bool:
        return self._state == PortfolioState.PAUSED

    @property
    def is_rebalancing(self) -> bool:
        return self._state == PortfolioState.REBALANCING

    # ==================================================================
    # Transition
    # ==================================================================

    def transition_to(
        self,
        to_state: PortfolioState,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> "PortfolioSession":
        """
        Apply a state transition.

        Parameters
        ----------
        to_state : Target state.
        actor :    Actor identifier for audit.
        reason :   Optional human-readable reason.

        Returns
        -------
        self (for chaining)

        Raises
        ------
        PortfolioSessionTerminatedError
            When the session is in an immutable (ARCHIVED) state.
        PortfolioInvalidTransitionError
            When the transition is not permitted.
        """
        if self._state in IMMUTABLE_STATES:
            raise PortfolioSessionTerminatedError(
                self._session_id, state=self._state.value
            )

        allowed = VALID_TRANSITIONS.get(self._state, frozenset())
        if to_state not in allowed:
            raise PortfolioInvalidTransitionError(
                self._state, to_state, self._session_id
            )

        now       = time.time()
        prev      = self._state
        self._state     = to_state
        self._updated_at = now

        # Lifecycle bookkeeping
        if to_state == PortfolioState.ACTIVE and self._start_time is None:
            self._start_time = now
        if to_state in TERMINAL_STATES and self._end_time is None:
            self._end_time = now
        if to_state == PortfolioState.ACTIVE:
            self._portfolio_status = PortfolioStatus.ACTIVE
        if to_state in (PortfolioState.COMPLETED, PortfolioState.FAILED,
                        PortfolioState.ARCHIVED):
            self._portfolio_status = PortfolioStatus.CLOSED

        # Append history
        self._state_history.append(
            PortfolioStateRecord(
                state      = to_state,
                entered_at = now,
                actor      = actor,
                reason     = reason,
            )
        )
        self._transitions.append(
            make_transition(
                self._session_id, prev, to_state,
                actor=actor, reason=reason,
            )
        )
        self._portfolio_version += 1
        return self

    def fail(
        self,
        reason: str = "",
        *,
        actor: str = ACTOR_LIFECYCLE,
    ) -> "PortfolioSession":
        """Convenience shortcut to transition to FAILED state."""
        self._failure_reason = reason
        return self.transition_to(PortfolioState.FAILED, actor=actor, reason=reason)

    # ==================================================================
    # Duration helpers
    # ==================================================================

    def duration_s(self) -> Optional[float]:
        """
        Wall-clock duration of the session in seconds.

        Returns the elapsed time from creation to end (if terminated) or
        the current elapsed time (if still active).
        """
        end = self._end_time or time.time()
        return end - self._created_at

    # ==================================================================
    # Serialisation
    # ==================================================================

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id":          self._session_id,
            "portfolio_id":        self._portfolio_id,
            "portfolio_version":   self._portfolio_version,
            "portfolio_name":      self._portfolio_name,
            "portfolio_type":      self._portfolio_type.value,
            "portfolio_scope":     self._portfolio_scope.value,
            "portfolio_objective": self._portfolio_objective.value,
            "portfolio_currency":  self._portfolio_currency,
            "portfolio_status":    self._portfolio_status.value,
            "state":               self._state.value,
            "failure_reason":      self._failure_reason,
            "created_at":          self._created_at,
            "updated_at":          self._updated_at,
            "start_time":          self._start_time,
            "end_time":            self._end_time,
            "transition_count":    len(self._transitions),
        }

    def __repr__(self) -> str:
        return (
            f"PortfolioSession("
            f"session_id={self._session_id!r}, "
            f"portfolio_id={self._portfolio_id!r}, "
            f"state={self._state.value!r})"
        )
