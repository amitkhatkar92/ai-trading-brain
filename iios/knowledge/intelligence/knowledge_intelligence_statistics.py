"""
knowledge_intelligence_statistics.py — iios.knowledge.intelligence
-------------------------------------------------------------------
Thread-safe statistics counters for the Knowledge Intelligence Framework.

Tracks 10 counters:
  1. artifacts_processed
  2. entities_extracted
  3. relationships_discovered
  4. graph_nodes
  5. graph_edges
  6. embeddings_generated
  7. vectors_indexed
  8. retrieval_requests
  9. recommendations_generated
 10. enrichment_operations

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class IntelligenceSnapshot:
    """Point-in-time snapshot of intelligence statistics."""
    artifacts_processed:      int
    entities_extracted:       int
    relationships_discovered: int
    graph_nodes:              int
    graph_edges:              int
    embeddings_generated:     int
    vectors_indexed:          int
    retrieval_requests:       int
    recommendations_generated: int
    enrichment_operations:    int
    captured_at:              str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifacts_processed":      self.artifacts_processed,
            "entities_extracted":       self.entities_extracted,
            "relationships_discovered": self.relationships_discovered,
            "graph_nodes":              self.graph_nodes,
            "graph_edges":              self.graph_edges,
            "embeddings_generated":     self.embeddings_generated,
            "vectors_indexed":          self.vectors_indexed,
            "retrieval_requests":       self.retrieval_requests,
            "recommendations_generated": self.recommendations_generated,
            "enrichment_operations":    self.enrichment_operations,
            "captured_at":              self.captured_at,
        }


class KnowledgeIntelligenceStatistics:
    """Thread-safe rolling statistics for the intelligence framework."""

    def __init__(self) -> None:
        self._lock                     = threading.Lock()
        self._artifacts_processed      = 0
        self._entities_extracted       = 0
        self._relationships_discovered = 0
        self._graph_nodes              = 0
        self._graph_edges              = 0
        self._embeddings_generated     = 0
        self._vectors_indexed          = 0
        self._retrieval_requests       = 0
        self._recommendations_generated = 0
        self._enrichment_operations    = 0

    # ------------------------------------------------------------------
    # Increment methods
    # ------------------------------------------------------------------

    def record_artifacts(self, n: int = 1) -> None:
        with self._lock:
            self._artifacts_processed += n

    def record_entities(self, n: int = 1) -> None:
        with self._lock:
            self._entities_extracted += n

    def record_relationships(self, n: int = 1) -> None:
        with self._lock:
            self._relationships_discovered += n

    def record_graph_state(self, nodes: int, edges: int) -> None:
        with self._lock:
            self._graph_nodes = nodes
            self._graph_edges = edges

    def record_embeddings(self, n: int = 1) -> None:
        with self._lock:
            self._embeddings_generated += n

    def record_vectors(self, n: int = 1) -> None:
        with self._lock:
            self._vectors_indexed += n

    def record_retrieval(self) -> None:
        with self._lock:
            self._retrieval_requests += 1

    def record_recommendations(self, n: int = 1) -> None:
        with self._lock:
            self._recommendations_generated += n

    def record_enrichment(self, n: int = 1) -> None:
        with self._lock:
            self._enrichment_operations += n

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> IntelligenceSnapshot:
        with self._lock:
            return IntelligenceSnapshot(
                artifacts_processed       = self._artifacts_processed,
                entities_extracted        = self._entities_extracted,
                relationships_discovered  = self._relationships_discovered,
                graph_nodes               = self._graph_nodes,
                graph_edges               = self._graph_edges,
                embeddings_generated      = self._embeddings_generated,
                vectors_indexed           = self._vectors_indexed,
                retrieval_requests        = self._retrieval_requests,
                recommendations_generated = self._recommendations_generated,
                enrichment_operations     = self._enrichment_operations,
                captured_at               = datetime.now(tz=timezone.utc).isoformat(),
            )

    def reset(self) -> None:
        with self._lock:
            self._artifacts_processed      = 0
            self._entities_extracted       = 0
            self._relationships_discovered = 0
            self._graph_nodes              = 0
            self._graph_edges              = 0
            self._embeddings_generated     = 0
            self._vectors_indexed          = 0
            self._retrieval_requests       = 0
            self._recommendations_generated = 0
            self._enrichment_operations    = 0
