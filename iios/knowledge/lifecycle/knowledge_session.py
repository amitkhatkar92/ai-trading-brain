"""
knowledge_session.py — iios.knowledge.lifecycle
-------------------------------------------------
Primary domain object representing one knowledge lifecycle session.

A :class:`KnowledgeSession` tracks a knowledge artifact from creation through
archival, recording every state transition and timing information.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    ACTIVE_STATES,
    IMMUTABLE_STATES,
    SUCCESS_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    KnowledgeLifecycleState,
    KnowledgeScope,
    KnowledgeSource,
    KnowledgeType,
)
from .exceptions import (
    KnowledgeInvalidTransitionError,
    KnowledgeSessionTerminatedError,
)
from .knowledge_metadata import KnowledgeMetadata
from .knowledge_state import KnowledgeStateRecord
from .knowledge_transition import KnowledgeTransition


class KnowledgeSession:
    """
    Mutable domain object that tracks the lifecycle of a knowledge artifact.

    Fields
    ------
    session_id :     Unique session identifier.
    artifact_id :    Identifier of the knowledge artifact being managed.
    metadata :       Immutable :class:`KnowledgeMetadata` block.
    state :          Current :class:`KnowledgeLifecycleState`.
    failure_reason : Non-empty when the session is in FAILED state.
    created_at :     Wall-clock creation time.
    updated_at :     Wall-clock time of the most recent state change.
    start_time :     Wall-clock time when the session entered CAPTURING.
    end_time :       Wall-clock time when the session terminated.
    """

    def __init__(
        self,
        *,
        session_id:  Optional[str]             = None,
        artifact_id: str,
        metadata:    KnowledgeMetadata,
    ) -> None:
        self._session_id:     str                           = session_id or str(uuid.uuid4())
        self._artifact_id:    str                           = artifact_id
        self._metadata:       KnowledgeMetadata             = metadata
        self._state:          KnowledgeLifecycleState       = KnowledgeLifecycleState.CREATED
        self._failure_reason: str                           = ""
        self._created_at:     float                         = time.time()
        self._updated_at:     float                         = self._created_at
        self._start_time:     Optional[float]               = None
        self._end_time:       Optional[float]               = None
        self._state_history:  List[KnowledgeStateRecord]   = []
        self._transitions:    List[KnowledgeTransition]    = []

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def artifact_id(self) -> str:
        return self._artifact_id

    @property
    def metadata(self) -> KnowledgeMetadata:
        return self._metadata

    @property
    def state(self) -> KnowledgeLifecycleState:
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
    def state_history(self) -> List[KnowledgeStateRecord]:
        return list(self._state_history)

    @property
    def transitions(self) -> List[KnowledgeTransition]:
        return list(self._transitions)

    # Convenience derived properties
    @property
    def knowledge_type(self) -> KnowledgeType:
        return self._metadata.knowledge_type

    @property
    def knowledge_scope(self) -> KnowledgeScope:
        return self._metadata.knowledge_scope

    @property
    def knowledge_source(self) -> KnowledgeSource:
        return self._metadata.knowledge_source

    @property
    def knowledge_version(self) -> str:
        return self._metadata.knowledge_version

    @property
    def is_active(self) -> bool:
        return self._state in ACTIVE_STATES

    @property
    def is_terminal(self) -> bool:
        return self._state in TERMINAL_STATES

    @property
    def is_archived(self) -> bool:
        return self._state in IMMUTABLE_STATES

    @property
    def is_successful(self) -> bool:
        return self._state in SUCCESS_STATES

    @property
    def duration_seconds(self) -> Optional[float]:
        """Total lifecycle duration in seconds, or ``None`` if not yet ended."""
        if self._end_time is None:
            return None
        return self._end_time - self._created_at

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def transition_to(
        self,
        new_state: KnowledgeLifecycleState,
        actor:     str,
        *,
        reason:    str                      = "",
        metadata:  Optional[Dict[str, Any]] = None,
    ) -> KnowledgeTransition:
        """
        Perform a validated state transition.

        Raises
        ------
        KnowledgeSessionTerminatedError
            If the session is in an immutable (ARCHIVED) state.
        KnowledgeInvalidTransitionError
            If the requested transition is not valid from the current state.
        """
        if self._state in IMMUTABLE_STATES:
            raise KnowledgeSessionTerminatedError(
                f"Session {self._session_id!r} is archived and cannot transition"
            )

        allowed = VALID_TRANSITIONS.get(self._state, frozenset())
        if new_state not in allowed:
            raise KnowledgeInvalidTransitionError(
                from_state=self._state.value,
                to_state=new_state.value,
            )

        now = time.time()
        duration_ms = (now - self._updated_at) * 1_000.0

        transition = KnowledgeTransition.create(
            session_id  = self._session_id,
            from_state  = self._state,
            to_state    = new_state,
            actor       = actor,
            reason      = reason,
            duration_ms = duration_ms,
            metadata    = metadata,
        )
        self._transitions.append(transition)

        # Record state entry
        record = KnowledgeStateRecord.create(
            session_id = self._session_id,
            state      = new_state,
            actor      = actor,
            reason     = reason,
            metadata   = metadata,
        )
        self._state_history.append(record)

        prev_state   = self._state
        self._state  = new_state
        self._updated_at = now

        # Side-effects on specific transitions
        if new_state == KnowledgeLifecycleState.CAPTURING and prev_state not in (
            KnowledgeLifecycleState.RESUMING,
        ):
            self._start_time = now
        if new_state in TERMINAL_STATES:
            self._end_time = now
        if new_state == KnowledgeLifecycleState.FAILED:
            self._failure_reason = reason

        return transition

    def record_initial_state(self, actor: str) -> None:
        """Record the initial CREATED state to history (called by factory)."""
        record = KnowledgeStateRecord.create(
            session_id = self._session_id,
            state      = self._state,
            actor      = actor,
        )
        self._state_history.append(record)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id":     self._session_id,
            "artifact_id":    self._artifact_id,
            "metadata":       self._metadata.to_dict(),
            "state":          self._state.value,
            "failure_reason": self._failure_reason,
            "created_at":     self._created_at,
            "updated_at":     self._updated_at,
            "start_time":     self._start_time,
            "end_time":       self._end_time,
            "transition_count": len(self._transitions),
        }

    def __repr__(self) -> str:
        return (
            f"KnowledgeSession("
            f"session_id={self._session_id!r}, "
            f"artifact_id={self._artifact_id!r}, "
            f"state={self._state.value!r})"
        )
