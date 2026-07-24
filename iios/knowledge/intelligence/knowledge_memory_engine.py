"""
knowledge_memory_engine.py — iios.knowledge.intelligence
---------------------------------------------------------
Maintains enterprise memory: running aggregates of all intelligence.

Provides EnterpriseMemorySummary and tracks totals across processing cycles.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Any, Dict

from iios.common.logging.logging_manager import get_logger

from .embedding_registry import EmbeddingRegistry
from .knowledge_graph_engine import KnowledgeGraph
from .knowledge_intelligence_response import EnterpriseMemorySummary
from .vector_store_manager import VectorStoreManager

_log = get_logger(__name__)


class KnowledgeMemoryEngine:
    """
    Maintains the aggregate knowledge store state.

    Tracks: artifacts processed, entities, relationships, embeddings, vectors.
    Produces EnterpriseMemorySummary on demand.
    """

    def __init__(
        self,
        graph:             KnowledgeGraph,
        embedding_registry: EmbeddingRegistry,
        vector_store:       VectorStoreManager,
    ) -> None:
        self._graph             = graph
        self._embedding_registry = embedding_registry
        self._vector_store      = vector_store
        self._artifact_count    = 0
        self._lock              = threading.Lock()

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def record_artifacts(self, count: int) -> None:
        with self._lock:
            self._artifact_count += count

    def reset(self) -> None:
        with self._lock:
            self._artifact_count = 0

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> EnterpriseMemorySummary:
        """Build and return a current EnterpriseMemorySummary."""
        with self._lock:
            artifact_count = self._artifact_count
        return EnterpriseMemorySummary.create(
            total_artifacts     = artifact_count,
            total_entities      = self._graph.node_count,
            total_relationships = self._graph.edge_count,
            total_embeddings    = self._embedding_registry.count(),
            total_vectors       = self._vector_store.count(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.summary().to_dict()
