"""
knowledge_lifecycle.py — iios.knowledge.lifecycle
---------------------------------------------------
Primary public interface of the Knowledge Lifecycle subsystem.

:class:`KnowledgeLifecycle` is the ONLY interface external callers use to
manage knowledge session lifecycle.

Responsibilities
----------------
* Session creation
* State-transition orchestration across all 13 lifecycle states
* Event dispatch to registered listeners
* History and statistics accumulation
* Structural integrity validation

Non-Responsibilities (intentional exclusions)
---------------------------------------------
* Knowledge reasoning
* Knowledge retrieval or search
* Indexing or embedding generation
* AI optimization

C14 Enterprise Knowledge Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.errors.exceptions import IIOSError
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import (
    ACTOR_LIFECYCLE,
    ACTOR_OPERATOR,
    KnowledgeEventType,
    KnowledgeLifecycleState,
    KnowledgeScope,
    KnowledgeSource,
    KnowledgeType,
    LIFECYCLE_SYSTEM_ID,
    VERSION,
)
from .exceptions import (
    KnowledgeLifecycleNotRunningError,
    KnowledgeSessionNotFoundError,
)
from .knowledge_events import KnowledgeEvent, KnowledgeEventBus, KnowledgeEventListener
from .knowledge_factory import KnowledgeFactory
from .knowledge_history import KnowledgeHistory
from .knowledge_registry import KnowledgeRegistry
from .knowledge_session import KnowledgeSession
from .knowledge_statistics import KnowledgeStatistics
from .knowledge_validation import KnowledgeValidator


_STATE_TO_EVENT: Dict[KnowledgeLifecycleState, KnowledgeEventType] = {
    KnowledgeLifecycleState.INITIALIZING:     KnowledgeEventType.KNOWLEDGE_INITIALIZED,
    KnowledgeLifecycleState.CAPTURING:        KnowledgeEventType.KNOWLEDGE_CAPTURE_STARTED,
    KnowledgeLifecycleState.PUBLISHED:        KnowledgeEventType.KNOWLEDGE_PUBLISHED,
    KnowledgeLifecycleState.PAUSED:           KnowledgeEventType.KNOWLEDGE_PAUSED,
    KnowledgeLifecycleState.RESUMING:         KnowledgeEventType.KNOWLEDGE_RESUMED,
    KnowledgeLifecycleState.COMPLETED:        KnowledgeEventType.KNOWLEDGE_COMPLETED,
    KnowledgeLifecycleState.FAILED:           KnowledgeEventType.KNOWLEDGE_FAILED,
    KnowledgeLifecycleState.ARCHIVED:         KnowledgeEventType.KNOWLEDGE_ARCHIVED,
    KnowledgeLifecycleState.READY:            KnowledgeEventType.KNOWLEDGE_VALIDATED,
}


class KnowledgeLifecycle(LifecycleAwareMixin):
    """
    Primary façade for managing knowledge session lifecycle.

    Usage::

        lifecycle = KnowledgeLifecycle()
        lifecycle.start()

        session = lifecycle.create("art-001", KnowledgeType.FACT)
        lifecycle.initialize(session.session_id)
        lifecycle.collect(session.session_id)
        lifecycle.validate_session(session.session_id)
        lifecycle.mark_ready(session.session_id)
        lifecycle.start_capture(session.session_id)
        lifecycle.mark_indexing_pending(session.session_id)
        lifecycle.publish(session.session_id)
        lifecycle.complete(session.session_id)
        lifecycle.archive(session.session_id)

        lifecycle.stop()
    """

    def __init__(
        self,
        *,
        max_sessions: int = 5_000,
        max_archived: int = 10_000,
        max_history:  int = 1_000,
    ) -> None:
        super().__init__()
        self._registry   = KnowledgeRegistry(max_sessions=max_sessions, max_archived=max_archived)
        self._history    = KnowledgeHistory(max_entries=max_history)
        self._statistics = KnowledgeStatistics()
        self._factory    = KnowledgeFactory()
        self._validator  = KnowledgeValidator()
        self._event_bus  = KnowledgeEventBus()
        self._log        = get_logger(LIFECYCLE_SYSTEM_ID)
        self._audit      = get_audit_logger(__name__)
        self._lock       = threading.Lock()

    # ------------------------------------------------------------------
    # LifecycleAwareMixin hooks
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        self._log.info(f"KnowledgeLifecycle started — version={VERSION}")

    def _on_stop(self) -> None:
        self._log.info(f"KnowledgeLifecycle stopped")

    # ------------------------------------------------------------------
    # Guard helper
    # ------------------------------------------------------------------

    def _require_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise KnowledgeLifecycleNotRunningError()

    # ------------------------------------------------------------------
    # Session creation
    # ------------------------------------------------------------------

    def create(
        self,
        artifact_id:       str,
        knowledge_type:    KnowledgeType,
        *,
        session_id:        Optional[str]            = None,
        knowledge_scope:   KnowledgeScope           = KnowledgeScope.DOMAIN,
        knowledge_source:  KnowledgeSource          = KnowledgeSource.INTERNAL,
        knowledge_version: str                      = "1.0.0",
        author:            str                      = "",
        tags:              Optional[List[str]]       = None,
        description:       str                      = "",
        custom:            Optional[Dict[str, Any]] = None,
        actor:             str                      = ACTOR_LIFECYCLE,
    ) -> KnowledgeSession:
        """Create and register a new knowledge session in CREATED state."""
        self._require_running()

        session = self._factory.create(
            artifact_id       = artifact_id,
            knowledge_type    = knowledge_type,
            session_id        = session_id,
            knowledge_scope   = knowledge_scope,
            knowledge_source  = knowledge_source,
            knowledge_version = knowledge_version,
            author            = author,
            tags              = tags,
            description       = description,
            custom            = custom,
            actor             = actor,
        )
        self._registry.register(session)
        self._statistics.record_created()

        event = KnowledgeEvent.create(
            event_type  = KnowledgeEventType.KNOWLEDGE_CREATED,
            session_id  = session.session_id,
            artifact_id = session.artifact_id,
            state       = session.state,
            actor       = actor,
        )
        self._event_bus.emit(event)
        self._log.info(
            f"Knowledge session created: session_id={session.session_id!r} "
            f"artifact_id={artifact_id!r} type={knowledge_type.value!r}"
        )
        return session

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    def initialize(self, session_id: str, *, actor: str = ACTOR_LIFECYCLE) -> None:
        """Transition: CREATED → INITIALIZING"""
        self._transition(session_id, KnowledgeLifecycleState.INITIALIZING, actor)

    def collect(self, session_id: str, *, actor: str = ACTOR_LIFECYCLE) -> None:
        """Transition: INITIALIZING → COLLECTING"""
        self._transition(session_id, KnowledgeLifecycleState.COLLECTING, actor)

    def validate_session(self, session_id: str, *, actor: str = ACTOR_LIFECYCLE) -> None:
        """Transition: COLLECTING → VALIDATING"""
        self._transition(session_id, KnowledgeLifecycleState.VALIDATING, actor)

    def mark_ready(self, session_id: str, *, actor: str = ACTOR_LIFECYCLE) -> None:
        """Transition: VALIDATING → READY"""
        self._transition(session_id, KnowledgeLifecycleState.READY, actor)

    def start_capture(self, session_id: str, *, actor: str = ACTOR_LIFECYCLE) -> None:
        """Transition: READY → CAPTURING"""
        self._transition(session_id, KnowledgeLifecycleState.CAPTURING, actor)

    def mark_indexing_pending(self, session_id: str, *, actor: str = ACTOR_LIFECYCLE) -> None:
        """Transition: CAPTURING → INDEXING_PENDING"""
        self._transition(session_id, KnowledgeLifecycleState.INDEXING_PENDING, actor)

    def publish(self, session_id: str, *, actor: str = ACTOR_LIFECYCLE) -> None:
        """Transition: INDEXING_PENDING → PUBLISHED"""
        self._transition(session_id, KnowledgeLifecycleState.PUBLISHED, actor)

    def pause(self, session_id: str, *, actor: str = ACTOR_OPERATOR) -> None:
        """Transition: READY|PUBLISHED → PAUSED"""
        self._transition(session_id, KnowledgeLifecycleState.PAUSED, actor)

    def resume(self, session_id: str, *, actor: str = ACTOR_OPERATOR) -> None:
        """Transition: PAUSED → RESUMING"""
        self._transition(session_id, KnowledgeLifecycleState.RESUMING, actor)

    def mark_resumed(
        self,
        session_id: str,
        *,
        to_state: KnowledgeLifecycleState = KnowledgeLifecycleState.READY,
        actor:    str                     = ACTOR_LIFECYCLE,
    ) -> None:
        """Transition: RESUMING → CAPTURING | READY"""
        if to_state not in (
            KnowledgeLifecycleState.CAPTURING,
            KnowledgeLifecycleState.READY,
        ):
            to_state = KnowledgeLifecycleState.READY
        self._transition(session_id, to_state, actor)

    def complete(self, session_id: str, *, actor: str = ACTOR_LIFECYCLE) -> None:
        """Transition: PUBLISHED → COMPLETED"""
        self._transition(session_id, KnowledgeLifecycleState.COMPLETED, actor)
        self._statistics.record_completed()

    def fail(
        self,
        session_id: str,
        reason:     str = "",
        *,
        actor:      str = ACTOR_LIFECYCLE,
    ) -> None:
        """Transition: any non-terminal state → FAILED"""
        self._transition(session_id, KnowledgeLifecycleState.FAILED, actor, reason=reason)
        self._statistics.record_failed()

    def archive(self, session_id: str, *, actor: str = ACTOR_LIFECYCLE) -> None:
        """Transition: COMPLETED | FAILED | PAUSED → ARCHIVED"""
        session = self._registry.get(session_id)
        self._transition(session_id, KnowledgeLifecycleState.ARCHIVED, actor)
        self._registry.update(session)
        self._statistics.record_archived(duration_seconds=session.duration_seconds)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_session(self, session_id: str) -> KnowledgeSession:
        """Return the session or raise :class:`KnowledgeSessionNotFoundError`."""
        self._require_running()
        return self._registry.get(session_id)

    def health(self) -> Dict[str, Any]:
        """Return a health-check dictionary."""
        state = self.lifecycle_state().value
        stats = self._statistics.snapshot()
        return {
            "status":          "healthy" if state == "running" else "degraded",
            "lifecycle_state": state,
            "active_sessions": self._registry.active_count(),
            "archived_sessions": self._registry.archived_count(),
            "statistics":      stats,
        }

    def statistics(self) -> Dict[str, Any]:
        """Return a snapshot of all lifecycle statistics."""
        return self._statistics.snapshot()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(
        self, session_id: str, *, raise_on_failure: bool = False
    ) -> List[Any]:
        """Validate the structural integrity of a session."""
        self._require_running()
        session = self._registry.get(session_id)
        return self._validator.validate(session, raise_on_failure=raise_on_failure)

    # ------------------------------------------------------------------
    # Event listeners
    # ------------------------------------------------------------------

    def add_listener(self, listener: KnowledgeEventListener) -> None:
        self._event_bus.add_listener(listener)

    def remove_listener(self, listener: KnowledgeEventListener) -> bool:
        return self._event_bus.remove_listener(listener)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def history(self, *, session_id: Optional[str] = None, n: int = 20) -> List[Any]:
        """Return recent transition history, optionally filtered by session."""
        if session_id is not None:
            return self._history.for_session(session_id)
        return self._history.recent(n)

    # ------------------------------------------------------------------
    # Internal transition engine
    # ------------------------------------------------------------------

    def _transition(
        self,
        session_id: str,
        new_state:  KnowledgeLifecycleState,
        actor:      str,
        *,
        reason:     str = "",
    ) -> None:
        """Core state-transition logic (thread-safe per session_id)."""
        self._require_running()

        session    = self._registry.get(session_id)
        transition = session.transition_to(new_state, actor, reason=reason)

        self._history.record(transition)
        self._statistics.record_transition()

        event_type = _STATE_TO_EVENT.get(new_state)
        if event_type is not None:
            event = KnowledgeEvent.create(
                event_type  = event_type,
                session_id  = session.session_id,
                artifact_id = session.artifact_id,
                state       = new_state,
                actor       = actor,
                reason      = reason,
            )
            self._event_bus.emit(event)

        self._log.info(
            f"Knowledge session transitioned: session_id={session_id!r} "
            f"new_state={new_state.value!r} actor={actor!r}"
        )
