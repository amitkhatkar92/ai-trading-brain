"""
integration_session.py — iios.integration.lifecycle
----------------------------------------------------
IntegrationSession — the core entity tracking an enterprise integration
session's lifecycle state.

Sessions are mutable (state transitions update them) and thread-safe.
The transition history records are immutable (frozen dataclasses).

C15 Enterprise Integration & Connectivity — Phase 1, Module 1
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
    IntegrationLifecycleState,
)
from .exceptions import (
    IntegrationInvalidTransitionError,
    IntegrationSessionTerminatedError,
)
from .integration_context import IntegrationContext
from .integration_metadata import IntegrationMetadata
from .integration_state import IntegrationStateRecord
from .integration_transition import IntegrationTransition

_log = get_logger(__name__)


class IntegrationSession:
    """
    Mutable entity representing an enterprise integration session.

    Thread-safe.  State transitions are validated against VALID_TRANSITIONS.
    All transitions and state records are logged in append-only lists.
    """

    def __init__(
        self,
        session_id:  str,
        workflow_id: str,
        context:     IntegrationContext,
        metadata:    IntegrationMetadata,
    ) -> None:
        self._lock         = threading.Lock()
        self._session_id   = session_id
        self._workflow_id  = workflow_id
        self._context      = context
        self._metadata     = metadata
        self._state        = IntegrationLifecycleState.CREATED
        self._created_at   = datetime.now(tz=timezone.utc).isoformat()
        self._updated_at   = self._created_at
        self._transitions: List[IntegrationTransition] = []
        self._state_records: List[IntegrationStateRecord] = []

        # Record initial state
        initial_record = IntegrationStateRecord.create(
            session_id = self._session_id,
            state      = IntegrationLifecycleState.CREATED,
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
    def context(self) -> IntegrationContext:
        return self._context

    @property
    def metadata(self) -> IntegrationMetadata:
        return self._metadata

    @property
    def state(self) -> IntegrationLifecycleState:
        with self._lock:
            return self._state

    @property
    def integration_type(self):
        return self._metadata.integration_type

    @property
    def integration_scope(self):
        return self._metadata.integration_scope

    @property
    def provider(self) -> str:
        return self._metadata.provider

    @property
    def protocol(self) -> str:
        return self._metadata.protocol

    @property
    def integration_version(self) -> str:
        return self._metadata.integration_version

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
        with self._lock:
            return self._state in IMMUTABLE_STATES

    # ----------------------------------------------------------------
    # State machine
    # ----------------------------------------------------------------

    def can_transition_to(
        self, to_state: IntegrationLifecycleState
    ) -> bool:
        with self._lock:
            return to_state in VALID_TRANSITIONS.get(self._state, set())

    def transition_to(
        self,
        to_state: IntegrationLifecycleState,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> IntegrationTransition:
        """
        Perform a validated state transition.

        Raises:
            IntegrationSessionTerminatedError if session is archived.
            IntegrationInvalidTransitionError if transition is not valid.
        """
        with self._lock:
            if self._state in IMMUTABLE_STATES:
                raise IntegrationSessionTerminatedError(self._session_id)

            allowed = VALID_TRANSITIONS.get(self._state, set())
            if to_state not in allowed:
                raise IntegrationInvalidTransitionError(
                    self._state.value, to_state.value
                )

            from_state       = self._state
            self._state      = to_state
            self._updated_at = datetime.now(tz=timezone.utc).isoformat()

            transition = IntegrationTransition.create(
                session_id = self._session_id,
                from_state = from_state,
                to_state   = to_state,
                actor      = actor,
                reason     = reason,
            )
            self._transitions.append(transition)

            state_record = IntegrationStateRecord.create(
                session_id = self._session_id,
                state      = to_state,
                actor      = actor,
                reason     = reason,
            )
            self._state_records.append(state_record)

        _log.debug(
            f"Session transitioned: "
            f"id={self._session_id!r} "
            f"{from_state.value!r} → {to_state.value!r}"
        )
        return transition

    # ----------------------------------------------------------------
    # History access
    # ----------------------------------------------------------------

    def transitions(self) -> List[IntegrationTransition]:
        with self._lock:
            return list(self._transitions)

    def state_records(self) -> List[IntegrationStateRecord]:
        with self._lock:
            return list(self._state_records)

    def transition_count(self) -> int:
        with self._lock:
            return len(self._transitions)

    # ----------------------------------------------------------------
    # Serialization
    # ----------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "session_id":         self._session_id,
                "workflow_id":        self._workflow_id,
                "state":              self._state.value,
                "integration_type":   self._metadata.integration_type.value,
                "integration_scope":  self._metadata.integration_scope.value,
                "provider":           self._metadata.provider,
                "protocol":           self._metadata.protocol,
                "integration_version": self._metadata.integration_version,
                "created_at":         self._created_at,
                "updated_at":         self._updated_at,
                "context":            self._context.to_dict(),
                "metadata":           self._metadata.to_dict(),
                "transition_count":   len(self._transitions),
            }
