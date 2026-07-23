"""
supervisor_session.py — iios.supervisor.lifecycle
--------------------------------------------------
Core domain object representing a single supervisor lifecycle session.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 1
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
    SupervisorPriority,
    SupervisorScope,
    SupervisorState,
    SupervisorType,
)
from .supervisor_state import SupervisorStateRecord
from .supervisor_transition import SupervisorTransition, make_transition
from .exceptions import (
    SupervisorInvalidTransitionError,
    SupervisorSessionTerminatedError,
)


class SupervisorSession:
    """
    Mutable domain object that carries the full lifecycle state of a single
    institutional supervisor session.

    Create via :class:`SupervisorFactory` or :meth:`SupervisorLifecycle.create`.
    Do not construct directly in application code.

    Attributes
    ----------
    session_id :          Unique identifier for this lifecycle session.
    supervisor_id :       Supervised entity / program identifier.
    workflow_id :         Workflow routing context.
    supervisor_scope :    Institutional scope of the supervision.
    supervisor_type :     Classification of the supervisor.
    supervisor_priority : Priority level of this session.
    supervisor_version :  Monotonically incrementing version counter.
    state :               Current :class:`SupervisorState`.
    failure_reason :      Non-empty when the session is in FAILED state.
    created_at :          Wall-clock creation time.
    updated_at :          Wall-clock time of the most recent state change.
    start_time :          Wall-clock time when the session entered SUPERVISING.
    end_time :            Wall-clock time when the session terminated.
    """

    def __init__(
        self,
        *,
        session_id:          Optional[str]           = None,
        supervisor_id:       str,
        workflow_id:         str                      = "",
        supervisor_scope:    SupervisorScope          = SupervisorScope.SYSTEM,
        supervisor_type:     SupervisorType           = SupervisorType.CUSTOM,
        supervisor_priority: SupervisorPriority       = SupervisorPriority.MEDIUM,
        supervisor_version:  int                      = 1,
        metadata:            Optional[Dict[str, Any]] = None,
    ) -> None:
        self._session_id          = session_id or str(uuid.uuid4())
        self._supervisor_id       = supervisor_id
        self._workflow_id         = workflow_id
        self._supervisor_scope    = supervisor_scope
        self._supervisor_type     = supervisor_type
        self._supervisor_priority = supervisor_priority
        self._supervisor_version  = supervisor_version
        self._metadata            = dict(metadata or {})

        now                                   = time.time()
        self._state: SupervisorState           = SupervisorState.CREATED
        self._start_time: Optional[float]     = None
        self._end_time:   Optional[float]     = None
        self._failure_reason: str             = ""
        self._created_at: float               = now
        self._updated_at: float               = now

        self._state_history: List[SupervisorStateRecord] = [
            SupervisorStateRecord(
                state      = SupervisorState.CREATED,
                entered_at = now,
                actor      = ACTOR_LIFECYCLE,
            )
        ]
        self._transitions: List[SupervisorTransition] = []

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def supervisor_id(self) -> str:
        return self._supervisor_id

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def supervisor_scope(self) -> SupervisorScope:
        return self._supervisor_scope

    @property
    def supervisor_type(self) -> SupervisorType:
        return self._supervisor_type

    @property
    def supervisor_priority(self) -> SupervisorPriority:
        return self._supervisor_priority

    @property
    def supervisor_version(self) -> int:
        return self._supervisor_version

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    @property
    def state(self) -> SupervisorState:
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
    def state_history(self) -> List[SupervisorStateRecord]:
        return list(self._state_history)

    @property
    def transitions(self) -> List[SupervisorTransition]:
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
        """Session duration in seconds (None if not yet started or terminated)."""
        if self._start_time is None or self._end_time is None:
            return None
        return self._end_time - self._start_time

    # ------------------------------------------------------------------
    # State transition
    # ------------------------------------------------------------------

    def transition_to(
        self,
        to_state:  SupervisorState,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> SupervisorTransition:
        """
        Apply a state transition, record history, and return the
        :class:`SupervisorTransition` record.

        Raises
        ------
        SupervisorSessionTerminatedError
            When the session is in an immutable (ARCHIVED) state.
        SupervisorInvalidTransitionError
            When the requested transition is not valid.
        """
        if self._state in IMMUTABLE_STATES:
            raise SupervisorSessionTerminatedError(
                session_id=self._session_id,
                state=self._state.value,
            )

        allowed = VALID_TRANSITIONS.get(self._state, frozenset())
        if to_state not in allowed:
            raise SupervisorInvalidTransitionError(
                from_state = self._state,
                to_state   = to_state,
                session_id = self._session_id,
            )

        from_state = self._state
        now        = time.time()

        self._state              = to_state
        self._updated_at         = now
        self._supervisor_version += 1

        self._state_history.append(
            SupervisorStateRecord(
                state      = to_state,
                entered_at = now,
                actor      = actor,
                reason     = reason,
            )
        )

        # Track start/end timestamps
        if to_state == SupervisorState.SUPERVISING and self._start_time is None:
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
    ) -> SupervisorTransition:
        """
        Convenience method — transition to FAILED and record the reason.
        """
        self._failure_reason = reason
        return self.transition_to(
            SupervisorState.FAILED,
            actor=actor,
            reason=reason,
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id":          self._session_id,
            "supervisor_id":       self._supervisor_id,
            "workflow_id":         self._workflow_id,
            "supervisor_scope":    self._supervisor_scope.value,
            "supervisor_type":     self._supervisor_type.value,
            "supervisor_priority": self._supervisor_priority.value,
            "supervisor_version":  self._supervisor_version,
            "state":               self._state.value,
            "failure_reason":      self._failure_reason,
            "created_at":          self._created_at,
            "updated_at":          self._updated_at,
            "start_time":          self._start_time,
            "end_time":            self._end_time,
            "duration_s":          self.duration_s,
            "is_active":           self.is_active,
            "is_terminal":         self.is_terminal,
            "is_successful":       self.is_successful,
            "transition_count":    len(self._transitions),
            "framework_version":   VERSION,
        }
