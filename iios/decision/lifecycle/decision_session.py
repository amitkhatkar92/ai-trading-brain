"""
decision_session.py — iios.decision.lifecycle
===============================================
Core domain object representing a single decision lifecycle session.

C9 Decision Intelligence — Phase 1, Module 1
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
    DecisionPriority,
    DecisionScope,
    DecisionState,
    DecisionTrigger,
    DecisionType,
)
from .decision_state import DecisionStateRecord
from .decision_transition import DecisionTransition, make_transition
from .exceptions import DecisionInvalidTransitionError, DecisionSessionTerminatedError


class DecisionSession:
    """
    Mutable domain object that carries the full lifecycle state of a single
    institutional decision session.

    Create via :class:`DecisionFactory` or :meth:`DecisionLifecycle.create`.
    Do not construct directly in application code.

    Attributes
    ----------
    session_id :         Unique identifier for this lifecycle session.
    decision_id :        Identifier of the decision being managed.
    workflow_id :        Optional workflow context.
    portfolio_id :       Optional portfolio context.
    strategy_id :        Optional strategy context.
    decision_scope :     Scope of the decision.
    decision_type :      Type of the decision.
    decision_priority :  Scheduling priority.
    decision_trigger :   What initiated the decision.
    decision_reason :    Human-readable reason for the decision.
    decision_version :   Monotonically incrementing version counter.
    state :              Current :class:`DecisionState`.
    start_time :         Wall-clock time when the session became ACTIVE.
    end_time :           Wall-clock time when the session became COMPLETED or FAILED.
    failure_reason :     Non-empty when the session is in FAILED state.
    created_at :         Wall-clock creation time.
    updated_at :         Wall-clock time of the most recent state change.
    """

    def __init__(
        self,
        *,
        session_id:         Optional[str]      = None,
        decision_id:        str,
        workflow_id:        str                = "",
        portfolio_id:       str                = "",
        strategy_id:        str                = "",
        decision_scope:     DecisionScope      = DecisionScope.ORDER,
        decision_type:      DecisionType       = DecisionType.ORDER,
        decision_priority:  DecisionPriority   = DecisionPriority.MEDIUM,
        decision_trigger:   DecisionTrigger    = DecisionTrigger.AUTOMATIC,
        decision_reason:    str                = "",
        decision_version:   int                = 1,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> None:
        self._session_id         = session_id or str(uuid.uuid4())
        self._decision_id        = decision_id
        self._workflow_id        = workflow_id
        self._portfolio_id       = portfolio_id
        self._strategy_id        = strategy_id
        self._decision_scope     = decision_scope
        self._decision_type      = decision_type
        self._decision_priority  = decision_priority
        self._decision_trigger   = decision_trigger
        self._decision_reason    = decision_reason
        self._decision_version   = decision_version
        self._metadata           = dict(metadata or {})

        now                               = time.time()
        self._state: DecisionState        = DecisionState.CREATED
        self._start_time: Optional[float] = None
        self._end_time:   Optional[float] = None
        self._failure_reason: str         = ""
        self._created_at: float           = now
        self._updated_at: float           = now

        self._state_history: List[DecisionStateRecord] = [
            DecisionStateRecord(
                state      = DecisionState.CREATED,
                entered_at = now,
                actor      = ACTOR_LIFECYCLE,
            )
        ]
        self._transitions: List[DecisionTransition] = []

    # ------------------------------------------------------------------
    # Identity properties
    # ------------------------------------------------------------------
    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def decision_id(self) -> str:
        return self._decision_id

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
    def decision_scope(self) -> DecisionScope:
        return self._decision_scope

    @property
    def decision_type(self) -> DecisionType:
        return self._decision_type

    @property
    def decision_priority(self) -> DecisionPriority:
        return self._decision_priority

    @property
    def decision_trigger(self) -> DecisionTrigger:
        return self._decision_trigger

    @property
    def decision_reason(self) -> str:
        return self._decision_reason

    @property
    def decision_version(self) -> int:
        return self._decision_version

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    # ------------------------------------------------------------------
    # Lifecycle properties
    # ------------------------------------------------------------------
    @property
    def state(self) -> DecisionState:
        return self._state

    @property
    def start_time(self) -> Optional[float]:
        return self._start_time

    @property
    def end_time(self) -> Optional[float]:
        return self._end_time

    @property
    def failure_reason(self) -> str:
        return self._failure_reason

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    # ------------------------------------------------------------------
    # Derived status properties
    # ------------------------------------------------------------------
    @property
    def is_active(self) -> bool:
        """``True`` when the session is in any in-flight state."""
        return self._state in ACTIVE_STATES

    @property
    def is_terminal(self) -> bool:
        """``True`` when the session has ended."""
        return self._state in TERMINAL_STATES

    @property
    def is_successful(self) -> bool:
        """``True`` when the session ended successfully."""
        return self._state in SUCCESS_STATES

    @property
    def is_paused(self) -> bool:
        """``True`` when the session is in PAUSED or RESUMING state."""
        return self._state in (DecisionState.PAUSED, DecisionState.RESUMING)

    @property
    def duration_s(self) -> Optional[float]:
        """
        Total session duration in seconds, or ``None`` if not yet completed.

        Measured from ``created_at`` to ``end_time`` for terminal sessions;
        from ``created_at`` to now for in-flight sessions.
        """
        if self._end_time is not None:
            return self._end_time - self._created_at
        return time.time() - self._created_at

    # ------------------------------------------------------------------
    # History access
    # ------------------------------------------------------------------
    @property
    def state_history(self) -> List[DecisionStateRecord]:
        """Ordered list of state-entry records (oldest first)."""
        return list(self._state_history)

    @property
    def transitions(self) -> List[DecisionTransition]:
        """Ordered list of transition records (oldest first)."""
        return list(self._transitions)

    @property
    def transition_count(self) -> int:
        """Total number of state transitions executed."""
        return len(self._transitions)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def transition_to(
        self,
        to_state:    DecisionState,
        *,
        actor:       str = ACTOR_LIFECYCLE,
        reason:      str = "",
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> "DecisionSession":
        """
        Execute a state transition.

        Parameters
        ----------
        to_state :  Desired next state.
        actor :     Who is triggering the transition.
        reason :    Optional human-readable context.
        metadata :  Optional supplementary transition data.

        Returns
        -------
        self — to allow chaining.

        Raises
        ------
        DecisionSessionTerminatedError
            If the session is already in an immutable (ARCHIVED) state.
        DecisionInvalidTransitionError
            If the transition is not permitted by the state machine.
        """
        if self._state in IMMUTABLE_STATES:
            raise DecisionSessionTerminatedError(
                session_id = self._session_id,
                state      = self._state,
            )

        allowed = VALID_TRANSITIONS.get(self._state, frozenset())
        if to_state not in allowed:
            raise DecisionInvalidTransitionError(
                from_state = self._state,
                to_state   = to_state,
                session_id = self._session_id,
            )

        now            = time.time()
        from_state     = self._state
        self._state    = to_state
        self._updated_at = now
        self._decision_version += 1

        # Lifecycle bookkeeping
        if to_state == DecisionState.ACTIVE and self._start_time is None:
            self._start_time = now
        if to_state in (DecisionState.COMPLETED, DecisionState.FAILED):
            self._end_time = now
        if to_state == DecisionState.FAILED and reason:
            self._failure_reason = reason

        # Append state-history record
        self._state_history.append(
            DecisionStateRecord(
                state      = to_state,
                entered_at = now,
                actor      = actor,
                reason     = reason,
            )
        )

        # Append transition record
        self._transitions.append(
            make_transition(
                session_id = self._session_id,
                from_state = from_state,
                to_state   = to_state,
                actor      = actor,
                reason     = reason,
                metadata   = metadata,
            )
        )

        return self

    def can_transition_to(self, to_state: DecisionState) -> bool:
        """Return ``True`` iff the transition to *to_state* is currently allowed."""
        if self._state in IMMUTABLE_STATES:
            return False
        return to_state in VALID_TRANSITIONS.get(self._state, frozenset())

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Serialize the session to a plain dictionary."""
        return {
            "session_id":        self._session_id,
            "decision_id":       self._decision_id,
            "workflow_id":       self._workflow_id,
            "portfolio_id":      self._portfolio_id,
            "strategy_id":       self._strategy_id,
            "decision_scope":    self._decision_scope.value,
            "decision_type":     self._decision_type.value,
            "decision_priority": self._decision_priority.value,
            "decision_trigger":  self._decision_trigger.value,
            "decision_reason":   self._decision_reason,
            "decision_version":  self._decision_version,
            "state":             self._state.value,
            "start_time":        self._start_time,
            "end_time":          self._end_time,
            "failure_reason":    self._failure_reason,
            "created_at":        self._created_at,
            "updated_at":        self._updated_at,
            "transition_count":  len(self._transitions),
            "version":           VERSION,
        }

    def __repr__(self) -> str:
        return (
            f"DecisionSession("
            f"session_id={self._session_id!r}, "
            f"decision_id={self._decision_id!r}, "
            f"state={self._state.value!r})"
        )
