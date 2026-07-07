"""
iios/knowledge/search/index_builder.py
========================================
Builds indexes by converting domain objects (KnowledgeRecord, GraphNode)
into UnifiedSearchResult entries and passing them to IndexManager.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from .index_manager import IndexManager, get_index_manager
from .models.unified_result import UnifiedSearchResult
from .search_constants import ItemType

__all__ = ["IndexBuilder", "get_index_builder", "reset_index_builder"]

_LOG  = logging.getLogger("iios.knowledge.search.builder")
_lock = threading.Lock()
_builder: Optional["IndexBuilder"] = None


class IndexBuilder:
    """
    Bridges between domain objects and the IndexManager.

    Usage::

        builder = get_index_builder()
        builder.index_knowledge_record(record)
        builder.index_graph_node(node)

        # Full rebuild from repositories
        stats = builder.full_rebuild()
        print(stats["indexed_total"])
    """

    def __init__(self, index_manager: Optional[IndexManager] = None) -> None:
        self._mgr  = index_manager or get_index_manager()
        self._lock = threading.RLock()

    # ── Single-item indexing ──────────────────────────────────────────────────

    def index_knowledge_record(self, record: Any) -> bool:
        """Index a single KnowledgeRecord. Returns True on success."""
        try:
            if record.is_deleted:
                return self.deindex_item(record.id)
            result = UnifiedSearchResult.from_knowledge_record(record)
            self._mgr.index_item(result)
            return True
        except Exception as exc:
            _LOG.warning("Failed to index knowledge record %s: %s", getattr(record, "id", "?"), exc)
            return False

    def index_graph_node(self, node: Any) -> bool:
        """Index a single GraphNode. Returns True on success."""
        try:
            if node.is_deleted:
                return self.deindex_item(node.node_id)
            result = UnifiedSearchResult.from_graph_node(node)
            self._mgr.index_item(result)
            return True
        except Exception as exc:
            _LOG.warning("Failed to index graph node %s: %s", getattr(node, "node_id", "?"), exc)
            return False

    def deindex_item(self, item_id: str) -> bool:
        return self._mgr.deindex_item(item_id)

    # ── Bulk indexing from repositories ───────────────────────────────────────

    def build_from_knowledge_repository(self, repository: Any) -> int:
        """
        Index all non-deleted KnowledgeRecord objects from a KnowledgeRepository.
        Returns count of items indexed.
        """
        indexed = 0
        try:
            for record in repository.all():
                if not record.is_deleted:
                    if self.index_knowledge_record(record):
                        indexed += 1
        except Exception as exc:
            _LOG.error("Error indexing from knowledge repository: %s", exc)
        return indexed

    def build_from_graph_repository(self, repository: Any) -> int:
        """
        Index all active GraphNode objects from a GraphRepository.
        Returns count of items indexed.
        """
        indexed = 0
        try:
            for node in repository.all_nodes(include_deleted=False):
                if self.index_graph_node(node):
                    indexed += 1
        except Exception as exc:
            _LOG.error("Error indexing from graph repository: %s", exc)
        return indexed

    def full_rebuild(
        self,
        knowledge_repository: Optional[Any] = None,
        graph_repository:     Optional[Any] = None,
    ) -> dict[str, Any]:
        """
        Full index rebuild from both repositories.
        Clears the index first, then rebuilds.

        Returns stats dict with keys: indexed_knowledge, indexed_graph, indexed_total,
        build_time_ms.
        """
        start = time.perf_counter()
        self._mgr.clear()

        k_count = 0
        g_count = 0

        if knowledge_repository is None:
            try:
                from ..repositories.knowledge_repository import get_knowledge_repository
                knowledge_repository = get_knowledge_repository()
            except Exception:
                pass

        if graph_repository is None:
            try:
                from ..graph.storage.graph_repository import get_graph_repository
                graph_repository = get_graph_repository()
            except Exception:
                pass

        if knowledge_repository is not None:
            k_count = self.build_from_knowledge_repository(knowledge_repository)

        if graph_repository is not None:
            g_count = self.build_from_graph_repository(graph_repository)

        elapsed_ms = (time.perf_counter() - start) * 1000
        _LOG.info(
            "Full rebuild: %d knowledge + %d graph nodes in %.1f ms",
            k_count, g_count, elapsed_ms,
        )
        return {
            "indexed_knowledge": k_count,
            "indexed_graph":     g_count,
            "indexed_total":     k_count + g_count,
            "build_time_ms":     round(elapsed_ms, 3),
        }


def get_index_builder(
    index_manager: Optional[IndexManager] = None,
) -> IndexBuilder:
    global _builder
    with _lock:
        if _builder is None:
            _builder = IndexBuilder(index_manager)
        return _builder


def reset_index_builder() -> None:
    global _builder
    with _lock:
        _builder = None
