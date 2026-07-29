"""
memory_events.py -- iios.ai.memory_knowledge.events
=====================================================
Immutable event objects emitted by A4 components.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .event_types import MemoryEventType


@dataclass(frozen=True)
class MemoryEvent:
    """Base class for all A4 events."""
    event_id:   str
    event_type: MemoryEventType
    occurred_at: float


# ── Memory events ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MemoryCreatedEvent(MemoryEvent):
    entry_id: str = ""
    scope:    str = ""
    owner_id: str = ""

    @classmethod
    def create(cls, entry_id: str, scope: str, owner_id: str) -> "MemoryCreatedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = MemoryEventType.MEMORY_CREATED,
            occurred_at = time.time(),
            entry_id    = entry_id,
            scope       = scope,
            owner_id    = owner_id,
        )


@dataclass(frozen=True)
class MemoryUpdatedEvent(MemoryEvent):
    entry_id: str = ""
    version:  int = 0

    @classmethod
    def create(cls, entry_id: str, version: int) -> "MemoryUpdatedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = MemoryEventType.MEMORY_UPDATED,
            occurred_at = time.time(),
            entry_id    = entry_id,
            version     = version,
        )


@dataclass(frozen=True)
class MemoryExpiredEvent(MemoryEvent):
    entry_id: str = ""

    @classmethod
    def create(cls, entry_id: str) -> "MemoryExpiredEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = MemoryEventType.MEMORY_EXPIRED,
            occurred_at = time.time(),
            entry_id    = entry_id,
        )


@dataclass(frozen=True)
class MemoryDeletedEvent(MemoryEvent):
    entry_id: str = ""

    @classmethod
    def create(cls, entry_id: str) -> "MemoryDeletedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = MemoryEventType.MEMORY_DELETED,
            occurred_at = time.time(),
            entry_id    = entry_id,
        )


# ── Knowledge events ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class KnowledgeAddedEvent(MemoryEvent):
    item_id:  str = ""
    category: str = ""
    title:    str = ""

    @classmethod
    def create(cls, item_id: str, category: str, title: str) -> "KnowledgeAddedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = MemoryEventType.KNOWLEDGE_ADDED,
            occurred_at = time.time(),
            item_id     = item_id,
            category    = category,
            title       = title,
        )


@dataclass(frozen=True)
class KnowledgeRemovedEvent(MemoryEvent):
    item_id: str = ""

    @classmethod
    def create(cls, item_id: str) -> "KnowledgeRemovedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = MemoryEventType.KNOWLEDGE_REMOVED,
            occurred_at = time.time(),
            item_id     = item_id,
        )


@dataclass(frozen=True)
class KnowledgeUpdatedEvent(MemoryEvent):
    item_id: str = ""
    version: int = 0

    @classmethod
    def create(cls, item_id: str, version: int) -> "KnowledgeUpdatedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = MemoryEventType.KNOWLEDGE_UPDATED,
            occurred_at = time.time(),
            item_id     = item_id,
            version     = version,
        )


# ── Retrieval / ranking events ────────────────────────────────────────────────

@dataclass(frozen=True)
class RetrievalCompletedEvent(MemoryEvent):
    request_id:   str = ""
    result_count: int = 0
    strategy:     str = ""

    @classmethod
    def create(
        cls, request_id: str, result_count: int, strategy: str
    ) -> "RetrievalCompletedEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = MemoryEventType.RETRIEVAL_COMPLETED,
            occurred_at   = time.time(),
            request_id    = request_id,
            result_count  = result_count,
            strategy      = strategy,
        )


@dataclass(frozen=True)
class RankingCompletedEvent(MemoryEvent):
    request_id:   str = ""
    ranked_count: int = 0
    strategy:     str = ""

    @classmethod
    def create(
        cls, request_id: str, ranked_count: int, strategy: str
    ) -> "RankingCompletedEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = MemoryEventType.RANKING_COMPLETED,
            occurred_at   = time.time(),
            request_id    = request_id,
            ranked_count  = ranked_count,
            strategy      = strategy,
        )


@dataclass(frozen=True)
class GraphTraversedEvent(MemoryEvent):
    start_node_id: str = ""
    path_length:   int = 0

    @classmethod
    def create(cls, start_node_id: str, path_length: int) -> "GraphTraversedEvent":
        return cls(
            event_id       = str(uuid.uuid4()),
            event_type     = MemoryEventType.GRAPH_TRAVERSED,
            occurred_at    = time.time(),
            start_node_id  = start_node_id,
            path_length    = path_length,
        )
