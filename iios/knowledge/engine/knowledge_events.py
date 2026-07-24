"""
knowledge_events.py — iios.knowledge.engine
---------------------------------------------
Domain events emitted by the Knowledge Engine subsystem.

9 event types:
  KnowledgeInitialized, KnowledgeCollectionStarted, KnowledgeCollected,
  KnowledgeValidated, KnowledgeClassified, KnowledgeDispatched,
  KnowledgePublished, KnowledgeCompleted, KnowledgeFailed

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .constants import (
    KnowledgeEventType,
    KnowledgeWorkflowType,
    EngineState,
)


@dataclass(frozen=True)
class KnowledgeEngineEvent:
    """
    Immutable domain event emitted by the Knowledge Engine.

    Fields
    ------
    event_id :     Unique event identifier.
    event_type :   Semantic event type.
    knowledge_id : Knowledge workflow run identifier.
    subsystem_id : Target subsystem identifier.
    pipeline_id :  Internal pipeline identifier.
    engine_state : Engine state at emission time.
    actor :        Identity that triggered the operation.
    occurred_at :  Wall-clock time the event occurred.
    reason :       Optional human-readable context.
    metadata :     Supplementary key-value metadata.
    """
    event_id:     str
    event_type:   KnowledgeEventType
    knowledge_id: str
    subsystem_id: str
    pipeline_id:  str
    engine_state: EngineState
    actor:        str
    occurred_at:  float          = field(default_factory=time.time)
    reason:       str            = ""
    metadata:     Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type:   KnowledgeEventType,
        knowledge_id: str,
        subsystem_id: str,
        pipeline_id:  str,
        engine_state: EngineState,
        actor:        str,
        *,
        event_id:     Optional[str]            = None,
        reason:       str                      = "",
        metadata:     Optional[Dict[str, Any]] = None,
    ) -> "KnowledgeEngineEvent":
        return cls(
            event_id     = event_id or str(uuid.uuid4()),
            event_type   = event_type,
            knowledge_id = knowledge_id,
            subsystem_id = subsystem_id,
            pipeline_id  = pipeline_id,
            engine_state = engine_state,
            actor        = actor,
            reason       = reason,
            metadata     = metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":     self.event_id,
            "event_type":   self.event_type.value,
            "knowledge_id": self.knowledge_id,
            "subsystem_id": self.subsystem_id,
            "pipeline_id":  self.pipeline_id,
            "engine_state": self.engine_state.value,
            "actor":        self.actor,
            "occurred_at":  self.occurred_at,
            "reason":       self.reason,
        }


# ---------------------------------------------------------------------------
# Event factory helpers
# ---------------------------------------------------------------------------

def _make_event(
    event_type:   KnowledgeEventType,
    knowledge_id: str,
    subsystem_id: str,
    pipeline_id:  str,
    engine_state: EngineState,
    actor:        str,
    reason:       str = "",
) -> KnowledgeEngineEvent:
    return KnowledgeEngineEvent.create(
        event_type   = event_type,
        knowledge_id = knowledge_id,
        subsystem_id = subsystem_id,
        pipeline_id  = pipeline_id,
        engine_state = engine_state,
        actor        = actor,
        reason       = reason,
    )


def make_knowledge_initialized(k, s, p, actor): return _make_event(KnowledgeEventType.KNOWLEDGE_INITIALIZED, k, s, p, EngineState.INITIALIZING, actor)
def make_knowledge_collection_started(k, s, p, actor): return _make_event(KnowledgeEventType.KNOWLEDGE_COLLECTION_STARTED, k, s, p, EngineState.COLLECTING, actor)
def make_knowledge_collected(k, s, p, actor): return _make_event(KnowledgeEventType.KNOWLEDGE_COLLECTED, k, s, p, EngineState.VALIDATING, actor)
def make_knowledge_validated(k, s, p, actor): return _make_event(KnowledgeEventType.KNOWLEDGE_VALIDATED, k, s, p, EngineState.CLASSIFYING, actor)
def make_knowledge_classified(k, s, p, actor): return _make_event(KnowledgeEventType.KNOWLEDGE_CLASSIFIED, k, s, p, EngineState.DISPATCHING, actor)
def make_knowledge_dispatched(k, s, p, actor): return _make_event(KnowledgeEventType.KNOWLEDGE_DISPATCHED, k, s, p, EngineState.PROCESSING, actor)
def make_knowledge_published(k, s, p, actor): return _make_event(KnowledgeEventType.KNOWLEDGE_PUBLISHED, k, s, p, EngineState.PUBLISHING, actor)
def make_knowledge_completed(k, s, p, actor): return _make_event(KnowledgeEventType.KNOWLEDGE_COMPLETED, k, s, p, EngineState.COMPLETED, actor)
def make_knowledge_failed(k, s, p, actor, reason=""): return _make_event(KnowledgeEventType.KNOWLEDGE_FAILED, k, s, p, EngineState.FAILED, actor, reason)


# ---------------------------------------------------------------------------
# Event bus
# ---------------------------------------------------------------------------

KnowledgeEngineEventListener = Callable[[KnowledgeEngineEvent], None]


class KnowledgeEngineEventBus:
    """
    Simple synchronous event bus for knowledge engine events.

    Listener exceptions are isolated so they do not affect other listeners.
    """

    def __init__(self) -> None:
        self._listeners: List[KnowledgeEngineEventListener] = []

    def add_listener(self, listener: KnowledgeEngineEventListener) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: KnowledgeEngineEventListener) -> bool:
        try:
            self._listeners.remove(listener)
            return True
        except ValueError:
            return False

    def listener_count(self) -> int:
        return len(self._listeners)

    def emit(self, event: KnowledgeEngineEvent) -> None:
        for listener in list(self._listeners):
            try:
                listener(event)
            except Exception:  # noqa: BLE001
                pass

    def clear(self) -> None:
        self._listeners.clear()
