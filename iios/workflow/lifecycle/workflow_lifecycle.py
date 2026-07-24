"""
workflow_lifecycle.py — iios.workflow.lifecycle
------------------------------------------------
WorkflowLifecycle — the state machine manager.

Coordinates:
  - WorkflowRegistry            (active sessions)
  - WorkflowHistory             (immutable audit trail)
  - WorkflowLifecycleEventBus   (lifecycle events)
  - WorkflowLifecycleStatistics (7 counters)

DOES NOT execute workflows.  Manages lifecycle state transitions ONLY.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_LIFECYCLE,
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    WorkflowEventType,
    WorkflowLifecycleState,
)
from .exceptions import (
    WorkflowInvalidTransitionError,
    WorkflowSessionNotFoundError,
    WorkflowSessionTerminatedError,
)
from .workflow_events import WorkflowLifecycleEventBus
from .workflow_factory import WorkflowFactory
from .workflow_history import WorkflowHistory
from .workflow_metadata import WorkflowMetadata
from .workflow_registry import WorkflowRegistry
from .workflow_session import WorkflowSession
from .workflow_statistics import WorkflowLifecycleStatistics
from .workflow_transition import WorkflowTransition

_log = get_logger(__name__)


class WorkflowLifecycle:
    """
    Orchestration-free workflow lifecycle state machine.

    Provides one method per lifecycle transition.  Each method:
      1. Retrieves the session from the registry.
      2. Calls session.transition_to() which validates against VALID_TRANSITIONS.
      3. Records the transition in history.
      4. Updates statistics.
      5. Emits a typed lifecycle event.
      6. Returns the WorkflowTransition.
    """

    def __init__(
        self,
        registry:  Optional[WorkflowRegistry]              = None,
        history:   Optional[WorkflowHistory]               = None,
        event_bus: Optional[WorkflowLifecycleEventBus]     = None,
        stats:     Optional[WorkflowLifecycleStatistics]   = None,
    ) -> None:
        self._registry  = registry  or WorkflowRegistry()
        self._history   = history   or WorkflowHistory()
        self._event_bus = event_bus or WorkflowLifecycleEventBus()
        self._stats     = stats     or WorkflowLifecycleStatistics()
        self._factory   = WorkflowFactory()
        self._lock      = threading.Lock()

    # ----------------------------------------------------------------
    # Session creation
    # ----------------------------------------------------------------

    def create_session(
        self,
        workflow_id: str,
        *,
        metadata:   Optional[WorkflowMetadata] = None,
        session_id: Optional[str]              = None,
    ) -> WorkflowSession:
        """
        Create and register a new WorkflowSession in CREATED state.

        Args:
            workflow_id: Identifies the workflow definition.
            metadata:    Workflow metadata.  Defaults to WorkflowMetadata.default().
            session_id:  Custom session ID.  Auto-generated if not supplied.

        Returns:
            WorkflowSession in CREATED state.
        """
        session = self._factory.create(
            workflow_id, metadata=metadata, session_id=session_id
        )
        self._registry.register(session)
        self._stats.record_created()

        # Record initial state in history
        state_records = session.state_records()
        if state_records:
            self._history.record_state(state_records[0])

        self._event_bus.emit(
            WorkflowEventType.WORKFLOW_CREATED,
            session.session_id,
            WorkflowLifecycleState.CREATED,
            payload={"workflow_id": workflow_id},
        )
        _log.info(
            f"Workflow session created: id={session.session_id!r} "
            f"workflow={workflow_id!r}"
        )
        return session

    # ----------------------------------------------------------------
    # Private helper — apply a named transition
    # ----------------------------------------------------------------

    def _apply(
        self,
        session_id: str,
        to_state:   WorkflowLifecycleState,
        event_type: WorkflowEventType,
        actor:      str,
        reason:     str,
    ) -> WorkflowTransition:
        session = self._registry.get_or_raise(session_id)
        transition = session.transition_to(to_state, actor=actor, reason=reason)

        # Record in history
        self._history.record_transition(transition)
        state_records = session.state_records()
        if state_records:
            self._history.record_state(state_records[-1])

        self._event_bus.emit(
            event_type,
            session_id,
            to_state,
            payload={
                "transition_id": transition.transition_id,
                "from_state":    transition.from_state.value,
                "to_state":      transition.to_state.value,
                "reason":        reason,
            },
        )
        return transition

    # ----------------------------------------------------------------
    # Named transition methods
    # ----------------------------------------------------------------

    def initialize(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "initializing",
    ) -> WorkflowTransition:
        """CREATED → INITIALIZING"""
        return self._apply(
            session_id,
            WorkflowLifecycleState.INITIALIZING,
            WorkflowEventType.WORKFLOW_INITIALIZED,
            actor,
            reason,
        )

    def validate_workflow(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "validating",
    ) -> WorkflowTransition:
        """INITIALIZING → VALIDATING"""
        return self._apply(
            session_id,
            WorkflowLifecycleState.VALIDATING,
            WorkflowEventType.WORKFLOW_VALIDATED,
            actor,
            reason,
        )

    def mark_ready(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "ready",
    ) -> WorkflowTransition:
        """VALIDATING → READY"""
        return self._apply(
            session_id,
            WorkflowLifecycleState.READY,
            WorkflowEventType.WORKFLOW_VALIDATED,
            actor,
            reason,
        )

    def schedule(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "scheduled",
    ) -> WorkflowTransition:
        """READY → SCHEDULED"""
        return self._apply(
            session_id,
            WorkflowLifecycleState.SCHEDULED,
            WorkflowEventType.WORKFLOW_SCHEDULED,
            actor,
            reason,
        )

    def queue(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "queued",
    ) -> WorkflowTransition:
        """SCHEDULED/READY → QUEUED"""
        return self._apply(
            session_id,
            WorkflowLifecycleState.QUEUED,
            WorkflowEventType.WORKFLOW_SCHEDULED,
            actor,
            reason,
        )

    def start(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "started",
    ) -> WorkflowTransition:
        """QUEUED/READY → RUNNING"""
        transition = self._apply(
            session_id,
            WorkflowLifecycleState.RUNNING,
            WorkflowEventType.WORKFLOW_STARTED,
            actor,
            reason,
        )
        self._stats.record_started()
        return transition

    def wait(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "waiting",
    ) -> WorkflowTransition:
        """RUNNING → WAITING"""
        return self._apply(
            session_id,
            WorkflowLifecycleState.WAITING,
            WorkflowEventType.WORKFLOW_PAUSED,
            actor,
            reason,
        )

    def resume_from_wait(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "resuming from wait",
    ) -> WorkflowTransition:
        """WAITING → RUNNING"""
        return self._apply(
            session_id,
            WorkflowLifecycleState.RUNNING,
            WorkflowEventType.WORKFLOW_RESUMED,
            actor,
            reason,
        )

    def pause(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "paused",
    ) -> WorkflowTransition:
        """RUNNING/WAITING → PAUSED"""
        return self._apply(
            session_id,
            WorkflowLifecycleState.PAUSED,
            WorkflowEventType.WORKFLOW_PAUSED,
            actor,
            reason,
        )

    def resume(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "resuming",
    ) -> WorkflowTransition:
        """PAUSED → RESUMING"""
        return self._apply(
            session_id,
            WorkflowLifecycleState.RESUMING,
            WorkflowEventType.WORKFLOW_RESUMED,
            actor,
            reason,
        )

    def complete(
        self,
        session_id: str,
        *,
        runtime_ms:            float = 0.0,
        lifecycle_duration_ms: float = 0.0,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "completed",
    ) -> WorkflowTransition:
        """RUNNING/WAITING → COMPLETED"""
        transition = self._apply(
            session_id,
            WorkflowLifecycleState.COMPLETED,
            WorkflowEventType.WORKFLOW_COMPLETED,
            actor,
            reason,
        )
        self._stats.record_completed(
            runtime_ms=runtime_ms,
            lifecycle_duration_ms=lifecycle_duration_ms,
        )
        return transition

    def fail(
        self,
        session_id: str,
        *,
        lifecycle_duration_ms: float = 0.0,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "failed",
    ) -> WorkflowTransition:
        """Any active state → FAILED"""
        transition = self._apply(
            session_id,
            WorkflowLifecycleState.FAILED,
            WorkflowEventType.WORKFLOW_FAILED,
            actor,
            reason,
        )
        self._stats.record_failed(lifecycle_duration_ms=lifecycle_duration_ms)
        return transition

    def cancel(
        self,
        session_id: str,
        *,
        lifecycle_duration_ms: float = 0.0,
        actor:  str = ACTOR_OPERATOR,
        reason: str = "cancelled",
    ) -> WorkflowTransition:
        """Any non-terminal state → CANCELLED"""
        transition = self._apply(
            session_id,
            WorkflowLifecycleState.CANCELLED,
            WorkflowEventType.WORKFLOW_CANCELLED,
            actor,
            reason,
        )
        self._stats.record_cancelled(lifecycle_duration_ms=lifecycle_duration_ms)
        return transition

    def archive(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_SYSTEM,
        reason: str = "archived",
    ) -> WorkflowTransition:
        """COMPLETED/FAILED/CANCELLED → ARCHIVED"""
        return self._apply(
            session_id,
            WorkflowLifecycleState.ARCHIVED,
            WorkflowEventType.WORKFLOW_ARCHIVED,
            actor,
            reason,
        )

    def retry(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "retrying from failed",
    ) -> WorkflowTransition:
        """FAILED → INITIALIZING (retry path)"""
        return self._apply(
            session_id,
            WorkflowLifecycleState.INITIALIZING,
            WorkflowEventType.WORKFLOW_INITIALIZED,
            actor,
            reason,
        )

    # ----------------------------------------------------------------
    # Queries
    # ----------------------------------------------------------------

    def get_session(self, session_id: str) -> Optional[WorkflowSession]:
        return self._registry.get(session_id)

    def get_session_or_raise(self, session_id: str) -> WorkflowSession:
        return self._registry.get_or_raise(session_id)

    def list_sessions(self) -> List[WorkflowSession]:
        return self._registry.all_sessions()

    def sessions_by_state(
        self, state: WorkflowLifecycleState
    ) -> List[WorkflowSession]:
        return self._registry.by_state(state)

    def sessions_by_workflow(
        self, workflow_id: str
    ) -> List[WorkflowSession]:
        return self._registry.by_workflow(workflow_id)

    def statistics(self):
        return self._stats.report()

    def history(self) -> WorkflowHistory:
        return self._history

    def event_bus(self) -> WorkflowLifecycleEventBus:
        return self._event_bus

    def registry(self) -> WorkflowRegistry:
        return self._registry
