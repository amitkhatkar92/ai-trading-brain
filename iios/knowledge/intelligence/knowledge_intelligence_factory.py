"""
knowledge_intelligence_factory.py — iios.knowledge.intelligence
----------------------------------------------------------------
Factory that constructs default-configured instances of all
Knowledge Intelligence Framework components.

All adapters default to None (stub mode).

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Optional

from .constants import (
    DEFAULT_EMBEDDING_DIMENSION,
    DEFAULT_MAX_EMBEDDINGS,
    DEFAULT_MAX_ENTITIES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_RELATIONSHIPS,
    DEFAULT_MAX_VECTORS,
    DEFAULT_TOP_K,
)
from .embedding_engine import EmbeddingEngine, EmbeddingProvider
from .embedding_registry import EmbeddingRegistry
from .entity_resolution_engine import EntityResolutionEngine
from .hybrid_search_engine import HybridSearchEngine
from .knowledge_clustering_engine import KnowledgeClusteringEngine
from .knowledge_enrichment_engine import KnowledgeEnrichmentEngine
from .knowledge_graph_builder import KnowledgeGraphBuilder
from .knowledge_graph_engine import KnowledgeGraph
from .knowledge_graph_registry import KnowledgeGraphRegistry
from .knowledge_intelligence_events import IntelligenceEventBus
from .knowledge_intelligence_history import KnowledgeIntelligenceHistory
from .knowledge_intelligence_registry import KnowledgeIntelligenceRegistry
from .knowledge_intelligence_statistics import KnowledgeIntelligenceStatistics
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


class KnowledgeIntelligenceFactory:
    """
    Constructs and wires all Knowledge Intelligence Framework components.

    Call build_*() methods to create individual components, or
    build_all() to obtain a fully wired component set.
    """

    def __init__(
        self,
        embedding_provider:   Optional[EmbeddingProvider]  = None,
        vector_store_adapter: Optional[VectorStoreAdapter]  = None,
        embedding_dimension:  int                          = DEFAULT_EMBEDDING_DIMENSION,
        max_entities:         int                          = DEFAULT_MAX_ENTITIES,
        max_relationships:    int                          = DEFAULT_MAX_RELATIONSHIPS,
        max_embeddings:       int                          = DEFAULT_MAX_EMBEDDINGS,
        max_vectors:          int                          = DEFAULT_MAX_VECTORS,
        max_history:          int                          = DEFAULT_MAX_HISTORY,
        top_k:                int                          = DEFAULT_TOP_K,
    ) -> None:
        self._embedding_provider   = embedding_provider
        self._vector_store_adapter = vector_store_adapter
        self._embedding_dimension  = embedding_dimension
        self._max_entities         = max_entities
        self._max_relationships    = max_relationships
        self._max_embeddings       = max_embeddings
        self._max_vectors          = max_vectors
        self._max_history          = max_history
        self._top_k                = top_k

    # ------------------------------------------------------------------
    # Individual builders
    # ------------------------------------------------------------------

    def build_graph(self) -> KnowledgeGraph:
        return KnowledgeGraph(
            max_entities  = self._max_entities,
            max_relations = self._max_relationships,
        )

    def build_graph_registry(self) -> KnowledgeGraphRegistry:
        return KnowledgeGraphRegistry()

    def build_graph_builder(self) -> KnowledgeGraphBuilder:
        return KnowledgeGraphBuilder()

    def build_embedding_engine(self) -> EmbeddingEngine:
        return EmbeddingEngine(
            provider  = self._embedding_provider,
            dimension = self._embedding_dimension,
        )

    def build_embedding_registry(self) -> EmbeddingRegistry:
        return EmbeddingRegistry(max_embeddings=self._max_embeddings)

    def build_vector_store(self) -> VectorStoreManager:
        return VectorStoreManager(
            adapter     = self._vector_store_adapter,
            max_vectors = self._max_vectors,
        )

    def build_entity_resolver(self) -> EntityResolutionEngine:
        return EntityResolutionEngine()

    def build_relationship_engine(self) -> RelationshipEngine:
        return RelationshipEngine()

    def build_semantic_engine(self) -> SemanticAnalysisEngine:
        return SemanticAnalysisEngine()

    def build_retrieval_engine(
        self,
        embedding_engine: EmbeddingEngine,
        vector_store:     VectorStoreManager,
    ) -> RetrievalEngine:
        return RetrievalEngine(
            embedding_engine = embedding_engine,
            vector_store     = vector_store,
            top_k            = self._top_k,
        )

    def build_hybrid_search(
        self,
        embedding_engine: EmbeddingEngine,
        vector_store:     VectorStoreManager,
    ) -> HybridSearchEngine:
        return HybridSearchEngine(
            embedding_engine = embedding_engine,
            vector_store     = vector_store,
            top_k            = self._top_k,
        )

    def build_reranker(self) -> RerankingEngine:
        return RerankingEngine()

    def build_similarity_engine(
        self,
        registry: EmbeddingRegistry,
    ) -> KnowledgeSimilarityEngine:
        return KnowledgeSimilarityEngine(registry=registry, top_k=self._top_k)

    def build_clustering_engine(
        self,
        registry: EmbeddingRegistry,
    ) -> KnowledgeClusteringEngine:
        return KnowledgeClusteringEngine(registry=registry)

    def build_reasoning_engine(
        self,
        graph:           KnowledgeGraph,
        semantic_engine: SemanticAnalysisEngine,
    ) -> KnowledgeReasoningEngine:
        return KnowledgeReasoningEngine(
            graph           = graph,
            semantic_engine = semantic_engine,
        )

    def build_enrichment_engine(
        self,
        graph:           KnowledgeGraph,
        semantic_engine: SemanticAnalysisEngine,
    ) -> KnowledgeEnrichmentEngine:
        return KnowledgeEnrichmentEngine(
            graph           = graph,
            semantic_engine = semantic_engine,
        )

    def build_memory_engine(
        self,
        graph:             KnowledgeGraph,
        embedding_registry: EmbeddingRegistry,
        vector_store:       VectorStoreManager,
    ) -> KnowledgeMemoryEngine:
        return KnowledgeMemoryEngine(
            graph              = graph,
            embedding_registry = embedding_registry,
            vector_store       = vector_store,
        )

    def build_recommendation_engine(
        self,
        similarity_engine: KnowledgeSimilarityEngine,
    ) -> KnowledgeRecommendationEngine:
        return KnowledgeRecommendationEngine(
            similarity_engine    = similarity_engine,
            max_recommendations  = self._top_k,
        )

    def build_validator(
        self,
        graph:             KnowledgeGraph,
        embedding_registry: EmbeddingRegistry,
        vector_store:       VectorStoreManager,
    ) -> KnowledgeIntelligenceValidator:
        return KnowledgeIntelligenceValidator(
            graph              = graph,
            embedding_registry = embedding_registry,
            vector_store       = vector_store,
        )

    def build_statistics(self) -> KnowledgeIntelligenceStatistics:
        return KnowledgeIntelligenceStatistics()

    def build_history(self) -> KnowledgeIntelligenceHistory:
        return KnowledgeIntelligenceHistory(max_history=self._max_history)

    def build_event_bus(self) -> IntelligenceEventBus:
        return IntelligenceEventBus()

    def build_registry(self) -> KnowledgeIntelligenceRegistry:
        return KnowledgeIntelligenceRegistry()

    # ------------------------------------------------------------------
    # Full wired set
    # ------------------------------------------------------------------

    def build_all(self) -> dict:
        """
        Construct and return all components in a dict.

        Keys match the constructor parameter names of
        KnowledgeIntelligenceEngine.
        """
        graph             = self.build_graph()
        graph_registry    = self.build_graph_registry()
        graph_builder     = self.build_graph_builder()
        emb_engine        = self.build_embedding_engine()
        emb_registry      = self.build_embedding_registry()
        vector_store      = self.build_vector_store()
        entity_resolver   = self.build_entity_resolver()
        relationship_eng  = self.build_relationship_engine()
        semantic_eng      = self.build_semantic_engine()
        retrieval_eng     = self.build_retrieval_engine(emb_engine, vector_store)
        hybrid_search     = self.build_hybrid_search(emb_engine, vector_store)
        reranker          = self.build_reranker()
        similarity_eng    = self.build_similarity_engine(emb_registry)
        clustering_eng    = self.build_clustering_engine(emb_registry)
        reasoning_eng     = self.build_reasoning_engine(graph, semantic_eng)
        enrichment_eng    = self.build_enrichment_engine(graph, semantic_eng)
        memory_eng        = self.build_memory_engine(graph, emb_registry, vector_store)
        recommendation_eng = self.build_recommendation_engine(similarity_eng)
        validator         = self.build_validator(graph, emb_registry, vector_store)
        statistics        = self.build_statistics()
        history           = self.build_history()
        event_bus         = self.build_event_bus()
        registry          = self.build_registry()

        return {
            "graph":              graph,
            "graph_registry":     graph_registry,
            "graph_builder":      graph_builder,
            "embedding_engine":   emb_engine,
            "embedding_registry": emb_registry,
            "vector_store":       vector_store,
            "entity_resolver":    entity_resolver,
            "relationship_engine": relationship_eng,
            "semantic_engine":    semantic_eng,
            "retrieval_engine":   retrieval_eng,
            "hybrid_search":      hybrid_search,
            "reranker":           reranker,
            "similarity_engine":  similarity_eng,
            "clustering_engine":  clustering_eng,
            "reasoning_engine":   reasoning_eng,
            "enrichment_engine":  enrichment_eng,
            "memory_engine":      memory_eng,
            "recommendation_engine": recommendation_eng,
            "validator":          validator,
            "statistics":         statistics,
            "history":            history,
            "event_bus":          event_bus,
            "registry":           registry,
        }
