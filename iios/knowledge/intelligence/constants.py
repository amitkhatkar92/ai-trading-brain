"""
constants.py — iios.knowledge.intelligence
===========================================
Enumerations, state machine, identifiers, and defaults for the
Institutional Knowledge Intelligence Framework.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from enum import Enum, IntEnum

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
INTELLIGENCE_SYSTEM_ID: str = "iios:knowledge:intelligence"
GRAPH_SYSTEM_ID:        str = "iios:knowledge:intelligence:graph"
EMBEDDING_SYSTEM_ID:    str = "iios:knowledge:intelligence:embedding"
VECTOR_SYSTEM_ID:       str = "iios:knowledge:intelligence:vector"
RETRIEVAL_SYSTEM_ID:    str = "iios:knowledge:intelligence:retrieval"
MEMORY_SYSTEM_ID:       str = "iios:knowledge:intelligence:memory"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Actor constants
# ---------------------------------------------------------------------------
ACTOR_INTELLIGENCE: str = "iios:knowledge:intelligence"
ACTOR_GRAPH:        str = "iios:knowledge:intelligence:graph"
ACTOR_EMBEDDING:    str = "iios:knowledge:intelligence:embedding"
ACTOR_RETRIEVAL:    str = "iios:knowledge:intelligence:retrieval"
ACTOR_SYSTEM:       str = "iios:system"

# ---------------------------------------------------------------------------
# Default limits
# ---------------------------------------------------------------------------
DEFAULT_EMBEDDING_DIMENSION: int = 128
DEFAULT_MAX_ENTITIES:        int = 100_000
DEFAULT_MAX_RELATIONSHIPS:   int = 500_000
DEFAULT_MAX_EMBEDDINGS:      int = 100_000
DEFAULT_MAX_VECTORS:         int = 100_000
DEFAULT_MAX_HISTORY:         int = 10_000
DEFAULT_TOP_K:               int = 10
DEFAULT_MAX_CLUSTERS:        int = 50
DEFAULT_MAX_RECOMMENDATIONS: int = 20


# ---------------------------------------------------------------------------
# IntelligenceEngineState — (12 states)
# ---------------------------------------------------------------------------
class IntelligenceEngineState(str, Enum):
    """Processing states of the Knowledge Intelligence Engine."""
    IDLE       = "idle"
    RECEIVING  = "receiving"
    VALIDATING = "validating"
    EXTRACTING = "extracting"
    BUILDING   = "building"
    EMBEDDING  = "embedding"
    INDEXING   = "indexing"
    ENRICHING  = "enriching"
    RETRIEVING = "retrieving"
    COMPLETED  = "completed"
    FAILED     = "failed"
    STOPPED    = "stopped"


# ---------------------------------------------------------------------------
# IntelligenceWorkflowType — (8 types)
# ---------------------------------------------------------------------------
class IntelligenceWorkflowType(str, Enum):
    """Supported knowledge intelligence workflow types."""
    FULL_INTELLIGENCE        = "full_intelligence"
    ENTITY_EXTRACTION        = "entity_extraction"
    RELATIONSHIP_DISCOVERY   = "relationship_discovery"
    EMBEDDING_GENERATION     = "embedding_generation"
    VECTOR_INDEXING          = "vector_indexing"
    SEMANTIC_RETRIEVAL       = "semantic_retrieval"
    KNOWLEDGE_ENRICHMENT     = "knowledge_enrichment"
    RECOMMENDATION_GENERATION = "recommendation_generation"


# ---------------------------------------------------------------------------
# EntityType — (12 types)
# ---------------------------------------------------------------------------
class EntityType(str, Enum):
    """Types of entities that can be extracted from knowledge artifacts."""
    CONCEPT   = "concept"
    METRIC    = "metric"
    EVENT     = "event"
    SIGNAL    = "signal"
    ASSET     = "asset"
    POSITION  = "position"
    RISK      = "risk"
    DECISION  = "decision"
    INSIGHT   = "insight"
    PATTERN   = "pattern"
    ANOMALY   = "anomaly"
    SYSTEM    = "system"


# ---------------------------------------------------------------------------
# RelationshipType — (12 types)
# ---------------------------------------------------------------------------
class RelationshipType(str, Enum):
    """Types of relationships between knowledge entities."""
    CAUSES         = "causes"
    CORRELATES_WITH = "correlates_with"
    PRECEDES       = "precedes"
    FOLLOWS        = "follows"
    CONTAINS       = "contains"
    BELONGS_TO     = "belongs_to"
    REFERENCES     = "references"
    IMPACTS        = "impacts"
    SIMILAR_TO     = "similar_to"
    OPPOSES        = "opposes"
    INFLUENCES     = "influences"
    TRIGGERS       = "triggers"


# ---------------------------------------------------------------------------
# RetrievalMode — (5 modes)
# ---------------------------------------------------------------------------
class RetrievalMode(str, Enum):
    """Modes of knowledge retrieval."""
    SEMANTIC       = "semantic"
    KEYWORD        = "keyword"
    HYBRID         = "hybrid"
    GRAPH          = "graph"
    RECOMMENDATION = "recommendation"


# ---------------------------------------------------------------------------
# SimilarityMetric — (5 metrics)
# ---------------------------------------------------------------------------
class SimilarityMetric(str, Enum):
    """Similarity metrics for knowledge vectors."""
    COSINE      = "cosine"
    DOT_PRODUCT = "dot_product"
    EUCLIDEAN   = "euclidean"
    MANHATTAN   = "manhattan"
    JACCARD     = "jaccard"


# ---------------------------------------------------------------------------
# ClusteringAlgorithm — (4 algorithms)
# ---------------------------------------------------------------------------
class ClusteringAlgorithm(str, Enum):
    """Supported clustering algorithms (adapter-pluggable)."""
    KMEANS       = "kmeans"
    HIERARCHICAL = "hierarchical"
    DBSCAN       = "dbscan"
    SPECTRAL     = "spectral"


# ---------------------------------------------------------------------------
# IntelligenceEventType — (10 event types)
# ---------------------------------------------------------------------------
class IntelligenceEventType(str, Enum):
    """Events emitted by the Knowledge Intelligence Framework."""
    KNOWLEDGE_RECEIVED              = "intelligence.knowledge_received"
    ENTITIES_EXTRACTED              = "intelligence.entities_extracted"
    RELATIONSHIPS_DISCOVERED        = "intelligence.relationships_discovered"
    KNOWLEDGE_GRAPH_UPDATED         = "intelligence.knowledge_graph_updated"
    EMBEDDINGS_GENERATED            = "intelligence.embeddings_generated"
    VECTOR_INDEX_UPDATED            = "intelligence.vector_index_updated"
    KNOWLEDGE_RETRIEVED             = "intelligence.knowledge_retrieved"
    KNOWLEDGE_ENRICHED              = "intelligence.knowledge_enriched"
    RECOMMENDATIONS_GENERATED       = "intelligence.recommendations_generated"
    KNOWLEDGE_INTELLIGENCE_COMPLETED = "intelligence.intelligence_completed"


# ---------------------------------------------------------------------------
# IntelligenceValidationCode — (8 codes)
# ---------------------------------------------------------------------------
class IntelligenceValidationCode(str, Enum):
    """Structural validation check codes."""
    KNOWLEDGE_CONSISTENCY  = "KNOWLEDGE_CONSISTENCY"
    ENTITY_INTEGRITY       = "ENTITY_INTEGRITY"
    RELATIONSHIP_INTEGRITY = "RELATIONSHIP_INTEGRITY"
    EMBEDDING_CONSISTENCY  = "EMBEDDING_CONSISTENCY"
    INDEX_INTEGRITY        = "INDEX_INTEGRITY"
    GRAPH_INTEGRITY        = "GRAPH_INTEGRITY"
    RETRIEVAL_QUALITY      = "RETRIEVAL_QUALITY"
    OUTPUT_COMPLETENESS    = "OUTPUT_COMPLETENESS"
