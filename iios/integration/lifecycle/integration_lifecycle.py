"""
integration_lifecycle.py — iios.integration.lifecycle
------------------------------------------------------
IntegrationLifecycle — the state machine manager.

Coordinates:
  - IntegrationRegistry  (active sessions)
  - IntegrationHistory   (immutable audit trail)
  - IntegrationLifecycleEventBus (lifecycle events)
  - IntegrationLifecycleStatistics (6 counters)

DOES NOT orchestrate workflows.  Only manages lifecycle state transitions.

C15 Enterprise Integration & Connectivity — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_LIFECYCLE,
    ACTOR_SYSTEM,
    IntegrationEventType,
    IntegrationLifecycleState,
)
from .exceptions import (
    IntegrationInvalidTransitionError,
    IntegrationSessionNotFoundError,
    IntegrationSessionTerminatedError,
)
from .integration_events import IntegrationLifecycleEventBus
from .integration_factory import IntegrationFactory
from .integration_history import IntegrationHistory
from .integration_metadata import IntegrationMetadata
from .integration_registry import IntegrationRegistry
from .integration_session import IntegrationSession
from .integration_statistics import IntegrationLifecycleStatistics
from .integration_transition import IntegrationTransition

_log = get_logger(__name__)


class IntegrationLifecycle:
    """
    Orchestration-free lifecycle state machine.

    Provides one method per lifecycle event.  Each method:
      1. Retrieves the session from the registry.
      2. Calls session.transition_to() which validates against VALID_TRANSITIONS.
      3. Records the transition in history.
      4. Updates statistics.
      5. Emits a typed lifecycle event.
      6. Returns the IntegrationTransition.
    """

    def __init__(
        self,
        registry:  Optional[IntegrationRegistry]              = None,
        history:   Optional[IntegrationHistory]               = None,
        event_bus: Optional[IntegrationLifecycleEventBus]     = None,
        stats:     Optional[IntegrationLifecycleStatistics]   = None,
    ) -> None:
        self._registry  = registry  or IntegrationRegistry()
        self._history   = history   or IntegrationHistory()
        self._event_bus = event_bus or IntegrationLifecycleEventBus()
        self._stats     = stats     or IntegrationLifecycleStatistics()
        self._factory   = IntegrationFactory()
        self._lock      = threading.Lock()

    # ----------------------------------------------------------------
    # Session creation
    # ----------------------------------------------------------------

    def create_session(
        self,
        workflow_id: str,
        *,
        metadata:    Optional[IntegrationMetadata] = None,
        session_id:  Optional[str]                 = None,
    ) -> IntegrationSession:
        session = self._factory.create(
            workflow_id, metadata=metadata, session_id=session_id
        )
        self._registry.register(session)
        self._stats.record_created()
        self._event_bus.emit(
            IntegrationEventType.INTEGRATION_CREATED,
            session.session_id,
            IntegrationLifecycleState.CREATED,
            payload={"workflow_id": workflow_id},
        )
        _log.info(
            f"Integration session created: id={session.session_id!r} "
            f"workflow={workflow_id!r}"
        )
        return session

    # ----------------------------------------------------------------
    # Private helper — apply a transition
    # ----------------------------------------------------------------

    def _apply(
        self,
        session_id: str,
        to_state:   IntegrationLifecycleState,
        event_type: IntegrationEventType,
        actor:      str,
        reason:     str,
    ) -> IntegrationTransition:
        session = self._registry.get_or_raise(session_id)
        # raises IntegrationSessionTerminatedError / IntegrationInvalidTransitionError
        transition = session.transition_to(to_state, actor=actor, reason=reason)

        # Record in history (both transition and state record)
        self._history.record_transition(transition)
        if session.state_records():
            latest_sr = session.state_records()[-1]
            self._history.record_state(latest_sr)

        self._stats.record_transition()

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
    ) -> IntegrationTransition:
        return self._apply(
            session_id,
            IntegrationLifecycleState.INITIALIZING,
            IntegrationEventType.INTEGRATION_INITIALIZED,
            actor,
            reason,
        )

    def discover(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "discovering",
    ) -> IntegrationTransition:
        return self._apply(
            session_id,
            IntegrationLifecycleState.DISCOVERING,
            IntegrationEventType.INTEGRATION_INITIALIZED,
            actor,
            reason,
        )

    def configure(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "configuring",
    ) -> IntegrationTransition:
        return self._apply(
            session_id,
            IntegrationLifecycleState.CONFIGURING,
            IntegrationEventType.INTEGRATION_CONFIGURED,
            actor,
            reason,
        )

    def validate_session(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "validating",
    ) -> IntegrationTransition:
        return self._apply(
            session_id,
            IntegrationLifecycleState.VALIDATING,
            IntegrationEventType.INTEGRATION_VALIDATED,
            actor,
            reason,
        )

    def mark_ready(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "ready",
    ) -> IntegrationTransition:
        return self._apply(
            session_id,
            IntegrationLifecycleState.READY,
            IntegrationEventType.INTEGRATION_VALIDATED,
            actor,
            reason,
        )

    def connect(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "connecting",
    ) -> IntegrationTransition:
        return self._apply(
            session_id,
            IntegrationLifecycleState.CONNECTING,
            IntegrationEventType.INTEGRATION_CONNECTED,
            actor,
            reason,
        )

    def activate(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "activated",
    ) -> IntegrationTransition:
        return self._apply(
            session_id,
            IntegrationLifecycleState.ACTIVE,
            IntegrationEventType.INTEGRATION_ACTIVATED,
            actor,
            reason,
        )

    def pause(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "paused",
    ) -> IntegrationTransition:
        return self._apply(
            session_id,
            IntegrationLifecycleState.PAUSED,
            IntegrationEventType.INTEGRATION_PAUSED,
            actor,
            reason,
        )

    def resume(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "resuming",
    ) -> IntegrationTransition:
        return self._apply(
            session_id,
            IntegrationLifecycleState.RESUMING,
            IntegrationEventType.INTEGRATION_RESUMED,
            actor,
            reason,
        )

    def mark_resumed(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "resumed",
    ) -> IntegrationTransition:
        return self._apply(
            session_id,
            IntegrationLifecycleState.ACTIVE,
            IntegrationEventType.INTEGRATION_ACTIVATED,
            actor,
            reason,
        )

    def complete(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "completed",
    ) -> IntegrationTransition:
        transition = self._apply(
            session_id,
            IntegrationLifecycleState.COMPLETED,
            IntegrationEventType.INTEGRATION_COMPLETED,
            actor,
            reason,
        )
        self._stats.record_completed()
        return transition

    def fail(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_SYSTEM,
        reason: str = "failed",
    ) -> IntegrationTransition:
        transition = self._apply(
            session_id,
            IntegrationLifecycleState.FAILED,
            IntegrationEventType.INTEGRATION_FAILED,
            actor,
            reason,
        )
        self._stats.record_failed()
        _log.warning(
            f"Integration session failed: id={session_id!r} reason={reason!r}"
        )
        return transition

    def archive(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "archived",
    ) -> IntegrationTransition:
        transition = self._apply(
            session_id,
            IntegrationLifecycleState.ARCHIVED,
            IntegrationEventType.INTEGRATION_ARCHIVED,
            actor,
            reason,
        )
        self._stats.record_archived()
        return transition

    # ----------------------------------------------------------------
    # Retry — FAILED → INITIALIZING
    # ----------------------------------------------------------------

    def retry(
        self,
        session_id: str,
        *,
        actor:  str = ACTOR_SYSTEM,
        reason: str = "retry after failure",
    ) -> IntegrationTransition:
        return self._apply(
            session_id,
            IntegrationLifecycleState.INITIALIZING,
            IntegrationEventType.INTEGRATION_INITIALIZED,
            actor,
            reason,
        )

    # ----------------------------------------------------------------
    # Read-only access
    # ----------------------------------------------------------------

    def get_session(self, session_id: str) -> Optional[IntegrationSession]:
        return self._registry.get(session_id)

    def get_session_or_raise(self, session_id: str) -> IntegrationSession:
        return self._registry.get_or_raise(session_id)

    @property
    def registry(self) -> IntegrationRegistry:
        return self._registry

    @property
    def history(self) -> IntegrationHistory:
        return self._history

    @property
    def event_bus(self) -> IntegrationLifecycleEventBus:
        return self._event_bus

    @property
    def stats(self) -> IntegrationLifecycleStatistics:
        return self._stats

    # ----------------------------------------------------------------
    # Health
    # ----------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        report = self._stats.report()
        return {
            "status":         "healthy",
            "active_sessions": self._registry.count(),
            "stats":          report.to_dict(),
        }
