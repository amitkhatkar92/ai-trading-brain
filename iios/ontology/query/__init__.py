"""iios/ontology/query/__init__.py — Ontology Query & Semantic Resolution Engine."""
from __future__ import annotations

# ── Legacy query builder (kept for backward compatibility) ────────────────────
from .ontology_query import (
    OntologyFilter,
    OntologyQuery,
    OntologyQueryResult,
    OntologyQueryEngine,
    get_query_engine,
    reset_query_engine,
)

# ── Constants ─────────────────────────────────────────────────────────────────
from .query_constants import (
    QueryType,
    ResolutionStrategy,
    NavigationDirection,
    SortOrder,
    QueryStatus,
    SemanticRelation,
    IndexHint,
    MAX_QUERY_DEPTH,
    DEFAULT_FUZZY_THRESHOLD,
    MAX_FUZZY_CANDIDATES,
    MAX_EXPAND_RADIUS,
    QUERY_TIMEOUT_MS,
    QUERY_CACHE_TTL_SECONDS,
    QUERY_CACHE_MAX_SIZE,
    MAX_NAMED_QUERIES,
    DEFAULT_RESULT_LIMIT,
    MAX_RESOLUTION_DEPTH,
    SEMANTIC_DISTANCE_INFINITY,
    QUERY_ENGINE_VERSION,
    SYSTEM_QUERY_ACTOR,
    QID_ALL_TYPES,
    QID_ENTITY_TYPES,
    QID_ABSTRACT_TYPES,
    QID_CONCRETE_TYPES,
    QID_ALL_RELATIONSHIPS,
    QID_ALL_NAMESPACES,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .query_exceptions import (
    QueryError,
    QueryNotFoundError,
    QueryTimeoutError,
    QuerySyntaxError,
    QueryLimitExceededError,
    ResolutionError,
    AliasResolutionError,
    InheritanceResolutionError,
    CircularResolutionError,
    ReferenceResolutionError,
    NavigationError,
    TraversalDepthError,
    NavigationDeadEndError,
    SemanticError,
    SemanticDistanceError,
    QueryCacheError,
    NamedQueryError,
    DuplicateNamedQueryError,
    UnknownNamedQueryError,
    QueryEngineError,
    QueryEngineNotInitializedError,
)

# ── Context ───────────────────────────────────────────────────────────────────
from .query_context import (
    QueryDiagnosticLevel,
    QueryDiagnostic,
    QueryContext,
    get_query_context,
    reset_query_context,
)

# ── Factory & models ──────────────────────────────────────────────────────────
from .query_factory import (
    QueryRequest,
    ResolutionRequest,
    NavigationRequest,
    SearchRequest,
    SemanticRequest,
    QueryResult,
    ResolutionResult,
    NavigationResult,
    SearchResult,
    SemanticResult,
    SimilarType,
    QueryFactory,
    get_query_factory,
    reset_query_factory,
)

# ── Cache ─────────────────────────────────────────────────────────────────────
from .query_cache import (
    QueryCacheEntry,
    QueryCache,
    get_query_cache,
    reset_query_cache,
)

# ── Optimizer ─────────────────────────────────────────────────────────────────
from .query_optimizer import (
    OptimizationStep,
    QueryPlan,
    QueryOptimizer,
    get_query_optimizer,
    reset_query_optimizer,
)

# ── Named query registry ──────────────────────────────────────────────────────
from .query_registry import (
    NamedQuery,
    QueryRegistry,
    get_query_registry,
    reset_query_registry,
)

# ── Resolution engine ─────────────────────────────────────────────────────────
from .resolution_engine import (
    ResolutionEngine,
    get_resolution_engine,
    reset_resolution_engine,
)

# ── Semantic engine ───────────────────────────────────────────────────────────
from .semantic_engine import (
    SemanticEngine,
    get_semantic_engine,
    reset_semantic_engine,
)

# ── Query manager ─────────────────────────────────────────────────────────────
from .query_manager import (
    QueryManager,
    get_query_manager,
    reset_query_manager,
)

# ── Master engine ─────────────────────────────────────────────────────────────
from .query_engine import (
    QueryEngine,
    get_query_engine_v2,
    reset_query_engine_v2,
)

__all__ = [
    # Legacy
    "OntologyFilter", "OntologyQuery", "OntologyQueryResult",
    "OntologyQueryEngine", "get_query_engine", "reset_query_engine",
    # Constants
    "QueryType", "ResolutionStrategy", "NavigationDirection", "SortOrder",
    "QueryStatus", "SemanticRelation", "IndexHint",
    "MAX_QUERY_DEPTH", "DEFAULT_FUZZY_THRESHOLD", "MAX_FUZZY_CANDIDATES",
    "MAX_EXPAND_RADIUS", "QUERY_TIMEOUT_MS", "QUERY_CACHE_TTL_SECONDS",
    "QUERY_CACHE_MAX_SIZE", "MAX_NAMED_QUERIES", "DEFAULT_RESULT_LIMIT",
    "MAX_RESOLUTION_DEPTH", "SEMANTIC_DISTANCE_INFINITY",
    "QUERY_ENGINE_VERSION", "SYSTEM_QUERY_ACTOR",
    "QID_ALL_TYPES", "QID_ENTITY_TYPES", "QID_ABSTRACT_TYPES",
    "QID_CONCRETE_TYPES", "QID_ALL_RELATIONSHIPS", "QID_ALL_NAMESPACES",
    # Exceptions
    "QueryError", "QueryNotFoundError", "QueryTimeoutError",
    "QuerySyntaxError", "QueryLimitExceededError",
    "ResolutionError", "AliasResolutionError", "InheritanceResolutionError",
    "CircularResolutionError", "ReferenceResolutionError",
    "NavigationError", "TraversalDepthError", "NavigationDeadEndError",
    "SemanticError", "SemanticDistanceError",
    "QueryCacheError",
    "NamedQueryError", "DuplicateNamedQueryError", "UnknownNamedQueryError",
    "QueryEngineError", "QueryEngineNotInitializedError",
    # Context
    "QueryDiagnosticLevel", "QueryDiagnostic", "QueryContext",
    "get_query_context", "reset_query_context",
    # Factory
    "QueryRequest", "ResolutionRequest", "NavigationRequest",
    "SearchRequest", "SemanticRequest",
    "QueryResult", "ResolutionResult", "NavigationResult",
    "SearchResult", "SemanticResult", "SimilarType",
    "QueryFactory", "get_query_factory", "reset_query_factory",
    # Cache
    "QueryCacheEntry", "QueryCache", "get_query_cache", "reset_query_cache",
    # Optimizer
    "OptimizationStep", "QueryPlan", "QueryOptimizer",
    "get_query_optimizer", "reset_query_optimizer",
    # Registry
    "NamedQuery", "QueryRegistry", "get_query_registry", "reset_query_registry",
    # Engines
    "ResolutionEngine", "get_resolution_engine", "reset_resolution_engine",
    "SemanticEngine", "get_semantic_engine", "reset_semantic_engine",
    "QueryManager", "get_query_manager", "reset_query_manager",
    "QueryEngine", "get_query_engine_v2", "reset_query_engine_v2",
]

