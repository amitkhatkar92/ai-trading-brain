"""
workflow_session.py — iios.workflow.lifecycle
----------------------------------------------
WorkflowSession — the core entity tracking a workflow session's
lifecycle state.

Sessions are mutable (state transitions update them) and thread-safe.
The transition history records are immutable (frozen dataclasses).

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 1
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_LIFECYCLE,
    IMMUTABLE_STATES,
    VALID_TRANSITIONS,
    WorkflowLifecycleState,
)
from .exceptions import (
    WorkflowInvalidTransitionError,
    WorkflowSessionTerminatedError,
)
from .workflow_context import WorkflowContext
from .workflow_metadata import WorkflowMetadata
from .workflow_state import WorkflowStateRecord
from .workflow_transition import WorkflowTransition

_log = get_logger(__name__)


class WorkflowSession:
    """
    Mutable entity representing a workflow lifecycle session.

    Thread-safe.  State transitions are validated against VALID_TRANSITIONS.
    All transitions and state records are logged in append-only lists.
    """

    def __init__(
        self,
        session_id:  str,
        workflow_id: str,
        context:     WorkflowContext,
        metadata:    WorkflowMetadata,
    ) -> None:
        self._lock          = threading.Lock()
        self._session_id    = session_id
        self._workflow_id   = workflow_id
        self._context       = context
        self._metadata      = metadata
        self._state         = WorkflowLifecycleState.CREATED
        self._created_at    = datetime.now(tz=timezone.utc).isoformat()
        self._updated_at    = self._created_at
        self._transitions:   List[WorkflowTransition]  = []
        self._state_records: List[WorkflowStateRecord] = []

        # Record initial state
        initial_record = WorkflowStateRecord.create(
            session_id = self._session_id,
            state      = WorkflowLifecycleState.CREATED,
            actor      = ACTOR_LIFECYCLE,
            reason     = "session created",
        )
        self._state_records.append(initial_record)

    # ----------------------------------------------------------------
    # Properties (read-only access)
    # ----------------------------------------------------------------

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def context(self) -> WorkflowContext:
        return self._context

    @property
    def metadata(self) -> WorkflowMetadata:
        return self._metadata

    @property
    def state(self) -> WorkflowLifecycleState:
        with self._lock:
            return self._state

    @property
    def workflow_type(self):
        return self._metadata.workflow_type

    @property
    def workflow_priority(self):
        return self._metadata.workflow_priority

    @property
    def enterprise_id(self) -> str:
        return self._metadata.enterprise_id

    @property
    def owner_id(self) -> str:
        return self._metadata.owner_id

    @property
    def workflow_version(self) -> str:
        return self._metadata.workflow_version

    @property
    def created_at(self) -> str:
        return self._created_at

    @property
    def updated_at(self) -> str:
        with self._lock:
            return self._updated_at

    @property
    def is_active(self) -> bool:
        from .constants import ACTIVE_STATES
        with self._lock:
            return self._state in ACTIVE_STATES

    @property
    def is_terminal(self) -> bool:
        from .constants import TERMINAL_STATES
        with self._lock:
            return self._state in TERMINAL_STATES

    @property
    def is_archived(self) -> bool:
        with self._lock:
            return self._state == WorkflowLifecycleState.ARCHIVED

    # ----------------------------------------------------------------
    # State transition
    # ----------------------------------------------------------------

    def transition_to(
        self,
        to_state: WorkflowLifecycleState,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> WorkflowTransition:
        """
        Attempt a state transition.  Validates against VALID_TRANSITIONS.

        Returns:
            WorkflowTransition — immutable audit record.

        Raises:
            WorkflowSessionTerminatedError — if session is ARCHIVED.
            WorkflowInvalidTransitionError — if transition is not in the table.
        """
        with self._lock:
            current = self._state
            if current in IMMUTABLE_STATES:
                raise WorkflowSessionTerminatedError(self._session_id)
            permitted = VALID_TRANSITIONS.get(current, set())
            if to_state not in permitted:
                raise WorkflowInvalidTransitionError(
                    current.value, to_state.value
                )
            self._state      = to_state
            self._updated_at = datetime.now(tz=timezone.utc).isoformat()

            transition = WorkflowTransition.create(
                session_id = self._session_id,
                from_state = current,
                to_state   = to_state,
                actor      = actor,
                reason     = reason,
            )
            self._transitions.append(transition)

            state_record = WorkflowStateRecord.create(
                session_id = self._session_id,
                state      = to_state,
                actor      = actor,
                reason     = reason,
            )
            self._state_records.append(state_record)

        _log.debug(
            f"Workflow session {self._session_id!r}: "
            f"{current.value} → {to_state.value}"
        )
        return transition

    # ----------------------------------------------------------------
    # Read-only history access
    # ----------------------------------------------------------------

    def transitions(self) -> List[WorkflowTransition]:
        with self._lock:
            return list(self._transitions)

    def state_records(self) -> List[WorkflowStateRecord]:
        with self._lock:
            return list(self._state_records)

    def transition_count(self) -> int:
        with self._lock:
            return len(self._transitions)

    # ----------------------------------------------------------------
    # Serialisation
    # ----------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "session_id":  self._session_id,
                "workflow_id": self._workflow_id,
                "state":       self._state.value,
                "created_at":  self._created_at,
                "updated_at":  self._updated_at,
                "context":     self._context.to_dict(),
                "metadata":    self._metadata.to_dict(),
                "transitions": [t.to_dict() for t in self._transitions],
            }
