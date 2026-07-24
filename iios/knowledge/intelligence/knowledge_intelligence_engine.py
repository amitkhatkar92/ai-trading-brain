"""
knowledge_intelligence_engine.py — iios.knowledge.intelligence
---------------------------------------------------------------
Primary façade for the Knowledge Intelligence Framework.

Implements LifecycleAwareMixin; all external callers go through this class.

Public API:
    process(request)             → KnowledgeIntelligenceResponse
    retrieve(query, mode, top_k) → KnowledgeRetrievalResult
    recommend(knowledge_id)      → KnowledgeRecommendationReport
    get_graph()                  → KnowledgeGraph
    memory_summary()             → EnterpriseMemorySummary
    health()                     → dict
    status()                     → dict
    statistics()                 → IntelligenceSnapshot
    history(n)                   → List[KnowledgeIntelligenceResponse]
    set_embedding_provider(p)
    set_vector_adapter(a)
    add_listener(fn) / remove_listener(fn)

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import (
    ACTOR_SYSTEM,
    DEFAULT_TOP_K,
    INTELLIGENCE_SYSTEM_ID,
    VERSION,
    IntelligenceEngineState,
    RetrievalMode,
)
from .embedding_engine import EmbeddingEngine, EmbeddingProvider
from .embedding_registry import EmbeddingRegistry
from .entity_resolution_engine import EntityResolutionEngine
from .exceptions import IntelligenceNotRunningError
from .hybrid_search_engine import HybridSearchEngine
from .knowledge_clustering_engine import KnowledgeClusteringEngine
from .knowledge_enrichment_engine import KnowledgeEnrichmentEngine
from .knowledge_graph_builder import KnowledgeGraphBuilder
from .knowledge_graph_engine import KnowledgeGraph
from .knowledge_graph_registry import KnowledgeGraphRegistry
from .knowledge_intelligence_context import KnowledgeIntelligenceContext
from .knowledge_intelligence_events import IntelligenceEventBus
from .knowledge_intelligence_factory import KnowledgeIntelligenceFactory
from .knowledge_intelligence_history import KnowledgeIntelligenceHistory
from .knowledge_intelligence_manager import KnowledgeIntelligenceManager
from .knowledge_intelligence_registry import KnowledgeIntelligenceRegistry
from .knowledge_intelligence_request import KnowledgeIntelligenceRequest
from .knowledge_intelligence_response import (
    EnterpriseMemorySummary,
    KnowledgeIntelligenceResponse,
    KnowledgeRecommendationReport,
    KnowledgeRetrievalResult,
)
from .knowledge_intelligence_statistics import (
    IntelligenceSnapshot,
    KnowledgeIntelligenceStatistics,
)
from .knowledge_intelligence_validator import KnowledgeIntelligenceValidator
from .knowledge_memory_engine import KnowledgeMemoryEngine
from .knowledge_reasoning_engine import KnowledgeReasoningEngine
from .knowledge_recommendation_engine import KnowledgeRecommendationEngine
from .knowledge_similarity_engine import KnowledgeSimilarityEngine
from .relationship_engine import RelationshipEngine
from .reranking_engine import RerankingEngine
from .retrieval_engine import RetrievalEngine
from .semantic_analysis_engine import SemanticAnalysisEngine
from .vector_index_engine import VectorStoreAdapter
from .vector_store_manager import VectorStoreManager

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=INTELLIGENCE_SYSTEM_ID)


class KnowledgeIntelligenceEngine(LifecycleAwareMixin):
    """
    Primary façade for the Institutional Knowledge Intelligence Framework.

    Accepts KnowledgeIntelligenceRequest; delegates to
    KnowledgeIntelligenceManager for 11-phase processing.
    Emits lifecycle events and audit records on start/stop.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        graph:               KnowledgeGraph,
        graph_registry:      KnowledgeGraphRegistry,
        graph_builder:       KnowledgeGraphBuilder,
        embedding_engine:    EmbeddingEngine,
        embedding_registry:  EmbeddingRegistry,
        vector_store:        VectorStoreManager,
        entity_resolver:     EntityResolutionEngine,
        relationship_engine: RelationshipEngine,
        semantic_engine:     SemanticAnalysisEngine,
        retrieval_engine:    RetrievalEngine,
        hybrid_search:       HybridSearchEngine,
        reranker:            RerankingEngine,
        similarity_engine:   KnowledgeSimilarityEngine,
        clustering_engine:   KnowledgeClusteringEngine,
        reasoning_engine:    KnowledgeReasoningEngine,
        enrichment_engine:   KnowledgeEnrichmentEngine,
        memory_engine:       KnowledgeMemoryEngine,
        recommendation_engine: KnowledgeRecommendationEngine,
        validator:           KnowledgeIntelligenceValidator,
        statistics:          KnowledgeIntelligenceStatistics,
        history:             KnowledgeIntelligenceHistory,
        event_bus:           IntelligenceEventBus,
        registry:            KnowledgeIntelligenceRegistry,
        top_k:               int = DEFAULT_TOP_K,
    ) -> None:
        super().__init__()
        self._graph               = graph
        self._graph_registry      = graph_registry
        self._graph_builder       = graph_builder
        self._embedding_engine    = embedding_engine
        self._embedding_registry  = embedding_registry
        self._vector_store        = vector_store
        self._entity_resolver     = entity_resolver
        self._relationship_engine = relationship_engine
        self._semantic_engine     = semantic_engine
        self._retrieval_engine    = retrieval_engine
        self._hybrid_search       = hybrid_search
        self._reranker            = reranker
        self._similarity_engine   = similarity_engine
        self._clustering_engine   = clustering_engine
        self._reasoning_engine    = reasoning_engine
        self._enrichment_engine   = enrichment_engine
        self._memory_engine       = memory_engine
        self._recommendation_engine = recommendation_engine
        self._validator           = validator
        self._statistics          = statistics
        self._history             = history
        self._event_bus           = event_bus
        self._registry            = registry
        self._top_k               = top_k
        self._state               = IntelligenceEngineState.IDLE
        self._lock                = threading.Lock()
        self._manager: Optional[KnowledgeIntelligenceManager] = None

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            engine_id  = INTELLIGENCE_SYSTEM_ID,
            from_state = "stopped",
            to_state   = "running",
            version    = VERSION,
            actor      = ACTOR_SYSTEM,
        )
        self._manager = KnowledgeIntelligenceManager(
            graph                = self._graph,
            graph_builder        = self._graph_builder,
            embedding_engine     = self._embedding_engine,
            embedding_registry   = self._embedding_registry,
            vector_store         = self._vector_store,
            entity_resolver      = self._entity_resolver,
            relationship_engine  = self._relationship_engine,
            reasoning_engine     = self._reasoning_engine,
            enrichment_engine    = self._enrichment_engine,
            memory_engine        = self._memory_engine,
            recommendation_engine = self._recommendation_engine,
            validator            = self._validator,
            statistics           = self._statistics,
            history              = self._history,
            event_bus            = self._event_bus,
        )
        # Register the primary graph
        self._graph_registry.register(self._graph)
        _log.info(
            f"KnowledgeIntelligenceEngine started: "
            f"system={INTELLIGENCE_SYSTEM_ID!r} version={VERSION!r}"
        )

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            engine_id  = INTELLIGENCE_SYSTEM_ID,
            from_state = "running",
            to_state   = "stopped",
            version    = VERSION,
            actor      = ACTOR_SYSTEM,
        )
        self._manager = None
        _log.info("KnowledgeIntelligenceEngine stopped")

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------

    def _require_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise IntelligenceNotRunningError()

    # ------------------------------------------------------------------
    # Core processing
    # ------------------------------------------------------------------

    def process(
        self, request: KnowledgeIntelligenceRequest,
    ) -> KnowledgeIntelligenceResponse:
        """Process a knowledge intelligence request through 11 phases."""
        self._require_running()
        with self._lock:
            self._state = IntelligenceEngineState.RECEIVING
        try:
            response = self._manager.process(request)
            return response
        finally:
            with self._lock:
                self._state = (
                    IntelligenceEngineState.COMPLETED
                    if not False else IntelligenceEngineState.FAILED
                )

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        mode:  RetrievalMode = RetrievalMode.SEMANTIC,
        top_k: int           = 0,
    ) -> KnowledgeRetrievalResult:
        """Retrieve knowledge artifacts by query."""
        self._require_running()
        self._statistics.record_retrieval()
        k = top_k or self._top_k
        if mode == RetrievalMode.HYBRID:
            result = self._hybrid_search.search(query, k)
        else:
            result = self._retrieval_engine.retrieve(query, k)
        items = self._reranker.rerank(query, list(result.items))
        from .knowledge_intelligence_response import KnowledgeRetrievalResult as KRR
        return KRR.create(
            query        = result.query,
            items        = items,
            mode         = result.mode,
            retrieval_ms = result.retrieval_ms,
        )

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------

    def recommend(
        self,
        knowledge_id:       str,
        anchor_artifact_id: str = "",
        top_k:              int = 0,
    ) -> KnowledgeRecommendationReport:
        """Generate knowledge recommendations."""
        self._require_running()
        aid = anchor_artifact_id or knowledge_id
        return self._recommendation_engine.recommend(knowledge_id, aid, top_k)

    # ------------------------------------------------------------------
    # Graph
    # ------------------------------------------------------------------

    def get_graph(self) -> KnowledgeGraph:
        self._require_running()
        return self._graph

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    def memory_summary(self) -> EnterpriseMemorySummary:
        self._require_running()
        return self._memory_engine.summary()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        return {
            "status":        "healthy" if self.lifecycle_state().value == "running" else "stopped",
            "graph_nodes":   self._graph.node_count,
            "graph_edges":   self._graph.edge_count,
            "embeddings":    self._embedding_registry.count(),
            "vectors":       self._vector_store.count(),
            "version":       VERSION,
        }

    def status(self) -> Dict[str, Any]:
        snap = self._statistics.snapshot()
        return {
            "system_id":       INTELLIGENCE_SYSTEM_ID,
            "lifecycle_state": self.lifecycle_state().value,
            "engine_state":    self._state.value,
            "statistics":      snap.to_dict(),
            "history_count":   self._history.count(),
            "graph_nodes":     self._graph.node_count,
            "listeners":       self._event_bus.listener_count(),
        }

    def statistics(self) -> IntelligenceSnapshot:
        return self._statistics.snapshot()

    def history(self, n: int = 20) -> List[KnowledgeIntelligenceResponse]:
        return self._history.recent(n)

    def engine_state(self) -> IntelligenceEngineState:
        with self._lock:
            return self._state

    # ------------------------------------------------------------------
    # Adapter injection (runtime)
    # ------------------------------------------------------------------

    def set_embedding_provider(self, provider: EmbeddingProvider) -> None:
        self._embedding_engine.set_provider(provider)

    def set_vector_adapter(self, adapter: VectorStoreAdapter) -> None:
        self._vector_store.set_adapter(adapter)

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------

    def add_listener(self, fn: Callable) -> None:
        self._event_bus.add_listener(fn)

    def remove_listener(self, fn: Callable) -> None:
        self._event_bus.remove_listener(fn)

    # ------------------------------------------------------------------
    # M2 integration delegate
    # ------------------------------------------------------------------

    def process_for_dispatcher(
        self,
        knowledge_id: str,
        context:      Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Called by KnowledgeEngine (M2) intelligence_delegate.

        Accepts raw dict context and returns a status dict.
        """
        artifacts = context.get("artifacts", []) if context else []
        subsystem = context.get("subsystem_id", "unknown") if context else "unknown"
        request   = KnowledgeIntelligenceRequest.create(
            knowledge_id = knowledge_id,
            subsystem_id = subsystem,
            artifacts    = artifacts,
        )
        response = self.process(request)
        return response.to_dict()

    @property
    def intelligence_delegate(self):
        """Bound method for use as an M2 intelligence delegate."""
        return self.process_for_dispatcher

    # ------------------------------------------------------------------
    # Factory classmethod
    # ------------------------------------------------------------------

    @classmethod
    def create_default(cls) -> "KnowledgeIntelligenceEngine":
        """Create a fully-wired engine with default (stub) configuration."""
        factory = KnowledgeIntelligenceFactory()
        parts   = factory.build_all()
        return cls(
            graph               = parts["graph"],
            graph_registry      = parts["graph_registry"],
            graph_builder       = parts["graph_builder"],
            embedding_engine    = parts["embedding_engine"],
            embedding_registry  = parts["embedding_registry"],
            vector_store        = parts["vector_store"],
            entity_resolver     = parts["entity_resolver"],
            relationship_engine = parts["relationship_engine"],
            semantic_engine     = parts["semantic_engine"],
            retrieval_engine    = parts["retrieval_engine"],
            hybrid_search       = parts["hybrid_search"],
            reranker            = parts["reranker"],
            similarity_engine   = parts["similarity_engine"],
            clustering_engine   = parts["clustering_engine"],
            reasoning_engine    = parts["reasoning_engine"],
            enrichment_engine   = parts["enrichment_engine"],
            memory_engine       = parts["memory_engine"],
            recommendation_engine = parts["recommendation_engine"],
            validator           = parts["validator"],
            statistics          = parts["statistics"],
            history             = parts["history"],
            event_bus           = parts["event_bus"],
            registry            = parts["registry"],
        )
