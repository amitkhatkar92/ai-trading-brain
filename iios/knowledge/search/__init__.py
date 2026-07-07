"""
iios/knowledge/search/__init__.py
==========================================
Knowledge Indexing & Search Engine + the original KnowledgeSearchEngine
(used internally by KnowledgeEngine / KnowledgeManager).
"""
from __future__ import annotations

# ── Original search engine (backward-compat) ──────────────────────────────────
from .knowledge_search import (
    SearchResult           as KnowledgeSearchResult,
    KnowledgeSearchEngine,
    get_search_engine      as get_knowledge_search_engine,
    reset_search_engine    as reset_knowledge_search_engine,
)
# Keep old names for direct imports of SearchResult / get_search_engine
from .knowledge_search import SearchResult, get_search_engine, reset_search_engine

# ── Constants & exceptions ────────────────────────────────────────────────────
from .search_constants import (
    SearchType, SearchIndexType, RankingStrategy, SearchSortOrder,
    SearchQueryOp, ItemType, SearchEvent,
    SEARCH_NAMESPACE, SYSTEM_SEARCH_ACTOR,
    DEFAULT_SEARCH_PAGE_SIZE, MAX_SEARCH_PAGE_SIZE, DEFAULT_MAX_RESULTS,
    SEARCH_CACHE_TTL, SEARCH_CACHE_MAX_SIZE,
    DEFAULT_FUZZY_THRESHOLD, SEARCH_SCHEMA_VERSION,
)
from .search_exceptions import (
    SearchError, SearchValidationError,
    SearchIndexError, SearchIndexNotFoundError, SearchIndexAlreadyExistsError,
    SearchQueryError, SearchQueryParseError, SearchQueryValidationError,
    SearchExecutionError, SearchRankingError, SearchCacheError,
    SearchEngineError, SearchEngineNotInitializedError,
    SearchRegistryError, SearchContextError, SearchIntegrationError,
)

# ── Models ────────────────────────────────────────────────────────────────────
from .models import (
    UnifiedSearchQuery, UnifiedSearchResult, SearchResponse,
    IndexDefinition, IndexStatistics,
)

# ── Index layer ───────────────────────────────────────────────────────────────
from .index_manager    import IndexManager,    get_index_manager,    reset_index_manager
from .index_builder    import IndexBuilder,    get_index_builder,    reset_index_builder
from .index_registry   import IndexRegistry,   get_index_registry,   reset_index_registry
from .index_statistics import SearchStats,     get_search_stats,     reset_search_stats
from .index_optimizer  import IndexOptimizer,  get_index_optimizer,  reset_index_optimizer

# ── Query layer ───────────────────────────────────────────────────────────────
from .query_parser    import ParsedQuery,     QueryParser,    get_query_parser,    reset_query_parser
from .query_builder   import QueryBuilder,    get_query_builder,   reset_query_builder
from .query_validator import QueryValidator,  get_query_validator, reset_query_validator
from .query_optimizer import QueryOptimizer,  get_query_optimizer, reset_query_optimizer
from .query_executor  import QueryExecutor,   get_query_executor,  reset_query_executor

# ── Search layer ──────────────────────────────────────────────────────────────
from .search_engine   import SearchEngine,    get_search_engine    as get_unified_search_engine,    reset_search_engine    as reset_unified_search_engine
from .search_context  import (
    SearchContext, get_search_context, reset_search_context,
    current_search_actor, current_search_operation_id, search_operation,
)
from .search_factory  import SearchFactory,   get_search_factory,  reset_search_factory
from .search_manager  import SearchManager,   get_search_manager,  reset_search_manager
from .search_registry import SearchRegistry,  get_search_registry, reset_search_registry

__all__ = [
    # legacy
    "SearchResult", "KnowledgeSearchResult", "KnowledgeSearchEngine",
    "get_knowledge_search_engine", "reset_knowledge_search_engine",
    "get_search_engine", "reset_search_engine",
    # constants
    "SearchType", "SearchIndexType", "RankingStrategy", "SearchSortOrder",
    "SearchQueryOp", "ItemType", "SearchEvent",
    "SEARCH_NAMESPACE", "SYSTEM_SEARCH_ACTOR",
    "DEFAULT_SEARCH_PAGE_SIZE", "MAX_SEARCH_PAGE_SIZE", "DEFAULT_MAX_RESULTS",
    "SEARCH_CACHE_TTL", "SEARCH_CACHE_MAX_SIZE",
    "DEFAULT_FUZZY_THRESHOLD", "SEARCH_SCHEMA_VERSION",
    # exceptions
    "SearchError", "SearchValidationError",
    "SearchIndexError", "SearchIndexNotFoundError", "SearchIndexAlreadyExistsError",
    "SearchQueryError", "SearchQueryParseError", "SearchQueryValidationError",
    "SearchExecutionError", "SearchRankingError", "SearchCacheError",
    "SearchEngineError", "SearchEngineNotInitializedError",
    "SearchRegistryError", "SearchContextError", "SearchIntegrationError",
    # models
    "UnifiedSearchQuery", "UnifiedSearchResult", "SearchResponse",
    "IndexDefinition", "IndexStatistics",
    # index
    "IndexManager",   "get_index_manager",   "reset_index_manager",
    "IndexBuilder",   "get_index_builder",   "reset_index_builder",
    "IndexRegistry",  "get_index_registry",  "reset_index_registry",
    "SearchStats",    "get_search_stats",    "reset_search_stats",
    "IndexOptimizer", "get_index_optimizer", "reset_index_optimizer",
    # query
    "ParsedQuery",    "QueryParser",    "get_query_parser",    "reset_query_parser",
    "QueryBuilder",   "get_query_builder",   "reset_query_builder",
    "QueryValidator", "get_query_validator", "reset_query_validator",
    "QueryOptimizer", "get_query_optimizer", "reset_query_optimizer",
    "QueryExecutor",  "get_query_executor",  "reset_query_executor",
    # search
    "SearchEngine",   "get_unified_search_engine",   "reset_unified_search_engine",
    "SearchContext",  "get_search_context",  "reset_search_context",
    "current_search_actor", "current_search_operation_id", "search_operation",
    "SearchFactory",  "get_search_factory",  "reset_search_factory",
    "SearchManager",  "get_search_manager",  "reset_search_manager",
    "SearchRegistry", "get_search_registry", "reset_search_registry",
]
