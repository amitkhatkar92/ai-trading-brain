"""
knowledge_intelligence_response.py — iios.knowledge.intelligence
-----------------------------------------------------------------
All output value objects for the Knowledge Intelligence Framework:

    KnowledgeRetrievalItem
    KnowledgeRetrievalResult
    KnowledgeSimilarityReport
    KnowledgeRecommendationItem
    KnowledgeRecommendationReport
    KnowledgeReasoningContext
    EnterpriseMemorySummary
    KnowledgeIntelligenceReport
    KnowledgeIntelligenceResponse

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import IntelligenceWorkflowType, RetrievalMode, SimilarityMetric


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeRetrievalItem:
    """A single item returned from a retrieval query."""
    item_id:     str
    artifact_id: str
    score:       float
    metadata:    Dict[str, Any]
    rank:        int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id":     self.item_id,
            "artifact_id": self.artifact_id,
            "score":       self.score,
            "metadata":    self.metadata,
            "rank":        self.rank,
        }


@dataclass(frozen=True)
class KnowledgeRetrievalResult:
    """Aggregated output from a knowledge retrieval request."""
    result_id:    str
    query:        str
    items:        tuple          # Tuple[KnowledgeRetrievalItem]
    mode:         RetrievalMode
    total_results: int
    retrieval_ms: float
    retrieved_at: str

    @classmethod
    def create(
        cls,
        query:        str,
        items:        List[KnowledgeRetrievalItem],
        mode:         RetrievalMode,
        retrieval_ms: float = 0.0,
    ) -> "KnowledgeRetrievalResult":
        return cls(
            result_id    = f"ret-{uuid.uuid4().hex[:10]}",
            query        = query,
            items        = tuple(items),
            mode         = mode,
            total_results = len(items),
            retrieval_ms = retrieval_ms,
            retrieved_at = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":     self.result_id,
            "query":         self.query,
            "items":         [i.to_dict() for i in self.items],
            "mode":          self.mode.value,
            "total_results": self.total_results,
            "retrieval_ms":  self.retrieval_ms,
            "retrieved_at":  self.retrieved_at,
        }


# ---------------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeSimilarityReport:
    """Pairwise similarity analysis for an anchor artifact."""
    report_id:          str
    anchor_artifact_id: str
    similar_artifacts:  tuple          # Tuple[Dict[str, Any]]
    metric:             SimilarityMetric
    generated_at:       str

    @classmethod
    def create(
        cls,
        anchor_artifact_id: str,
        similar_artifacts:  List[Dict[str, Any]],
        metric:             SimilarityMetric = SimilarityMetric.COSINE,
    ) -> "KnowledgeSimilarityReport":
        return cls(
            report_id          = f"sim-{uuid.uuid4().hex[:10]}",
            anchor_artifact_id = anchor_artifact_id,
            similar_artifacts  = tuple(similar_artifacts),
            metric             = metric,
            generated_at       = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":          self.report_id,
            "anchor_artifact_id": self.anchor_artifact_id,
            "similar_artifacts":  list(self.similar_artifacts),
            "metric":             self.metric.value,
            "generated_at":       self.generated_at,
        }


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeRecommendationItem:
    """A single recommendation result."""
    item_id:         str
    artifact_id:     str
    relevance_score: float
    reason:          str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id":         self.item_id,
            "artifact_id":     self.artifact_id,
            "relevance_score": self.relevance_score,
            "reason":          self.reason,
        }


@dataclass(frozen=True)
class KnowledgeRecommendationReport:
    """Aggregated recommendations for a knowledge artifact."""
    report_id:    str
    knowledge_id: str
    items:        tuple          # Tuple[KnowledgeRecommendationItem]
    generated_at: str

    @classmethod
    def create(
        cls,
        knowledge_id: str,
        items:        List[KnowledgeRecommendationItem],
    ) -> "KnowledgeRecommendationReport":
        return cls(
            report_id    = f"rec-{uuid.uuid4().hex[:10]}",
            knowledge_id = knowledge_id,
            items        = tuple(items),
            generated_at = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":    self.report_id,
            "knowledge_id": self.knowledge_id,
            "items":        [i.to_dict() for i in self.items],
            "generated_at": self.generated_at,
        }


# ---------------------------------------------------------------------------
# Reasoning
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeReasoningContext:
    """Structured reasoning context assembled from graph + semantic analysis."""
    context_id:       str
    knowledge_id:     str
    entities:         tuple                # Tuple[Dict[str, Any]]
    relationships:    tuple                # Tuple[Dict[str, Any]]
    graph_summary:    Dict[str, Any]
    semantic_context: Dict[str, Any]
    generated_at:     str

    @classmethod
    def create(
        cls,
        knowledge_id:     str,
        entities:         list,
        relationships:    list,
        graph_summary:    Dict[str, Any] = None,
        semantic_context: Dict[str, Any] = None,
    ) -> "KnowledgeReasoningContext":
        return cls(
            context_id       = f"rc-{uuid.uuid4().hex[:10]}",
            knowledge_id     = knowledge_id,
            entities         = tuple(entities),
            relationships    = tuple(relationships),
            graph_summary    = dict(graph_summary or {}),
            semantic_context = dict(semantic_context or {}),
            generated_at     = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":       self.context_id,
            "knowledge_id":     self.knowledge_id,
            "entity_count":     len(self.entities),
            "relationship_count": len(self.relationships),
            "graph_summary":    self.graph_summary,
            "semantic_context": self.semantic_context,
            "generated_at":     self.generated_at,
        }


# ---------------------------------------------------------------------------
# Enterprise memory
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnterpriseMemorySummary:
    """Aggregate view of the intelligence knowledge store."""
    summary_id:           str
    total_artifacts:      int
    total_entities:       int
    total_relationships:  int
    total_embeddings:     int
    total_vectors:        int
    graph_density:        float   # edges / (nodes*(nodes-1)) or 0
    generated_at:         str

    @classmethod
    def create(
        cls,
        total_artifacts:     int   = 0,
        total_entities:      int   = 0,
        total_relationships: int   = 0,
        total_embeddings:    int   = 0,
        total_vectors:       int   = 0,
    ) -> "EnterpriseMemorySummary":
        n = total_entities
        graph_density = (
            total_relationships / (n * (n - 1)) if n > 1 else 0.0
        )
        return cls(
            summary_id          = f"mem-{uuid.uuid4().hex[:10]}",
            total_artifacts     = total_artifacts,
            total_entities      = total_entities,
            total_relationships = total_relationships,
            total_embeddings    = total_embeddings,
            total_vectors       = total_vectors,
            graph_density       = graph_density,
            generated_at        = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id":           self.summary_id,
            "total_artifacts":      self.total_artifacts,
            "total_entities":       self.total_entities,
            "total_relationships":  self.total_relationships,
            "total_embeddings":     self.total_embeddings,
            "total_vectors":        self.total_vectors,
            "graph_density":        self.graph_density,
            "generated_at":         self.generated_at,
        }


# ---------------------------------------------------------------------------
# Intelligence report & response
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeIntelligenceReport:
    """Full output of a knowledge intelligence workflow."""
    report_id:               str
    knowledge_id:            str
    subsystem_id:            str
    workflow_type:           IntelligenceWorkflowType
    entities_extracted:      int
    relationships_discovered: int
    embeddings_generated:    int
    vectors_indexed:         int
    reasoning_context:       Optional[KnowledgeReasoningContext]
    enrichment_applied:      bool
    recommendations:         Optional[KnowledgeRecommendationReport]
    generated_at:            str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":               self.report_id,
            "knowledge_id":            self.knowledge_id,
            "subsystem_id":            self.subsystem_id,
            "workflow_type":           self.workflow_type.value,
            "entities_extracted":      self.entities_extracted,
            "relationships_discovered": self.relationships_discovered,
            "embeddings_generated":    self.embeddings_generated,
            "vectors_indexed":         self.vectors_indexed,
            "reasoning_context":       (
                self.reasoning_context.to_dict()
                if self.reasoning_context else None
            ),
            "enrichment_applied":      self.enrichment_applied,
            "recommendations":         (
                self.recommendations.to_dict()
                if self.recommendations else None
            ),
            "generated_at":            self.generated_at,
        }


@dataclass(frozen=True)
class KnowledgeIntelligenceResponse:
    """Top-level response returned by the Knowledge Intelligence Engine."""
    response_id:   str
    request_id:    str
    knowledge_id:  str
    succeeded:     bool
    report:        Optional[KnowledgeIntelligenceReport]
    errors:        tuple      # Tuple[str]
    warnings:      tuple      # Tuple[str]
    processing_ms: float
    responded_at:  str

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def success(
        cls,
        request_id:    str,
        knowledge_id:  str,
        report:        KnowledgeIntelligenceReport,
        processing_ms: float = 0.0,
        warnings:      List[str] = None,
    ) -> "KnowledgeIntelligenceResponse":
        return cls(
            response_id   = f"resp-{uuid.uuid4().hex[:10]}",
            request_id    = request_id,
            knowledge_id  = knowledge_id,
            succeeded     = True,
            report        = report,
            errors        = (),
            warnings      = tuple(warnings or []),
            processing_ms = processing_ms,
            responded_at  = datetime.now(tz=timezone.utc).isoformat(),
        )

    @classmethod
    def failure(
        cls,
        request_id:    str,
        knowledge_id:  str,
        errors:        List[str],
        processing_ms: float = 0.0,
        warnings:      List[str] = None,
    ) -> "KnowledgeIntelligenceResponse":
        return cls(
            response_id   = f"resp-{uuid.uuid4().hex[:10]}",
            request_id    = request_id,
            knowledge_id  = knowledge_id,
            succeeded     = False,
            report        = None,
            errors        = tuple(errors),
            warnings      = tuple(warnings or []),
            processing_ms = processing_ms,
            responded_at  = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":   self.response_id,
            "request_id":    self.request_id,
            "knowledge_id":  self.knowledge_id,
            "succeeded":     self.succeeded,
            "report":        self.report.to_dict() if self.report else None,
            "errors":        list(self.errors),
            "warnings":      list(self.warnings),
            "processing_ms": self.processing_ms,
            "responded_at":  self.responded_at,
        }
