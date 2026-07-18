"""iios/execution/recovery/lifecycle/recovery_session.py
==================================================
RecoverySession — core mutable domain object for a recovery lifecycle
session.

NOT a LifecycleAwareMixin; managed exclusively by RecoveryLifecycle.

C7 Execution Recovery & Resilience — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    ACTIVE_STATES,
    ACTOR_LIFECYCLE,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    RecoveryState,
    RecoveryTrigger,
    VERSION,
)
from .exceptions import RecoveryInvalidTransitionError, RecoverySessionTerminalError
from .recovery_state import RecoveryStateRecord
from .recovery_transition import RecoveryTransition, make_recovery_transition


class RecoverySession:
    """
    Core domain object representing a single execution recovery lifecycle.

    State transitions are validated against ``VALID_TRANSITIONS``.
    ``start_time`` is set on entering RECOVERING.
    ``end_time`` is set on entering COMPLETED, FAILED, or ABORTED.
    ``failure_reason`` is set when the session transitions to FAILED.
    ``abort_reason`` is set when the session transitions to ABORTED.
    """

    def __init__(
        self,
        *,
        session_id:           Optional[str]          = None,
        execution_session_id: str,
        subsystem_id:         str,
        recovery_trigger:     RecoveryTrigger         = RecoveryTrigger.AUTOMATIC,
        recovery_reason:      str                     = "",
        workflow_id:          Optional[str]           = None,
        failure_id:           Optional[str]           = None,
        recovery_plan_id:     Optional[str]           = None,
        recovery_version:     int                     = 1,
        metadata:             Optional[Dict[str, Any]]= None,
    ) -> None:
        self._session_id           = session_id or str(uuid.uuid4())
        self._execution_session_id = execution_session_id
        self._subsystem_id         = subsystem_id
        self._recovery_trigger     = recovery_trigger
        self._recovery_reason      = recovery_reason
        self._workflow_id          = workflow_id
        self._failure_id           = failure_id
        self._recovery_plan_id     = recovery_plan_id
        self._recovery_version     = recovery_version
        self._metadata             = dict(metadata or {})

        now                         = time.time()
        self._state                 = RecoveryState.CREATED
        self._start_time: Optional[float]  = None
        self._end_time:   Optional[float]  = None
        self._failure_reason: str          = ""
        self._abort_reason:   str          = ""
        self._created_at                   = now
        self._updated_at                   = now

        self._state_history: List[RecoveryStateRecord] = [
            RecoveryStateRecord(
                state      = RecoveryState.CREATED,
                entered_at = now,
                actor      = ACTOR_LIFECYCLE,
            )
        ]
        self._transitions: List[RecoveryTransition] = []

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def execution_session_id(self) -> str:
        return self._execution_session_id

    @property
    def subsystem_id(self) -> str:
        return self._subsystem_id

    @property
    def recovery_trigger(self) -> RecoveryTrigger:
        return self._recovery_trigger

    @property
    def recovery_reason(self) -> str:
        return self._recovery_reason

    @property
    def workflow_id(self) -> Optional[str]:
        return self._workflow_id

    @property
    def failure_id(self) -> Optional[str]:
        return self._failure_id

    @property
    def recovery_plan_id(self) -> Optional[str]:
        return self._recovery_plan_id

    @property
    def recovery_version(self) -> int:
        return self._recovery_version

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def state(self) -> RecoveryState:
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
    def abort_reason(self) -> str:
        return self._abort_reason

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    # ── Transition history ────────────────────────────────────────────────────

    @property
    def state_history(self) -> List[RecoveryStateRecord]:
        return list(self._state_history)

    @property
    def transitions(self) -> List[RecoveryTransition]:
        return list(self._transitions)

    @property
    def transition_count(self) -> int:
        return len(self._transitions)

    # ── Derived predicates ────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self._state in ACTIVE_STATES

    @property
    def is_terminal(self) -> bool:
        return self._state in TERMINAL_STATES

    @property
    def is_completed(self) -> bool:
        return self._state == RecoveryState.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self._state == RecoveryState.FAILED

    @property
    def is_aborted(self) -> bool:
        return self._state == RecoveryState.ABORTED

    @property
    def is_archived(self) -> bool:
        return self._state == RecoveryState.ARCHIVED

    @property
    def is_recovering(self) -> bool:
        return self._state == RecoveryState.RECOVERING

    @property
    def duration_ms(self) -> float:
        """
        Duration from RECOVERING (start_time) to end_time (or now).

        Returns 0.0 if recovery has not yet started.
        """
        if self._start_time is None:
            return 0.0
        end = self._end_time if self._end_time is not None else time.time()
        return max(0.0, (end - self._start_time) * 1_000)

    @property
    def age_ms(self) -> float:
        """Wall-time since session was created, in milliseconds."""
        return (time.time() - self._created_at) * 1_000

    # ── State machine ─────────────────────────────────────────────────────────

    def transition_to(
        self,
        new_state: RecoveryState,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> "RecoverySession":
        """
        Apply a state transition.

        Raises
        ------
        RecoverySessionTerminalError
            If the session is already in an immutable terminal state.
        RecoveryInvalidTransitionError
            If the transition is not permitted by the state machine.
        """
        from .constants import IMMUTABLE_STATES

        if self._state in IMMUTABLE_STATES:
            raise RecoverySessionTerminalError(self._session_id, self._state.value)

        allowed = VALID_TRANSITIONS.get(self._state, frozenset())
        if new_state not in allowed:
            raise RecoveryInvalidTransitionError(
                self._state.value, new_state.value, self._session_id
            )

        old_state = self._state
        now       = time.time()

        # Capture transition record
        self._transitions.append(
            make_recovery_transition(
                self._session_id,
                old_state,
                new_state,
                actor  = actor,
                reason = reason,
            )
        )
        # Append state record
        self._state_history.append(
            RecoveryStateRecord(
                state      = new_state,
                entered_at = now,
                actor      = actor,
                reason     = reason,
            )
        )

        # Milestone bookkeeping
        if new_state == RecoveryState.RECOVERING and self._start_time is None:
            self._start_time = now
        if new_state in (
            RecoveryState.COMPLETED,
            RecoveryState.FAILED,
            RecoveryState.ABORTED,
        ):
            self._end_time = now
        if new_state == RecoveryState.FAILED and reason:
            self._failure_reason = reason
        if new_state == RecoveryState.ABORTED and reason:
            self._abort_reason = reason

        self._state      = new_state
        self._updated_at = now
        return self

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id":           self._session_id,
            "execution_session_id": self._execution_session_id,
            "subsystem_id":         self._subsystem_id,
            "recovery_trigger":     self._recovery_trigger.value,
            "recovery_reason":      self._recovery_reason,
            "workflow_id":          self._workflow_id,
            "failure_id":           self._failure_id,
            "recovery_plan_id":     self._recovery_plan_id,
            "recovery_version":     self._recovery_version,
            "state":                self._state.value,
            "start_time":           self._start_time,
            "end_time":             self._end_time,
            "failure_reason":       self._failure_reason,
            "abort_reason":         self._abort_reason,
            "duration_ms":          self.duration_ms,
            "created_at":           self._created_at,
            "updated_at":           self._updated_at,
            "transition_count":     self.transition_count,
            "framework_version":    VERSION,
        }
