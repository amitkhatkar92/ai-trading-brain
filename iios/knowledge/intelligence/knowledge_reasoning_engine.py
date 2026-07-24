"""
knowledge_reasoning_engine.py — iios.knowledge.intelligence
------------------------------------------------------------
Assembles a KnowledgeReasoningContext from graph and semantic analysis.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List

from iios.common.logging.logging_manager import get_logger

from .knowledge_graph_engine import KnowledgeGraph
from .knowledge_intelligence_response import KnowledgeReasoningContext
from .semantic_analysis_engine import SemanticAnalysisEngine

_log = get_logger(__name__)


class KnowledgeReasoningEngine:
    """
    Builds a structured reasoning context for a knowledge artifact.

    Aggregates:
      - Entities extracted from the knowledge graph
      - Relationships involving those entities
      - Graph summary (node/edge counts)
      - Semantic feature dict from SemanticAnalysisEngine
    """

    def __init__(
        self,
        graph:            KnowledgeGraph,
        semantic_engine:  SemanticAnalysisEngine,
    ) -> None:
        self._graph   = graph
        self._semantic = semantic_engine

    def build_context(
        self,
        knowledge_id: str,
        artifact:     Dict[str, Any] = None,
    ) -> KnowledgeReasoningContext:
        """Build a reasoning context. Never raises; returns empty context on error."""
        try:
            all_entities      = self._graph.all_entities()
            all_relationships = self._graph.all_relationships()

            entity_dicts = [e.to_dict() for e in all_entities]
            rel_dicts    = [r.to_dict() for r in all_relationships]

            graph_summary = {
                "graph_id":  self._graph.graph_id,
                "node_count": self._graph.node_count,
                "edge_count": self._graph.edge_count,
            }

            text = ""
            if artifact:
                text = self._semantic.artifact_text(artifact)
            semantic_ctx = self._semantic.analyze(text) if text else {}

            return KnowledgeReasoningContext.create(
                knowledge_id     = knowledge_id,
                entities         = entity_dicts,
                relationships    = rel_dicts,
                graph_summary    = graph_summary,
                semantic_context = semantic_ctx,
            )
        except Exception as exc:
            _log.warning(f"Reasoning context build failed: {exc!r}")
            return KnowledgeReasoningContext.create(
                knowledge_id = knowledge_id,
                entities     = [],
                relationships = [],
            )
