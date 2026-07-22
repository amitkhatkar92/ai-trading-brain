"""
risk_session.py — iios.risk.lifecycle
========================================
Core domain object representing a single risk lifecycle session.

C11 Risk Intelligence — Phase 1, Module 1
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
    RiskPriority,
    RiskScope,
    RiskState,
    RiskType,
)
from .risk_state import RiskStateRecord
from .risk_transition import RiskTransition, make_transition
from .exceptions import (
    RiskInvalidTransitionError,
    RiskSessionTerminatedError,
)


class RiskSession:
    """
    Mutable domain object that carries the full lifecycle state of a single
    institutional risk session.

    Create via :class:`RiskFactory` or :meth:`RiskLifecycle.create`.
    Do not construct directly in application code.

    Attributes
    ----------
    session_id :      Unique identifier for this lifecycle session.
    risk_id :         Risk assessment identifier.
    assessment_id :   Assessment correlation identifier.
    workflow_id :     Workflow routing context.
    portfolio_id :    Portfolio being assessed.
    strategy_id :     Strategy being assessed (may be empty).
    risk_scope :      Scope of the risk assessment.
    risk_type :       Type of risk being assessed.
    risk_priority :   Priority level of this session.
    risk_version :    Monotonically incrementing version counter.
    state :           Current :class:`RiskState`.
    failure_reason :  Non-empty when the session is in FAILED state.
    created_at :      Wall-clock creation time.
    updated_at :      Wall-clock time of the most recent state change.
    start_time :      Wall-clock time when the session entered ASSESSING.
    end_time :        Wall-clock time when the session terminated.
    """

    def __init__(
        self,
        *,
        session_id:    Optional[str]          = None,
        risk_id:       str,
        assessment_id: str                    = "",
        workflow_id:   str                    = "",
        portfolio_id:  str,
        strategy_id:   str                    = "",
        risk_scope:    RiskScope              = RiskScope.PORTFOLIO,
        risk_type:     RiskType               = RiskType.CUSTOM,
        risk_priority: RiskPriority           = RiskPriority.MEDIUM,
        risk_version:  int                    = 1,
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> None:
        self._session_id    = session_id or str(uuid.uuid4())
        self._risk_id       = risk_id
        self._assessment_id = assessment_id
        self._workflow_id   = workflow_id
        self._portfolio_id  = portfolio_id
        self._strategy_id   = strategy_id
        self._risk_scope    = risk_scope
        self._risk_type     = risk_type
        self._risk_priority = risk_priority
        self._risk_version  = risk_version
        self._metadata      = dict(metadata or {})

        now                              = time.time()
        self._state: RiskState            = RiskState.CREATED
        self._start_time: Optional[float] = None
        self._end_time:   Optional[float] = None
        self._failure_reason: str         = ""
        self._created_at: float           = now
        self._updated_at: float           = now

        self._state_history: List[RiskStateRecord] = [
            RiskStateRecord(
                state      = RiskState.CREATED,
                entered_at = now,
                actor      = ACTOR_LIFECYCLE,
                reason     = "session created",
            )
        ]
        self._transitions: List[RiskTransition] = []

    # ==================================================================
    # Read-only properties
    # ==================================================================

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def risk_id(self) -> str:
        return self._risk_id

    @property
    def assessment_id(self) -> str:
        return self._assessment_id

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    @property
    def risk_scope(self) -> RiskScope:
        return self._risk_scope

    @property
    def risk_type(self) -> RiskType:
        return self._risk_type

    @property
    def risk_priority(self) -> RiskPriority:
        return self._risk_priority

    @property
    def risk_version(self) -> int:
        return self._risk_version

    @property
    def state(self) -> RiskState:
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
    def state_history(self) -> List[RiskStateRecord]:
        return list(self._state_history)

    @property
    def transitions(self) -> List[RiskTransition]:
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
        return self._state == RiskState.FAILED

    @property
    def is_archived(self) -> bool:
        return self._state == RiskState.ARCHIVED

    @property
    def is_paused(self) -> bool:
        return self._state == RiskState.PAUSED

    @property
    def is_assessing(self) -> bool:
        return self._state == RiskState.ASSESSING

    @property
    def is_monitoring(self) -> bool:
        return self._state == RiskState.MONITORING

    # ==================================================================
    # Duration
    # ==================================================================

    @property
    def duration_s(self) -> float:
        """
        Elapsed session duration in seconds.

        Uses ``end_time`` when terminated; otherwise current wall-clock.
        """
        end = self._end_time if self._end_time is not None else time.time()
        return end - self._created_at

    # ==================================================================
    # Transition
    # ==================================================================

    def transition_to(
        self,
        to_state: RiskState,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> "RiskSession":
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
        RiskSessionTerminatedError
            When the session is in an immutable (ARCHIVED) state.
        RiskInvalidTransitionError
            When the transition is not permitted.
        """
        if self._state in IMMUTABLE_STATES:
            raise RiskSessionTerminatedError(
                self._session_id, state=self._state.value
            )

        allowed = VALID_TRANSITIONS.get(self._state, frozenset())
        if to_state not in allowed:
            raise RiskInvalidTransitionError(
                self._state, to_state, self._session_id
            )

        now        = time.time()
        from_state = self._state

        # Record transition
        transition = make_transition(
            self._session_id, from_state, to_state,
            actor=actor, reason=reason,
        )
        self._transitions.append(transition)

        # Record state entry
        self._state_history.append(
            RiskStateRecord(
                state      = to_state,
                entered_at = now,
                actor      = actor,
                reason     = reason,
            )
        )

        # Update state
        self._state      = to_state
        self._updated_at = now

        # Track start / end
        if to_state == RiskState.ASSESSING and self._start_time is None:
            self._start_time = now
        if to_state in TERMINAL_STATES:
            self._end_time = now
        if to_state == RiskState.FAILED:
            self._failure_reason = reason or "session failed"

        return self

    # ==================================================================
    # Serialization
    # ==================================================================

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id":    self._session_id,
            "risk_id":       self._risk_id,
            "assessment_id": self._assessment_id,
            "workflow_id":   self._workflow_id,
            "portfolio_id":  self._portfolio_id,
            "strategy_id":   self._strategy_id,
            "risk_scope":    self._risk_scope.value,
            "risk_type":     self._risk_type.value,
            "risk_priority": self._risk_priority.value,
            "risk_version":  self._risk_version,
            "state":         self._state.value,
            "failure_reason": self._failure_reason,
            "created_at":    self._created_at,
            "updated_at":    self._updated_at,
            "start_time":    self._start_time,
            "end_time":      self._end_time,
            "duration_s":    self.duration_s,
            "transitions":   len(self._transitions),
            "framework_version": VERSION,
        }
