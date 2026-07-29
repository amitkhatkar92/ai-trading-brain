"""
memory_knowledge_gateway.py -- iios.ai.memory_knowledge.gateway
================================================================
:class:`MemoryKnowledgeGateway` — the single public entry point for A4.

All external AI Platform modules (A5+, orchestration, agents) interact
with A4 exclusively through this gateway.

Design
------
* Inherits ``AILifecycleAwareMixin`` (A1) — full lifecycle management.
* Owns a :class:`MemoryKnowledgeContainer` — DI composition root.
* Exposes a minimal, stable public API — this is the V1 contract for A4.

A4 Memory & Knowledge Platform  |  M6 Gateway
"""
from __future__ import annotations

import time
from typing import Any, Dict, FrozenSet, List, Optional

from iios.common.logging.logging_manager import get_logger

from ..container.memory_knowledge_container import MemoryKnowledgeContainer
from ..core.knowledge_category              import KnowledgeCategory
from ..core.knowledge_item                  import KnowledgeItem
from ..core.memory_entry                    import MemoryEntry
from ..core.memory_scope                    import MemoryScope
from ..events.event_bus                     import MemoryEventBus
from ..graph.knowledge_graph                import KnowledgeGraph
from ..graph.knowledge_node                 import KnowledgeNode
from ..graph.knowledge_path                 import KnowledgePath
from ..graph.knowledge_relationship         import KnowledgeRelationship
from ..knowledge.knowledge_collection       import KnowledgeCollection
from ..lifecycle                             import AILifecycleAwareMixin
from ..retrieval.retrieval_engine           import RetrievalEngine
from ..retrieval.retrieval_request          import RetrievalRequest
from ..retrieval.retrieval_result           import RetrievalResult
from ..snapshot.memory_knowledge_snapshot   import MemoryKnowledgeSnapshot

_log = get_logger(__name__)

SYSTEM_ID = "iios:ai:memory_knowledge:gateway"


class MemoryKnowledgeGateway(AILifecycleAwareMixin):
    """
    Single public entry point for the A4 Memory & Knowledge Platform.

    Usage::

        from iios.ai.memory_knowledge.gateway import MemoryKnowledgeGateway
        from iios.ai.memory_knowledge.core import MemoryScope, KnowledgeCategory

        gw = MemoryKnowledgeGateway()
        gw.initialize()
        gw.start()

        entry = gw.store_memory("market regime: bullish", scope=MemoryScope.SESSION)
        items = gw.search_knowledge("NIFTY analysis", top_k=5)
    """

    SYSTEM_ID: str = "iios:ai:memory_knowledge:gateway"
    VERSION:   str = "1.0.0"

    def __init__(
        self, container: Optional[MemoryKnowledgeContainer] = None
    ) -> None:
        self._container:  MemoryKnowledgeContainer = container or MemoryKnowledgeContainer()
        self._started_at: Optional[float]           = None

    # ── Lifecycle hooks ───────────────────────────────────────────────────────

    def _on_initialize(self) -> None:
        self._container.build()
        _log.info("MemoryKnowledgeGateway: container built")

    def _on_start(self) -> None:
        self._started_at = time.time()
        _log.info("MemoryKnowledgeGateway: started")

    def _on_stop(self) -> None:
        _log.info("MemoryKnowledgeGateway: stopped")

    # ── Memory API ────────────────────────────────────────────────────────────

    def store_memory(
        self,
        content:    Any,
        scope:      MemoryScope         = MemoryScope.SESSION,
        owner_id:   str                 = "system",
        tags:       FrozenSet[str]      = frozenset(),
        expires_at: Optional[float]     = None,
        source:     str                 = "",
        *,
        entry_id:   Optional[str]       = None,
    ) -> MemoryEntry:
        """Store a new memory entry; return the entry."""
        return self._container.memory_manager.store(
            content    = content,
            scope      = scope,
            owner_id   = owner_id,
            tags       = tags,
            expires_at = expires_at,
            source     = source,
            entry_id   = entry_id,
        )

    def retrieve_memory(self, entry_id: str) -> MemoryEntry:
        """Retrieve a specific memory entry by ID."""
        return self._container.memory_manager.retrieve(entry_id)

    def update_memory(self, entry_id: str, new_content: Any) -> MemoryEntry:
        """Update the content of an existing memory entry."""
        return self._container.memory_manager.update(entry_id, new_content)

    def delete_memory(self, entry_id: str) -> None:
        """Delete a memory entry."""
        self._container.memory_manager.delete(entry_id)

    def list_memory(
        self,
        *,
        scope:    Optional[MemoryScope] = None,
        owner_id: Optional[str]         = None,
        tags:     Optional[FrozenSet[str]] = None,
    ) -> List[MemoryEntry]:
        """List memory entries filtered by scope, owner, or tags."""
        mm = self._container.memory_manager
        if scope:
            return mm.retrieve_by_scope(scope)
        if owner_id:
            return mm.retrieve_by_owner(owner_id)
        if tags:
            return mm.retrieve_by_tags(tags)
        return mm.list_all()

    def evict_expired_memory(self) -> int:
        """Purge expired entries; return count evicted."""
        return self._container.memory_manager.evict_expired()

    # ── Knowledge API ─────────────────────────────────────────────────────────

    def add_knowledge(
        self,
        title:         str,
        content:       Any,
        category:      KnowledgeCategory   = KnowledgeCategory.DOCUMENT,
        tags:          FrozenSet[str]       = frozenset(),
        author:        str                  = "system",
        source:        str                  = "",
        language:      str                  = "en",
        collection_id: Optional[str]        = None,
        *,
        item_id:       Optional[str]        = None,
    ) -> KnowledgeItem:
        """Add a new knowledge item."""
        return self._container.knowledge_manager.add(
            title         = title,
            content       = content,
            category      = category,
            tags          = tags,
            author        = author,
            source        = source,
            language      = language,
            collection_id = collection_id,
            item_id       = item_id,
        )

    def remove_knowledge(self, item_id: str) -> None:
        """Remove a knowledge item."""
        self._container.knowledge_manager.remove(item_id)

    def update_knowledge(self, item_id: str, new_content: Any) -> KnowledgeItem:
        """Update the content of an existing knowledge item."""
        return self._container.knowledge_manager.update(item_id, new_content)

    def get_knowledge(self, item_id: str) -> KnowledgeItem:
        """Get a knowledge item by ID."""
        return self._container.knowledge_manager.get(item_id)

    def search_knowledge(
        self,
        query:    str,
        top_k:    int                          = 10,
        category: Optional[KnowledgeCategory]  = None,
        tags:     Optional[FrozenSet[str]]      = None,
    ) -> List[KnowledgeItem]:
        """
        Keyword search over the knowledge catalogue.
        Returns up to ``top_k`` items.
        """
        return self._container.knowledge_manager.search(
            category = category,
            tags     = tags,
            keyword  = query,
        )[:top_k]

    def list_knowledge(
        self,
        *,
        category: Optional[KnowledgeCategory] = None,
        tags:     Optional[FrozenSet[str]]     = None,
    ) -> List[KnowledgeItem]:
        """List knowledge items filtered by category or tags."""
        return self._container.knowledge_manager.search(
            category = category,
            tags     = tags,
        )

    # ── Retrieval API ─────────────────────────────────────────────────────────

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Execute a cross-store retrieval request."""
        return self._container.retrieval_engine.retrieve(request)

    # ── Collection API ────────────────────────────────────────────────────────

    def create_collection(
        self,
        name:          str,
        category:      KnowledgeCategory,
        description:   str              = "",
        tags:          FrozenSet[str]   = frozenset(),
        *,
        collection_id: Optional[str]    = None,
    ) -> KnowledgeCollection:
        """Create a knowledge collection."""
        return self._container.knowledge_manager.create_collection(
            name          = name,
            category      = category,
            description   = description,
            tags          = tags,
            collection_id = collection_id,
        )

    def list_collections(self) -> List[KnowledgeCollection]:
        """List all knowledge collections."""
        return self._container.knowledge_manager.list_collections()

    # ── Graph API ─────────────────────────────────────────────────────────────

    def add_graph_node(self, node: KnowledgeNode) -> None:
        """Add a node to the knowledge graph."""
        self._container.knowledge_graph.add_node(node)

    def add_graph_relationship(self, rel: KnowledgeRelationship) -> None:
        """Add a directed relationship to the knowledge graph."""
        self._container.knowledge_graph.add_relationship(rel)

    def get_graph_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """Return a knowledge graph node by ID."""
        return self._container.knowledge_graph.get_node(node_id)

    def shortest_path(
        self, start_id: str, end_id: str
    ) -> Optional[KnowledgePath]:
        """Find shortest path between two knowledge graph nodes."""
        return self._container.knowledge_graph.shortest_path(start_id, end_id)

    def traverse_graph(
        self, start_id: str, max_depth: int = 3
    ) -> List[KnowledgeNode]:
        """BFS traversal of the knowledge graph from a starting node."""
        return self._container.knowledge_graph.traverse_bfs(start_id, max_depth)

    # ── Observability ─────────────────────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        """Return a lightweight health summary."""
        c = self._container
        return {
            "system_id":       self.SYSTEM_ID,
            "version":         self.VERSION,
            "memory_entries":  c.memory_manager.count(),
            "knowledge_items": c.knowledge_manager.count(),
            "graph_nodes":     c.knowledge_graph.node_count(),
            "events_published": c.event_bus.published_count,
        }

    def status(self) -> Dict[str, Any]:
        """Return detailed status including uptime."""
        h = self.health()
        h["started_at"]  = self._started_at
        h["uptime_s"]    = (time.time() - self._started_at) if self._started_at else None
        return h

    def snapshot(self) -> MemoryKnowledgeSnapshot:
        """Capture an immutable point-in-time snapshot."""
        c = self._container
        return MemoryKnowledgeSnapshot.capture(
            memory_manager    = c.memory_manager,
            knowledge_manager = c.knowledge_manager,
            knowledge_graph   = c.knowledge_graph,
            event_bus         = c.event_bus,
        )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def event_bus(self) -> MemoryEventBus:
        return self._container.event_bus

    @property
    def container(self) -> MemoryKnowledgeContainer:
        return self._container
