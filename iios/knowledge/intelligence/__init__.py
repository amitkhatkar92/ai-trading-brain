"""
__init__.py — iios.knowledge.intelligence
------------------------------------------
Public API surface for the Knowledge Intelligence Framework (C14 M4).

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

# ---- Constants & Enums -------------------------------------------------
from .constants import (
    ACTOR_INTELLIGENCE,
    ACTOR_SYSTEM,
    DEFAULT_EMBEDDING_DIMENSION,
    DEFAULT_MAX_EMBEDDINGS,
    DEFAULT_MAX_ENTITIES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_RELATIONSHIPS,
    DEFAULT_MAX_VECTORS,
    DEFAULT_TOP_K,
    INTELLIGENCE_SYSTEM_ID,
    SCHEMA_VERSION,
    VERSION,
    ClusteringAlgorithm,
    EntityType,
    IntelligenceEngineState,
    IntelligenceEventType,
    IntelligenceValidationCode,
    IntelligenceWorkflowType,
    RelationshipType,
    RetrievalMode,
    SimilarityMetric,
)

# ---- Exceptions --------------------------------------------------------
from .exceptions import (
    EmbeddingError,
    EnrichmentError,
    EntityResolutionError,
    IntelligenceCapacityError,
    IntelligenceNotRunningError,
    IntelligenceValidationError,
    KnowledgeGraphError,
    KnowledgeIntelligenceError,
    RetrievalError,
    VectorIndexError,
)

# ---- Domain objects ----------------------------------------------------
from .knowledge_graph_engine import (
    KnowledgeEntity,
    KnowledgeGraph,
    KnowledgeGraphAdapter,
    KnowledgeRelationship,
)
from .embedding_engine import (
    EmbeddingEngine,
    EmbeddingProvider,
    EmbeddingVector,
)
from .vector_index_engine import (
    VectorIndex,
    VectorIndexEngine,
    VectorSearchResult,
    VectorStoreAdapter,
)

# ---- Request / Response ------------------------------------------------
from .knowledge_intelligence_context import KnowledgeIntelligenceContext
from .knowledge_intelligence_request import KnowledgeIntelligenceRequest
from .knowledge_intelligence_response import (
    EnterpriseMemorySummary,
    KnowledgeIntelligenceReport,
    KnowledgeIntelligenceResponse,
    KnowledgeReasoningContext,
    KnowledgeRecommendationItem,
    KnowledgeRecommendationReport,
    KnowledgeRetrievalItem,
    KnowledgeRetrievalResult,
    KnowledgeSimilarityReport,
)

# ---- Sub-engines -------------------------------------------------------
from .knowledge_graph_builder import KnowledgeGraphBuilder
from .knowledge_graph_registry import KnowledgeGraphRegistry
from .entity_resolution_engine import EntityResolutionEngine, EntityExtractionAdapter
from .relationship_engine import RelationshipEngine, RelationshipDiscoveryAdapter
from .semantic_analysis_engine import SemanticAnalysisEngine, SemanticAnalysisAdapter
from .embedding_registry import EmbeddingRegistry
from .vector_store_manager import VectorStoreManager
from .retrieval_engine import RetrievalEngine
from .hybrid_search_engine import HybridSearchEngine
from .reranking_engine import RerankingEngine, RerankingAdapter
from .knowledge_similarity_engine import KnowledgeSimilarityEngine
from .knowledge_clustering_engine import KnowledgeClusteringEngine, ClusteringAdapter
from .knowledge_reasoning_engine import KnowledgeReasoningEngine
from .knowledge_enrichment_engine import KnowledgeEnrichmentEngine, EnrichmentAdapter
from .knowledge_memory_engine import KnowledgeMemoryEngine
from .knowledge_recommendation_engine import KnowledgeRecommendationEngine

# ---- Infrastructure ----------------------------------------------------
from .knowledge_intelligence_validator import (
    KnowledgeIntelligenceValidator,
    IntelligenceValidationReport,
    ValidationResult,
)
from .knowledge_intelligence_statistics import (
    KnowledgeIntelligenceStatistics,
    IntelligenceSnapshot,
)
from .knowledge_intelligence_history import KnowledgeIntelligenceHistory
from .knowledge_intelligence_events import (
    IntelligenceEvent,
    IntelligenceEventBus,
)
from .knowledge_intelligence_factory import KnowledgeIntelligenceFactory
from .knowledge_intelligence_registry import KnowledgeIntelligenceRegistry

# ---- Orchestration -----------------------------------------------------
from .knowledge_intelligence_manager import KnowledgeIntelligenceManager
from .knowledge_intelligence_engine import KnowledgeIntelligenceEngine

__all__ = [
    # Constants
    "INTELLIGENCE_SYSTEM_ID", "VERSION", "SCHEMA_VERSION",
    "ACTOR_INTELLIGENCE", "ACTOR_SYSTEM",
    "DEFAULT_EMBEDDING_DIMENSION", "DEFAULT_MAX_ENTITIES",
    "DEFAULT_MAX_RELATIONSHIPS", "DEFAULT_MAX_EMBEDDINGS",
    "DEFAULT_MAX_VECTORS", "DEFAULT_MAX_HISTORY", "DEFAULT_TOP_K",
    # Enums
    "IntelligenceEngineState", "IntelligenceWorkflowType",
    "EntityType", "RelationshipType", "RetrievalMode",
    "SimilarityMetric", "ClusteringAlgorithm",
    "IntelligenceEventType", "IntelligenceValidationCode",
    # Exceptions
    "KnowledgeIntelligenceError", "IntelligenceNotRunningError",
    "IntelligenceValidationError", "KnowledgeGraphError",
    "EntityResolutionError", "EmbeddingError", "VectorIndexError",
    "RetrievalError", "EnrichmentError", "IntelligenceCapacityError",
    # Domain objects
    "KnowledgeEntity", "KnowledgeRelationship", "KnowledgeGraph",
    "KnowledgeGraphAdapter",
    "EmbeddingVector", "EmbeddingProvider", "EmbeddingEngine",
    "VectorSearchResult", "VectorIndex", "VectorIndexEngine",
    "VectorStoreAdapter",
    # Request / Response
    "KnowledgeIntelligenceContext", "KnowledgeIntelligenceRequest",
    "KnowledgeRetrievalItem", "KnowledgeRetrievalResult",
    "KnowledgeSimilarityReport",
    "KnowledgeRecommendationItem", "KnowledgeRecommendationReport",
    "KnowledgeReasoningContext", "EnterpriseMemorySummary",
    "KnowledgeIntelligenceReport", "KnowledgeIntelligenceResponse",
    # Sub-engines
    "KnowledgeGraphBuilder", "KnowledgeGraphRegistry",
    "EntityResolutionEngine", "EntityExtractionAdapter",
    "RelationshipEngine", "RelationshipDiscoveryAdapter",
    "SemanticAnalysisEngine", "SemanticAnalysisAdapter",
    "EmbeddingRegistry", "VectorStoreManager",
    "RetrievalEngine", "HybridSearchEngine",
    "RerankingEngine", "RerankingAdapter",
    "KnowledgeSimilarityEngine",
    "KnowledgeClusteringEngine", "ClusteringAdapter",
    "KnowledgeReasoningEngine", "KnowledgeEnrichmentEngine",
    "EnrichmentAdapter", "KnowledgeMemoryEngine",
    "KnowledgeRecommendationEngine",
    # Infrastructure
    "ValidationResult", "IntelligenceValidationReport",
    "KnowledgeIntelligenceValidator",
    "IntelligenceSnapshot", "KnowledgeIntelligenceStatistics",
    "KnowledgeIntelligenceHistory",
    "IntelligenceEvent", "IntelligenceEventBus",
    "KnowledgeIntelligenceFactory", "KnowledgeIntelligenceRegistry",
    # Orchestration
    "KnowledgeIntelligenceManager", "KnowledgeIntelligenceEngine",
]
