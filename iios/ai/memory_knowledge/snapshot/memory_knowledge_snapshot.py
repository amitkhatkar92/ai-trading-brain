"""
memory_knowledge_snapshot.py -- iios.ai.memory_knowledge.snapshot
==================================================================
:class:`MemoryKnowledgeSnapshot` — immutable point-in-time capture of A4
module state.  Used for dashboards, health endpoints, and audits.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Optional

from ..events.event_bus          import MemoryEventBus
from ..graph.knowledge_graph     import KnowledgeGraph
from ..knowledge.knowledge_manager import KnowledgeManager
from ..memory.memory_manager       import MemoryManager


@dataclass(frozen=True)
class MemoryKnowledgeSnapshot:
    """Immutable snapshot of A4 Memory & Knowledge Platform state."""
    snapshot_id:        str
    captured_at:        float
    memory_count:       int
    knowledge_count:    int
    collection_count:   int
    graph_node_count:   int
    graph_rel_count:    int
    events_published:   int

    @property
    def taken_at(self) -> float:  # pragma: no cover  # deprecated alias
        """Deprecated: use captured_at."""
        return self.captured_at

    @classmethod
    def capture(
        cls,
        memory_manager:    MemoryManager,
        knowledge_manager: KnowledgeManager,
        knowledge_graph:   KnowledgeGraph,
        event_bus:         Optional[MemoryEventBus] = None,
    ) -> "MemoryKnowledgeSnapshot":
        return cls(
            snapshot_id      = str(uuid.uuid4()),
            captured_at      = time.time(),
            memory_count     = memory_manager.count(),
            knowledge_count  = knowledge_manager.count(),
            collection_count = len(knowledge_manager.list_collections()),
            graph_node_count = knowledge_graph.node_count(),
            graph_rel_count  = knowledge_graph.relationship_count(),
            events_published = event_bus.published_count if event_bus else 0,
        )
