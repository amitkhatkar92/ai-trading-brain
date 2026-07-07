"""
iios/ontology/query/query_engine.py
=====================================
Master Ontology Query & Semantic Resolution Engine.

This is the single semantic access layer for every IIOS subsystem.
No subsystem should access ontology structures directly — all semantic
operations must pass through this engine.

Architecture::

    QueryEngine          ← master facade
      ├── QueryManager   ← structured query coordination
      ├── ResolutionEngine ← canonical / alias / fuzzy resolution
      ├── SemanticEngine   ← similarity, expansion, neighbourhood
      ├── QueryRegistry    ← named / reusable queries
      ├── QueryCache       ← transparent result cache
      └── QueryOptimizer   ← query planning

Singleton: get_query_engine_v2() / reset_query_engine_v2()
(Named with _v2 to avoid clashing with the legacy get_query_engine()
 from ontology_query.py which is used by StatisticsService.)
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Optional

from .query_constants import (
    QueryType,
    ResolutionStrategy,
    NavigationDirection,
    SortOrder,
    SemanticRelation,
    DEFAULT_RESULT_LIMIT,
    QUERY_ENGINE_VERSION,
    SYSTEM_QUERY_ACTOR,
)
from .query_exceptions import QueryEngineNotInitializedError
from .query_context    import get_query_context
from .query_factory    import (
    QueryRequest,
    QueryResult,
    ResolutionRequest,
    ResolutionResult,
    NavigationRequest,
    NavigationResult,
    SearchRequest,
    SearchResult,
    SemanticRequest,
    SemanticResult,
    SimilarType,
    get_query_factory,
)
from .query_cache      import get_query_cache
from .query_optimizer  import get_query_optimizer
from .query_registry   import get_query_registry
from .query_manager    import get_query_manager, QueryManager
from .resolution_engine import get_resolution_engine
from .semantic_engine   import get_semantic_engine
from ..registry.ontology_registry_manager import get_registry_manager
from ..runtime.runtime_object import (
    OntologyNamespace,
    OntologyProperty,
    OntologyRelationshipDef,
    OntologyTypeDef,
)

__all__ = [
    "QueryEngine",
    "get_query_engine_v2",
    "reset_query_engine_v2",
]

_LOG = logging.getLogger("iios.ontology.query.engine")


class QueryEngine:
    """
    Master Ontology Query & Semantic Resolution Engine.

    Exposes the full semantic API surface in one object.  All methods
    delegate to the appropriate sub-engine after initialization.

    Usage::

        engine = get_query_engine_v2()

        # Simple lookups
        td = engine.type("iios.entity.Instrument")
        parents = engine.ancestors_of("iios.entity.Equity")

        # Semantic
        similar = engine.similar_types("iios.entity.Bond", top_k=5)
        dist    = engine.semantic_distance("iios.entity.Bond", "iios.entity.Equity")

        # Fluent queries
        result = engine.query(QueryType.DESCENDANTS, "iios.entity.Asset").execute()
    """

    def __init__(self) -> None:
        self._initialized   = False
        self._init_at:  float = 0.0
        self._lock      = threading.RLock()

    # ── Initialization ────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Idempotent setup — triggers all sub-engine singletons."""
        with self._lock:
            if self._initialized:
                return
            get_query_manager()        # boots cache, optimizer, registry, etc.
            self._initialized = True
            self._init_at     = time.time()
            _LOG.info(
                "QueryEngine v%s initialized.",
                QUERY_ENGINE_VERSION,
            )

    def _require_init(self) -> None:
        if not self._initialized:
            raise QueryEngineNotInitializedError()

    # ══════════════════════════════════════════════════════════════════════════
    #  Type resolution
    # ══════════════════════════════════════════════════════════════════════════

    def type(
        self,
        ref:      str,
        strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
    ) -> Optional[OntologyTypeDef]:
        """Resolve *ref* to a type definition (None if not found)."""
        return get_query_manager().lookup_type(ref, strategy)

    def type_or_raise(
        self,
        ref:      str,
        strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
    ) -> OntologyTypeDef:
        """Like type() but raises QueryNotFoundError if unresolvable."""
        return get_query_manager().lookup_type_or_raise(ref, strategy)

    def has_type(self, ref: str) -> bool:
        return get_query_manager().exists(ref)

    def canonical_uri(self, ref: str) -> Optional[str]:
        return get_resolution_engine().resolve_canonical(ref)

    # ══════════════════════════════════════════════════════════════════════════
    #  Hierarchy navigation
    # ══════════════════════════════════════════════════════════════════════════

    def parent_of(self, type_uri: str) -> Optional[OntologyTypeDef]:
        return get_query_manager().parent_of(type_uri)

    def children_of(self, type_uri: str) -> list[OntologyTypeDef]:
        return get_query_manager().children_of(type_uri)

    def ancestors_of(
        self,
        type_uri:  str,
        max_depth: int = 32,
    ) -> list[OntologyTypeDef]:
        return get_query_manager().ancestors_of(type_uri, max_depth=max_depth)

    def descendants_of(self, type_uri: str) -> list[OntologyTypeDef]:
        return get_query_manager().descendants_of(type_uri)

    def inheritance_chain(self, type_uri: str) -> list[OntologyTypeDef]:
        """Full chain: [type, parent, grandparent, …, root]."""
        return get_query_manager().inheritance_chain(type_uri)

    def is_subtype_of(self, candidate: str, base: str) -> bool:
        return get_query_manager().is_subtype_of(candidate, base)

    # ══════════════════════════════════════════════════════════════════════════
    #  Properties
    # ══════════════════════════════════════════════════════════════════════════

    def properties_of(
        self,
        type_uri:  str,
        inherited: bool = True,
    ) -> dict[str, OntologyProperty]:
        return get_query_manager().properties_of(type_uri, inherited=inherited)

    def property(
        self,
        type_uri:  str,
        prop_name: str,
        inherited: bool = True,
    ) -> Optional[OntologyProperty]:
        props = self.properties_of(type_uri, inherited=inherited)
        return props.get(prop_name)

    # ══════════════════════════════════════════════════════════════════════════
    #  Relationships
    # ══════════════════════════════════════════════════════════════════════════

    def relationship(self, ref: str) -> Optional[OntologyRelationshipDef]:
        return get_query_manager().lookup_relationship(ref)

    def relationships_for(self, type_uri: str) -> list[OntologyRelationshipDef]:
        return get_query_manager().relationships_for(type_uri)

    def all_relationships(self) -> list[OntologyRelationshipDef]:
        return get_query_manager().all_relationships()

    # ══════════════════════════════════════════════════════════════════════════
    #  Namespaces
    # ══════════════════════════════════════════════════════════════════════════

    def namespace(self, uri: str) -> Optional[OntologyNamespace]:
        return get_registry_manager().get_namespace_or_none(uri)

    def all_namespaces(self) -> list[OntologyNamespace]:
        return get_registry_manager().list_namespaces()

    def types_in_namespace(self, namespace_uri: str) -> list[OntologyTypeDef]:
        return get_registry_manager().types_in_namespace(namespace_uri)

    # ══════════════════════════════════════════════════════════════════════════
    #  Search
    # ══════════════════════════════════════════════════════════════════════════

    def search(
        self,
        query_term:     str,
        namespace_hint: Optional[str] = None,
        max_results:    int            = DEFAULT_RESULT_LIMIT,
    ) -> list[OntologyTypeDef]:
        """Fast substring search with semantic ranking."""
        return get_query_manager().search(query_term, namespace_hint, max_results)

    def fuzzy_search(
        self,
        query_term: str,
        threshold:  float         = 0.5,
        namespace:  Optional[str] = None,
        top_k:      int           = DEFAULT_RESULT_LIMIT,
    ) -> list[tuple[OntologyTypeDef, float]]:
        """Fuzzy match returning (type, score) pairs."""
        return get_query_manager().fuzzy_search(query_term, threshold, namespace, top_k)

    def suggest(self, partial: str, limit: int = 10) -> list[str]:
        """Autocompletion suggestions for a partial query term."""
        return get_query_manager().suggest(partial, limit=limit)

    # ══════════════════════════════════════════════════════════════════════════
    #  Semantic reasoning
    # ══════════════════════════════════════════════════════════════════════════

    def similar_types(
        self,
        type_uri: str,
        top_k:    int = 10,
    ) -> list[SimilarType]:
        """Top-k semantically similar types with scores and relations."""
        return get_query_manager().similar_types(type_uri, top_k=top_k)

    def semantic_distance(self, uri_a: str, uri_b: str) -> float:
        """LCA-based semantic distance (0.0 = identical)."""
        return get_query_manager().semantic_distance(uri_a, uri_b)

    def is_semantically_equivalent(self, uri_a: str, uri_b: str) -> bool:
        """True if the two URIs resolve to the same canonical type."""
        return get_semantic_engine().is_semantically_equivalent(uri_a, uri_b)

    def expand_concept(
        self,
        type_uri: str,
        radius:   int = 3,
    ) -> list[OntologyTypeDef]:
        """BFS neighbourhood expansion within *radius* hops."""
        return get_query_manager().expand_concept(type_uri, radius=radius)

    def neighborhood(self, type_uri: str, depth: int = 2) -> dict:
        """Structured neighbourhood view: parents/children/siblings/related."""
        return get_query_manager().neighborhood(type_uri, depth=depth)

    def find_related(
        self,
        type_uri: str,
        relation: SemanticRelation,
    ) -> list[OntologyTypeDef]:
        """Find types connected by the specified semantic relation."""
        return get_query_manager().find_related(type_uri, relation)

    def semantic_rank(
        self,
        types:      list[OntologyTypeDef],
        query_term: str,
    ) -> list[OntologyTypeDef]:
        """Re-rank *types* by relevance to *query_term*."""
        return get_semantic_engine().semantic_rank(types, query_term)

    # ══════════════════════════════════════════════════════════════════════════
    #  Resolution
    # ══════════════════════════════════════════════════════════════════════════

    def resolve_alias(self, alias: str) -> Optional[str]:
        return get_resolution_engine().resolve_alias(alias)

    def resolve_by_label(
        self,
        label:          str,
        namespace_hint: Optional[str] = None,
    ) -> list[OntologyTypeDef]:
        return get_resolution_engine().resolve_by_label(label, namespace_hint)

    def all_properties_merged(
        self,
        type_uri: str,
    ) -> dict[str, OntologyProperty]:
        """Fully merged property map (child overrides parent)."""
        return get_resolution_engine().resolve_all_properties(type_uri)

    # ══════════════════════════════════════════════════════════════════════════
    #  Fluent request builders
    # ══════════════════════════════════════════════════════════════════════════

    def query(
        self,
        query_type: QueryType,
        target:     str,
        **options: Any,
    ) -> "_FluentQuery":
        """Start a fluent query chain: engine.query(QueryType.SEARCH, "bond").execute()"""
        return _FluentQuery(self, query_type, target, **options)

    def resolution_request(
        self,
        ref:      str,
        strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
    ) -> ResolutionResult:
        factory = get_query_factory()
        req     = factory.make_resolution(ref, strategy)
        return get_query_manager().execute_resolution(req)

    def navigation_request(
        self,
        start_uri:  str,
        direction:  NavigationDirection = NavigationDirection.DOWN,
        max_depth:  int                 = 16,
    ) -> NavigationResult:
        factory = get_query_factory()
        req     = factory.make_navigation(start_uri, direction, max_depth)
        return get_query_manager().execute_navigation(req)

    def search_request(
        self,
        query_term:     str,
        namespace_hint: Optional[str] = None,
        max_results:    int           = DEFAULT_RESULT_LIMIT,
        fuzzy_threshold: float        = 0.5,
    ) -> SearchResult:
        factory = get_query_factory()
        req     = factory.make_search(query_term, namespace_hint, max_results, fuzzy_threshold)
        return get_query_manager().execute_search(req)

    def semantic_request(
        self,
        type_uri: str,
        top_k:    int = 10,
        radius:   int = 3,
    ) -> SemanticResult:
        factory = get_query_factory()
        req     = factory.make_semantic(type_uri, top_k=top_k, radius=radius)
        return get_query_manager().execute_semantic(req)

    # ══════════════════════════════════════════════════════════════════════════
    #  Named query API
    # ══════════════════════════════════════════════════════════════════════════

    def execute_named(self, query_id: str, **overrides: Any) -> QueryResult:
        return get_query_manager().execute_named(query_id, **overrides)

    def register_named_query(
        self,
        query_id:       str,
        name:           str,
        description:    str,
        query_type:     QueryType,
        default_target: str                                = "",
        parameters:     dict[str, Any] | None             = None,
        builder:        Optional[Callable[..., QueryRequest]] = None,
        tags:           list[str] | None                   = None,
        overwrite:      bool                               = False,
    ) -> None:
        get_query_registry().register(
            query_id       = query_id,
            name           = name,
            description    = description,
            query_type     = query_type,
            default_target = default_target,
            parameters     = parameters,
            builder        = builder,
            tags           = tags,
            overwrite      = overwrite,
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  Cache management
    # ══════════════════════════════════════════════════════════════════════════

    def invalidate_cache(self) -> None:
        get_query_manager().invalidate_cache()

    def invalidate_namespace_cache(self, namespace_uri: str) -> int:
        return get_query_manager().invalidate_namespace(namespace_uri)

    # ══════════════════════════════════════════════════════════════════════════
    #  Utility listing
    # ══════════════════════════════════════════════════════════════════════════

    def all_types(self) -> list[OntologyTypeDef]:
        return get_registry_manager().list_all_types()

    def all_type_uris(self) -> list[str]:
        return get_registry_manager().all_type_uris()

    # ══════════════════════════════════════════════════════════════════════════
    #  Stats & health
    # ══════════════════════════════════════════════════════════════════════════

    def stats(self) -> dict:
        return {
            "version":     QUERY_ENGINE_VERSION,
            "initialized": self._initialized,
            "uptime_s":    round(time.time() - self._init_at, 1) if self._init_at else 0,
            **get_query_manager().stats(),
        }

    def health(self) -> dict:
        h = get_query_manager().health()
        h["version"] = QUERY_ENGINE_VERSION
        return h


# ── Fluent query helper ───────────────────────────────────────────────────────

class _FluentQuery:
    """Allows engine.query(type, target).namespace("x").limit(50).execute()."""

    def __init__(
        self,
        engine:     QueryEngine,
        query_type: QueryType,
        target:     str,
        **options: Any,
    ) -> None:
        self._engine     = engine
        self._query_type = query_type
        self._target     = target
        self._limit      = options.get("limit", DEFAULT_RESULT_LIMIT)
        self._namespace  = options.get("namespace_hint")
        self._abstract   = options.get("include_abstract", True)
        self._deprecated = options.get("include_deprecated", False)
        self._sort       = options.get("sort_order", SortOrder.RELEVANCE)
        self._filters: dict[str, Any] = {}
        self._actor      = options.get("actor", SYSTEM_QUERY_ACTOR)

    def limit(self, n: int) -> "_FluentQuery":
        self._limit = n
        return self

    def namespace(self, ns: str) -> "_FluentQuery":
        self._namespace = ns
        return self

    def not_abstract(self) -> "_FluentQuery":
        self._abstract = False
        return self

    def include_deprecated(self) -> "_FluentQuery":
        self._deprecated = True
        return self

    def sort_by(self, order: SortOrder) -> "_FluentQuery":
        self._sort = order
        return self

    def filter(self, **kwargs: Any) -> "_FluentQuery":
        self._filters.update(kwargs)
        return self

    def execute(self) -> QueryResult:
        factory = get_query_factory()
        req     = factory.make_query(
            query_type        = self._query_type,
            target            = self._target,
            limit             = self._limit,
            sort_order        = self._sort,
            include_abstract  = self._abstract,
            include_deprecated = self._deprecated,
            namespace_hint    = self._namespace,
            filters           = self._filters,
            actor             = self._actor,
        )
        return get_query_manager().execute_query(req)


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine_lock = threading.Lock()
_engine_instance: Optional[QueryEngine] = None


def get_query_engine_v2() -> QueryEngine:
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                _engine_instance = QueryEngine()
                _engine_instance.initialize()
    return _engine_instance


def reset_query_engine_v2() -> None:
    global _engine_instance
    with _engine_lock:
        _engine_instance = None
