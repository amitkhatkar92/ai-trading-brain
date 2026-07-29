"""
event_types.py -- iios.ai.memory_knowledge.events
==================================================
:class:`MemoryEventType` — all event types emitted by A4.
"""
from __future__ import annotations

from enum import Enum


class MemoryEventType(str, Enum):
    MEMORY_CREATED       = "memory.created"
    MEMORY_UPDATED       = "memory.updated"
    MEMORY_EXPIRED       = "memory.expired"
    MEMORY_DELETED       = "memory.deleted"
    KNOWLEDGE_ADDED      = "knowledge.added"
    KNOWLEDGE_REMOVED    = "knowledge.removed"
    KNOWLEDGE_UPDATED    = "knowledge.updated"
    RETRIEVAL_COMPLETED  = "retrieval.completed"
    RANKING_COMPLETED    = "ranking.completed"
    GRAPH_TRAVERSED      = "graph.traversed"
