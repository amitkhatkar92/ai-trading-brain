"""
knowledge_intelligence_manager.py — iios.knowledge.intelligence
----------------------------------------------------------------
11-phase intelligence workflow orchestrator.

NEVER RAISES — all errors are caught, logged, and recorded in the
response.  Callers always receive a KnowledgeIntelligenceResponse.

Phase  1: Validate request
Phase  2: Extract entities
Phase  3: Resolve entity identities
Phase  4: Discover relationships
Phase  5: Build/update knowledge graph
Phase  6: Generate embeddings
Phase  7: Update vector indexes
Phase  8: Enrich knowledge
Phase  9: Build reasoning context
Phase 10: Generate recommendations
Phase 11: Return KnowledgeIntelligenceResponse

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from iios.common.logging.logging_manager import get_logger

from .constants import IntelligenceEventType, IntelligenceWorkflowType
from .embedding_engine import EmbeddingEngine
from .embedding_registry import EmbeddingRegistry
from .entity_resolution_engine import EntityResolutionEngine
from .knowledge_enrichment_engine import KnowledgeEnrichmentEngine
from .knowledge_graph_builder import KnowledgeGraphBuilder
from .knowledge_graph_engine import KnowledgeGraph
from .knowledge_intelligence_events import IntelligenceEventBus
from .knowledge_intelligence_history import KnowledgeIntelligenceHistory
from .knowledge_intelligence_request import KnowledgeIntelligenceRequest
from .knowledge_intelligence_response import (
    KnowledgeIntelligenceReport,
    KnowledgeIntelligenceResponse,
)
from .knowledge_intelligence_statistics import KnowledgeIntelligenceStatistics
from .knowledge_intelligence_validator import KnowledgeIntelligenceValidator
from .knowledge_memory_engine import KnowledgeMemoryEngine
from .knowledge_reasoning_engine import KnowledgeReasoningEngine
from .knowledge_recommendation_engine import KnowledgeRecommendationEngine
from .relationship_engine import RelationshipEngine
from .vector_store_manager import VectorStoreManager

_log = get_logger(__name__)


class KnowledgeIntelligenceManager:
    """
    Orchestrates the 11-phase knowledge intelligence workflow.

    NEVER RAISES.  All exceptions are caught and returned as failure
    KnowledgeIntelligenceResponse objects.
    """

    def __init__(
        self,
        graph:               KnowledgeGraph,
        graph_builder:       KnowledgeGraphBuilder,
        embedding_engine:    EmbeddingEngine,
        embedding_registry:  EmbeddingRegistry,
        vector_store:        VectorStoreManager,
        entity_resolver:     EntityResolutionEngine,
        relationship_engine: RelationshipEngine,
        reasoning_engine:    KnowledgeReasoningEngine,
        enrichment_engine:   KnowledgeEnrichmentEngine,
        memory_engine:       KnowledgeMemoryEngine,
        recommendation_engine: KnowledgeRecommendationEngine,
        validator:           KnowledgeIntelligenceValidator,
        statistics:          KnowledgeIntelligenceStatistics,
        history:             KnowledgeIntelligenceHistory,
        event_bus:           IntelligenceEventBus,
    ) -> None:
        self._graph               = graph
        self._graph_builder       = graph_builder
        self._embedding_engine    = embedding_engine
        self._embedding_registry  = embedding_registry
        self._vector_store        = vector_store
        self._entity_resolver     = entity_resolver
        self._relationship_engine = relationship_engine
        self._reasoning_engine    = reasoning_engine
        self._enrichment_engine   = enrichment_engine
        self._memory_engine       = memory_engine
        self._recommendation_engine = recommendation_engine
        self._validator           = validator
        self._statistics          = statistics
        self._history             = history
        self._event_bus           = event_bus

    # ------------------------------------------------------------------
    # Public — NEVER RAISES
    # ------------------------------------------------------------------

    def process(
        self, request: KnowledgeIntelligenceRequest,
    ) -> KnowledgeIntelligenceResponse:
        """Execute the full 11-phase intelligence pipeline."""
        t_start  = time.monotonic()
        errors:   List[str] = []
        warnings: List[str] = []

        try:
            # ─────────────────────────────────────────────────────────
            # Phase 1 — Validate
            # ─────────────────────────────────────────────────────────
            val_report = self._validator.validate(request)
            if not val_report.passed:
                failed = [r.message for r in val_report.results if not r.passed]
                return self._fail(
                    request, t_start, [f"Validation: {m}" for m in failed]
                )

            self._event_bus.emit(
                IntelligenceEventType.KNOWLEDGE_RECEIVED,
                {"knowledge_id": request.knowledge_id},
            )

            artifacts = list(request.artifacts)

            # ─────────────────────────────────────────────────────────
            # Phase 2 — Extract entities
            # ─────────────────────────────────────────────────────────
            entities = self._entity_resolver.extract_batch(artifacts)
            self._statistics.record_entities(len(entities))
            self._event_bus.emit(
                IntelligenceEventType.ENTITIES_EXTRACTED,
                {"count": len(entities), "knowledge_id": request.knowledge_id},
            )

            # ─────────────────────────────────────────────────────────
            # Phase 3 — Entity identity resolution (dedup by name)
            # Already done in extract_batch — pass through
            # ─────────────────────────────────────────────────────────

            # ─────────────────────────────────────────────────────────
            # Phase 4 — Discover relationships
            # ─────────────────────────────────────────────────────────
            relationships = self._relationship_engine.discover(entities)
            self._statistics.record_relationships(len(relationships))
            self._event_bus.emit(
                IntelligenceEventType.RELATIONSHIPS_DISCOVERED,
                {
                    "count":        len(relationships),
                    "knowledge_id": request.knowledge_id,
                },
            )

            # ─────────────────────────────────────────────────────────
            # Phase 5 — Build knowledge graph
            # ─────────────────────────────────────────────────────────
            self._graph_builder.build(self._graph, entities, relationships)
            self._statistics.record_graph_state(
                self._graph.node_count, self._graph.edge_count
            )
            self._event_bus.emit(
                IntelligenceEventType.KNOWLEDGE_GRAPH_UPDATED,
                {
                    "nodes": self._graph.node_count,
                    "edges": self._graph.edge_count,
                },
            )

            # ─────────────────────────────────────────────────────────
            # Phase 6 — Generate embeddings
            # ─────────────────────────────────────────────────────────
            embeddings_generated = 0
            for artifact in artifacts:
                art_id = artifact.get("artifact_id", f"art-{uuid.uuid4().hex[:8]}")
                try:
                    text = " ".join(
                        str(v) for v in artifact.values() if isinstance(v, (str, int, float))
                    )
                    emb = self._embedding_engine.generate(art_id, text)
                    self._embedding_registry.store(emb)
                    embeddings_generated += 1
                except Exception as exc:
                    warnings.append(f"Embedding skipped {art_id!r}: {exc!r}")

            self._statistics.record_embeddings(embeddings_generated)
            self._event_bus.emit(
                IntelligenceEventType.EMBEDDINGS_GENERATED,
                {"count": embeddings_generated},
            )

            # ─────────────────────────────────────────────────────────
            # Phase 7 — Update vector index
            # ─────────────────────────────────────────────────────────
            vectors_indexed = 0
            for art_id_key in self._embedding_registry.all_artifact_ids():
                emb = self._embedding_registry.get(art_id_key)
                if emb is None:
                    continue
                try:
                    self._vector_store.index_embedding(
                        emb, metadata={"artifact_id": art_id_key}
                    )
                    vectors_indexed += 1
                except Exception as exc:
                    warnings.append(f"Indexing skipped {art_id_key!r}: {exc!r}")

            self._statistics.record_vectors(vectors_indexed)
            self._event_bus.emit(
                IntelligenceEventType.VECTOR_INDEX_UPDATED,
                {"count": vectors_indexed},
            )

            # ─────────────────────────────────────────────────────────
            # Phase 8 — Enrich
            # ─────────────────────────────────────────────────────────
            enrichment_applied = False
            if request.workflow_type in (
                IntelligenceWorkflowType.FULL_INTELLIGENCE,
                IntelligenceWorkflowType.KNOWLEDGE_ENRICHMENT,
            ):
                try:
                    self._enrichment_engine.enrich_batch(artifacts)
                    self._statistics.record_enrichment(len(artifacts))
                    enrichment_applied = True
                    self._event_bus.emit(
                        IntelligenceEventType.KNOWLEDGE_ENRICHED,
                        {"artifact_count": len(artifacts)},
                    )
                except Exception as exc:
                    warnings.append(f"Enrichment failed: {exc!r}")

            # ─────────────────────────────────────────────────────────
            # Phase 9 — Build reasoning context
            # ─────────────────────────────────────────────────────────
            reasoning_ctx = None
            if artifacts:
                try:
                    reasoning_ctx = self._reasoning_engine.build_context(
                        knowledge_id = request.knowledge_id,
                        artifact     = artifacts[0],
                    )
                except Exception as exc:
                    warnings.append(f"Reasoning context failed: {exc!r}")

            # ─────────────────────────────────────────────────────────
            # Phase 10 — Recommendations
            # ─────────────────────────────────────────────────────────
            recommendations = None
            first_art_id = (
                artifacts[0].get("artifact_id") if artifacts else None
            )
            if first_art_id and request.workflow_type in (
                IntelligenceWorkflowType.FULL_INTELLIGENCE,
                IntelligenceWorkflowType.RECOMMENDATION_GENERATION,
            ):
                try:
                    recommendations = self._recommendation_engine.recommend(
                        knowledge_id        = request.knowledge_id,
                        anchor_artifact_id  = first_art_id,
                    )
                    self._statistics.record_recommendations(
                        len(recommendations.items)
                    )
                    self._event_bus.emit(
                        IntelligenceEventType.RECOMMENDATIONS_GENERATED,
                        {"count": len(recommendations.items)},
                    )
                except Exception as exc:
                    warnings.append(f"Recommendations failed: {exc!r}")

            # ─────────────────────────────────────────────────────────
            # Phase 11 — Build response
            # ─────────────────────────────────────────────────────────
            self._memory_engine.record_artifacts(len(artifacts))
            self._statistics.record_artifacts(len(artifacts))

            processing_ms = (time.monotonic() - t_start) * 1_000
            report = KnowledgeIntelligenceReport(
                report_id                = f"ir-{uuid.uuid4().hex[:10]}",
                knowledge_id             = request.knowledge_id,
                subsystem_id             = request.subsystem_id,
                workflow_type            = request.workflow_type,
                entities_extracted       = len(entities),
                relationships_discovered = len(relationships),
                embeddings_generated     = embeddings_generated,
                vectors_indexed          = vectors_indexed,
                reasoning_context        = reasoning_ctx,
                enrichment_applied       = enrichment_applied,
                recommendations          = recommendations,
                generated_at             = datetime.now(tz=timezone.utc).isoformat(),
            )

            response = KnowledgeIntelligenceResponse.success(
                request_id    = request.request_id,
                knowledge_id  = request.knowledge_id,
                report        = report,
                processing_ms = processing_ms,
                warnings      = warnings,
            )

            self._history.record(response)
            self._event_bus.emit(
                IntelligenceEventType.KNOWLEDGE_INTELLIGENCE_COMPLETED,
                {
                    "knowledge_id": request.knowledge_id,
                    "succeeded":    True,
                    "ms":           round(processing_ms, 2),
                },
            )
            _log.info(
                f"Intelligence completed: knowledge_id={request.knowledge_id!r} "
                f"entities={len(entities)} embeddings={embeddings_generated} "
                f"ms={processing_ms:.1f}"
            )
            return response

        except Exception as exc:
            _log.exception(
                f"Unexpected intelligence failure: knowledge_id={request.knowledge_id!r} "
                f"error={exc!r}"
            )
            return self._fail(request, t_start, [str(exc)], warnings)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fail(
        self,
        request:      KnowledgeIntelligenceRequest,
        t_start:      float,
        errors:       List[str],
        warnings:     List[str] = None,
    ) -> KnowledgeIntelligenceResponse:
        processing_ms = (time.monotonic() - t_start) * 1_000
        response = KnowledgeIntelligenceResponse.failure(
            request_id    = request.request_id,
            knowledge_id  = request.knowledge_id,
            errors        = errors,
            processing_ms = processing_ms,
            warnings      = warnings or [],
        )
        self._history.record(response)
        self._event_bus.emit(
            IntelligenceEventType.KNOWLEDGE_INTELLIGENCE_COMPLETED,
            {
                "knowledge_id": request.knowledge_id,
                "succeeded":    False,
                "errors":       errors,
            },
        )
        _log.warning(
            f"Intelligence failed: knowledge_id={request.knowledge_id!r} "
            f"errors={errors!r}"
        )
        return response
