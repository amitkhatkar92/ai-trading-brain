"""
knowledge_enrichment_engine.py — iios.knowledge.intelligence
------------------------------------------------------------
Enriches knowledge artifacts with derived metadata fields.

Stub enrichment adds:
  - entity_count, relationship_count from the graph
  - keyword_count from semantic analysis
  - enriched_at timestamp

An EnrichmentAdapter Protocol allows injection of a domain-specific
enrichment pipeline.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from iios.common.logging.logging_manager import get_logger

from .knowledge_graph_engine import KnowledgeGraph
from .semantic_analysis_engine import SemanticAnalysisEngine

_log = get_logger(__name__)


@runtime_checkable
class EnrichmentAdapter(Protocol):
    """Protocol for domain-specific enrichment backends."""
    def enrich(
        self,
        artifact:     Dict[str, Any],
        graph:        KnowledgeGraph,
        semantic_ctx: Dict[str, Any],
    ) -> Dict[str, Any]: ...   # returns enriched artifact dict


class KnowledgeEnrichmentEngine:
    """
    Enriches artifacts with intelligence-derived metadata.

    Never modifies artifacts in-place; returns new enriched dicts.
    """

    def __init__(
        self,
        graph:          KnowledgeGraph,
        semantic_engine: SemanticAnalysisEngine,
        adapter:         Optional[EnrichmentAdapter] = None,
    ) -> None:
        self._graph   = graph
        self._semantic = semantic_engine
        self._adapter  = adapter

    def enrich(
        self,
        artifact: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Return enriched copy of artifact. Never raises."""
        try:
            text         = self._semantic.artifact_text(artifact)
            semantic_ctx = self._semantic.analyze(text)
            if self._adapter:
                return self._adapter.enrich(artifact, self._graph, semantic_ctx)
            return self._stub_enrich(artifact, semantic_ctx)
        except Exception as exc:
            _log.warning(f"Enrichment failed: {exc!r}")
            return dict(artifact)

    def enrich_batch(
        self,
        artifacts: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        return [self.enrich(a) for a in artifacts]

    def _stub_enrich(
        self,
        artifact:     Dict[str, Any],
        semantic_ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        enriched = dict(artifact)
        enriched["_enriched"] = {
            "entity_count":       self._graph.node_count,
            "relationship_count": self._graph.edge_count,
            "keyword_count":      len(semantic_ctx.get("keywords", [])),
            "enriched_at":        datetime.now(tz=timezone.utc).isoformat(),
        }
        return enriched

    def set_adapter(self, adapter: EnrichmentAdapter) -> None:
        self._adapter = adapter
        _log.info("EnrichmentAdapter registered")
