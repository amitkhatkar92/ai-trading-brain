"""
iios.knowledge
================
Knowledge Engine — Wave 3 of the Investment Intelligence Operating System.

Provides:
- Typed knowledge records (facts, rules, concepts, patterns, strategies, …)
- Repository with transparent cache + multi-field index
- Full-text / keyword / tag / hybrid search
- Directed relationship graph with BFS / DFS / cycle-detection
- Snapshot-based versioning with rollback
- Structural validation, checksum integrity, constraint checking
- High-level KnowledgeManager façade and KnowledgeEngine lifecycle controller

Quick start::

    from iios.knowledge import get_knowledge_engine, get_knowledge_manager

    engine = get_knowledge_engine()
    engine.initialize()

    km = get_knowledge_manager()
    rec = km.create_fact("NIFTY 50 close", {"close": 24350.0})
    results = km.search("NIFTY close")

Architecture Reference: IIOS-MKA-001, IIOS-KON-001
Layer: KNOWLEDGE  |  Wave: 3  |  Owner: Platform
"""
from __future__ import annotations

# Constants
from .knowledge_constants import (
    KnowledgeType,
    KnowledgeStatus,
    KnowledgePriority,
    KnowledgeSource,
    KnowledgeDomain,
    VersionBump,
    VersionStatus,
    ValidationResult,
    ConstraintType,
    QueryOperator,
    SortOrder,
    SearchMode,
    RelationshipType,
    RelationshipStrength,
    IndexType,
    KnowledgeEvent,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    DEFAULT_CACHE_TTL,
    DEFAULT_CONFIDENCE,
    KNOWLEDGE_NAMESPACE,
    SYSTEM_OWNER,
)

# Exceptions
from .knowledge_exceptions import (
    KnowledgeError,
    KnowledgeNotFoundError,
    KnowledgeAlreadyExistsError,
    KnowledgeValidationError,
    KnowledgeVersionError,
    KnowledgeStorageError,
    KnowledgeSearchError,
    KnowledgeGraphError,
    KnowledgeRelationshipError,
    KnowledgeCycleError,
    KnowledgeEngineError,
    KnowledgeEngineNotInitializedError,
    KnowledgeAccessDeniedError,
)

# Models
from .models import (
    KnowledgeId,
    KnowledgeMetadata,
    KnowledgeReference,
    KnowledgeRecord,
    KnowledgeSnapshot,
    VersionDiff,
    KnowledgeItemStats,
    KnowledgeRepositoryStats,
    KnowledgeFilter,
    KnowledgeQuery,
    SearchQuery,
    PageRequest,
    PageResult,
    generate_id,
    parse_id,
)

# Core context
from .knowledge_context import (
    KnowledgeContext,
    get_knowledge_context,
    reset_knowledge_context,
    current_actor,
    current_operation_id,
    knowledge_operation,
)

# Factory
from .knowledge_factory import KnowledgeFactory, get_knowledge_factory

# Repository
from .repositories import KnowledgeRepository, get_knowledge_repository, reset_knowledge_repository

# Search
from .search import SearchResult, KnowledgeSearchEngine, get_search_engine, reset_search_engine

# Graph
from .graph import KnowledgeGraph, get_knowledge_graph, reset_knowledge_graph

# Versioning
from .versioning import KnowledgeVersioningEngine, get_versioning_engine, reset_versioning_engine

# Storage
from .storage import KnowledgeStorage, get_knowledge_storage, reset_knowledge_storage

# Manager (façade)
from .knowledge_manager import KnowledgeManager, get_knowledge_manager, reset_knowledge_manager

# Engine (lifecycle)
from .knowledge_engine import KnowledgeEngine, get_knowledge_engine, reset_knowledge_engine

__version__ = "1.0.0"
__status__ = "production"
__wave__ = 3
__layer__ = "KNOWLEDGE"
__owner__ = "Platform"

__all__ = [
    # constants
    "KnowledgeType", "KnowledgeStatus", "KnowledgePriority", "KnowledgeSource",
    "KnowledgeDomain", "VersionBump", "VersionStatus", "ValidationResult",
    "ConstraintType", "QueryOperator", "SortOrder", "SearchMode",
    "RelationshipType", "RelationshipStrength", "IndexType", "KnowledgeEvent",
    "DEFAULT_PAGE_SIZE", "MAX_PAGE_SIZE", "DEFAULT_CACHE_TTL", "DEFAULT_CONFIDENCE",
    "KNOWLEDGE_NAMESPACE", "SYSTEM_OWNER",
    # exceptions
    "KnowledgeError", "KnowledgeNotFoundError", "KnowledgeAlreadyExistsError",
    "KnowledgeValidationError", "KnowledgeVersionError", "KnowledgeStorageError",
    "KnowledgeSearchError", "KnowledgeGraphError", "KnowledgeRelationshipError",
    "KnowledgeCycleError", "KnowledgeEngineError", "KnowledgeEngineNotInitializedError",
    "KnowledgeAccessDeniedError",
    # models
    "KnowledgeId", "KnowledgeMetadata", "KnowledgeReference", "KnowledgeRecord",
    "KnowledgeSnapshot", "VersionDiff", "KnowledgeItemStats", "KnowledgeRepositoryStats",
    "KnowledgeFilter", "KnowledgeQuery", "SearchQuery", "PageRequest", "PageResult",
    "generate_id", "parse_id",
    # context
    "KnowledgeContext", "get_knowledge_context", "reset_knowledge_context",
    "current_actor", "current_operation_id", "knowledge_operation",
    # factory
    "KnowledgeFactory", "get_knowledge_factory",
    # repository
    "KnowledgeRepository", "get_knowledge_repository", "reset_knowledge_repository",
    # search
    "SearchResult", "KnowledgeSearchEngine", "get_search_engine", "reset_search_engine",
    # graph
    "KnowledgeGraph", "get_knowledge_graph", "reset_knowledge_graph",
    # versioning
    "KnowledgeVersioningEngine", "get_versioning_engine", "reset_versioning_engine",
    # storage
    "KnowledgeStorage", "get_knowledge_storage", "reset_knowledge_storage",
    # manager
    "KnowledgeManager", "get_knowledge_manager", "reset_knowledge_manager",
    # engine
    "KnowledgeEngine", "get_knowledge_engine", "reset_knowledge_engine",
]

