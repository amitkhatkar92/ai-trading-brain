"""
iios/ontology/query/query_manager.py
=====================================
Unified query manager — the primary entry point for all structured
ontology queries.

Coordinates the query cache, optimizer, resolution engine, semantic
engine, and the legacy OntologyQueryEngine so that callers only need
one object to drive all query operations.

Singleton: get_query_manager() / reset_query_manager()
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from .query_constants import (
    QueryType,
    ResolutionStrategy,
    NavigationDirection,
    SortOrder,
    QueryStatus,
    SemanticRelation,
    DEFAULT_RESULT_LIMIT,
    SYSTEM_QUERY_ACTOR,
)
from .query_exceptions import (
    QueryNotFoundError,
    QueryTimeoutError,
    QueryEngineNotInitializedError,
)
from .query_context   import get_query_context
from .query_cache     import get_query_cache, QueryCache
from .query_factory   import (
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
    get_query_factory,
)
from .query_optimizer  import get_query_optimizer
from .query_registry   import get_query_registry
from .resolution_engine import get_resolution_engine
from .semantic_engine   import get_semantic_engine
from ..registry.ontology_registry_manager import get_registry_manager
from ..runtime.runtime_object import (
    OntologyProperty,
    OntologyRelationshipDef,
    OntologyTypeDef,
)

__all__ = [
    "QueryManager",
    "get_query_manager",
    "reset_query_manager",
]

_LOG = logging.getLogger("iios.ontology.query.manager")


class QueryManager:
    """
    Unified query manager.

    All major query and resolution operations are available here.
    The manager handles caching transparently: callers do not need to
    know about cache keys or TTLs.
    """

    def __init__(self) -> None:
        self._initialized = False
        self._query_count = 0
        self._cache_hits  = 0
        self._lock        = threading.RLock()

    # ── Initialization ────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Idempotent initialization — safe to call multiple times."""
        with self._lock:
            if self._initialized:
                return
            # Trigger singleton creation for all dependencies
            get_query_cache()
            get_query_optimizer()
            get_query_registry()
            get_resolution_engine()
            get_semantic_engine()
            self._initialized = True
            _LOG.info("QueryManager initialized.")

    # ══════════════════════════════════════════════════════════════════════════
    #  Type lookup
    # ══════════════════════════════════════════════════════════════════════════

    def lookup_type(
        self,
        ref:      str,
        strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
    ) -> Optional[OntologyTypeDef]:
        """Resolve *ref* (URI / alias / name) to a type definition."""
        res  = get_resolution_engine()
        return res.resolve(ref, strategy)

    def lookup_type_or_raise(
        self,
        ref:      str,
        strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
    ) -> OntologyTypeDef:
        td = self.lookup_type(ref, strategy)
        if td is None:
            raise QueryNotFoundError(ref)
        return td

    def exists(self, ref: str) -> bool:
        return get_registry_manager().has_type(ref)

    # ══════════════════════════════════════════════════════════════════════════
    #  Hierarchy
    # ══════════════════════════════════════════════════════════════════════════

    def parent_of(self, type_uri: str) -> Optional[OntologyTypeDef]:
        """Return the direct parent type, or None if *type_uri* is a root."""
        mgr = get_registry_manager()
        td  = mgr.get_type_or_none(type_uri)
        if td and td.parent_uri:
            return mgr.get_type_or_none(td.parent_uri)
        return None

    def children_of(self, type_uri: str) -> list[OntologyTypeDef]:
        """Return the direct children of *type_uri*."""
        mgr = get_registry_manager()
        return [
            t for uri in sorted(mgr.children_of(type_uri))
            if (t := mgr.get_type_or_none(uri)) is not None
        ]

    def ancestors_of(
        self,
        type_uri:  str,
        max_depth: int = 32,
    ) -> list[OntologyTypeDef]:
        """
        Return ancestor types ordered nearest → root.
        Uses the resolution engine for cycle safety.
        """
        res   = get_resolution_engine()
        chain = res.resolve_inheritance_chain(type_uri, max_depth=max_depth)
        # First element is the type itself — return from index 1
        return chain[1:] if len(chain) > 1 else []

    def descendants_of(
        self,
        type_uri:  str,
        max_depth: int = 32,
    ) -> list[OntologyTypeDef]:
        """Return all descendant types (BFS order)."""
        mgr  = get_registry_manager()
        uris = mgr.descendants_of(type_uri)
        return [t for u in sorted(uris) if (t := mgr.get_type_or_none(u)) is not None]

    def is_subtype_of(self, candidate: str, base: str) -> bool:
        return get_registry_manager().is_subtype_of(candidate, base)

    def inheritance_chain(self, type_uri: str) -> list[OntologyTypeDef]:
        """Full chain from *type_uri* down to its root (inclusive)."""
        return get_resolution_engine().resolve_inheritance_chain(type_uri)

    # ══════════════════════════════════════════════════════════════════════════
    #  Properties
    # ══════════════════════════════════════════════════════════════════════════

    def properties_of(
        self,
        type_uri: str,
        inherited: bool = True,
    ) -> dict[str, OntologyProperty]:
        """
        Return the property map for *type_uri*.
        If *inherited* is True, merge inherited properties (child overrides parent).
        """
        if inherited:
            return get_resolution_engine().resolve_all_properties(type_uri)
        mgr = get_registry_manager()
        td  = mgr.get_type_or_none(type_uri)
        return dict(td.properties) if td else {}

    # ══════════════════════════════════════════════════════════════════════════
    #  Relationships
    # ══════════════════════════════════════════════════════════════════════════

    def lookup_relationship(
        self,
        ref: str,
    ) -> Optional[OntologyRelationshipDef]:
        return get_resolution_engine().resolve_relationship(ref)

    def relationships_for(
        self,
        type_uri: str,
    ) -> list[OntologyRelationshipDef]:
        """All relationships where *type_uri* is the source."""
        return get_registry_manager().relationships_for_source(type_uri)

    def all_relationships(self) -> list[OntologyRelationshipDef]:
        return get_registry_manager().list_relationships()

    # ══════════════════════════════════════════════════════════════════════════
    #  Search
    # ══════════════════════════════════════════════════════════════════════════

    def search(
        self,
        query_term:     str,
        namespace_hint: Optional[str] = None,
        max_results:    int            = DEFAULT_RESULT_LIMIT,
    ) -> list[OntologyTypeDef]:
        """
        Fast substring search over type names, URIs, labels, aliases.
        Results are semantically ranked.
        """
        cache     = get_query_cache()
        cache_key = cache.make_key("search", query_term, namespace_hint)

        cached = cache.get(cache_key)
        if cached is not None:
            with self._lock:
                self._cache_hits += 1
            return cached[:max_results]

        mgr     = get_registry_manager()
        results = mgr.search_types(query_term, max_results=max_results)

        if namespace_hint:
            results = [t for t in results if t.namespace_uri == namespace_hint]

        sem     = get_semantic_engine()
        ranked  = sem.semantic_rank(results, query_term)

        cache.put(cache_key, ranked, result_type="search")
        with self._lock:
            self._query_count += 1

        return ranked[:max_results]

    def fuzzy_search(
        self,
        query_term:  str,
        threshold:   float          = 0.5,
        namespace:   Optional[str]  = None,
        top_k:       int            = DEFAULT_RESULT_LIMIT,
    ) -> list[tuple[OntologyTypeDef, float]]:
        """Fuzzy-match *query_term* and return (type, score) pairs."""
        res = get_resolution_engine()
        return res.resolve_fuzzy(query_term, threshold=threshold, top_k=top_k, namespace=namespace)

    def suggest(self, partial: str, limit: int = 10) -> list[str]:
        """Return autocompletion suggestions for a partial query term."""
        return get_semantic_engine().suggest_queries(partial, limit=limit)

    # ══════════════════════════════════════════════════════════════════════════
    #  Semantic
    # ══════════════════════════════════════════════════════════════════════════

    def similar_types(
        self,
        type_uri: str,
        top_k:    int = 10,
    ):
        """Return the top-k semantically similar types."""
        return get_semantic_engine().find_similar(type_uri, top_k=top_k)

    def semantic_distance(self, uri_a: str, uri_b: str) -> float:
        return get_semantic_engine().semantic_distance(uri_a, uri_b)

    def neighborhood(self, type_uri: str, depth: int = 2) -> dict:
        return get_semantic_engine().discover_neighborhood(type_uri, depth=depth)

    def expand_concept(
        self,
        type_uri: str,
        radius:   int = 3,
    ) -> list[OntologyTypeDef]:
        return get_semantic_engine().expand_concept(type_uri, radius=radius)

    def find_related(
        self,
        type_uri: str,
        relation: SemanticRelation,
    ) -> list[OntologyTypeDef]:
        return get_semantic_engine().find_related(type_uri, relation)

    # ══════════════════════════════════════════════════════════════════════════
    #  Generic request API
    # ══════════════════════════════════════════════════════════════════════════

    def execute_query(self, request: QueryRequest) -> QueryResult:
        """
        Execute a QueryRequest, respecting optimizer hints and cache policy.
        """
        t0        = time.perf_counter()
        cache     = get_query_cache()
        optimizer = get_query_optimizer()
        factory   = get_query_factory()
        mgr       = get_registry_manager()

        plan = optimizer.plan(request)

        # Cache check
        if plan.use_cache:
            cache_key = cache.make_key(
                request.query_type.value,
                request.target,
                request.namespace_hint,
                request.include_abstract,
                request.include_deprecated,
            )
            cached = cache.get(cache_key)
            if cached is not None:
                duration = (time.perf_counter() - t0) * 1_000.0
                with self._lock:
                    self._cache_hits += 1
                return factory.make_query_result(
                    request     = request,
                    types       = cached,
                    status      = QueryStatus.CACHED,
                    duration_ms = duration,
                    from_cache  = True,
                )

        # Execute
        with get_query_context().query_operation(request.query_type, request.target):
            types = self._execute(request, mgr)

        # Truncation
        truncated = len(types) > request.limit
        types     = types[:request.limit]

        if plan.use_cache:
            cache.put(cache_key, types, ttl=plan.cache_ttl)

        duration = (time.perf_counter() - t0) * 1_000.0
        with self._lock:
            self._query_count += 1

        return factory.make_query_result(
            request     = request,
            types       = types,
            status      = QueryStatus.COMPLETED,
            duration_ms = duration,
            truncated   = truncated,
        )

    def execute_resolution(self, request: ResolutionRequest) -> ResolutionResult:
        return get_resolution_engine().resolve_request(request)

    def execute_navigation(self, request: NavigationRequest) -> NavigationResult:
        return self._navigate(request)

    def execute_search(self, request: SearchRequest) -> SearchResult:
        t0      = time.perf_counter()
        factory = get_query_factory()
        matches = self.fuzzy_search(
            request.query_term,
            threshold  = request.fuzzy_threshold,
            namespace  = request.namespace_hint,
            top_k      = request.max_results,
        )
        duration = (time.perf_counter() - t0) * 1_000.0
        return factory.make_search_result(
            request     = request,
            matches     = matches,
            duration_ms = duration,
        )

    def execute_semantic(self, request: SemanticRequest) -> SemanticResult:
        return get_semantic_engine().process_request(request)

    # ══════════════════════════════════════════════════════════════════════════
    #  Named queries
    # ══════════════════════════════════════════════════════════════════════════

    def execute_named(
        self,
        query_id: str,
        **overrides,
    ) -> QueryResult:
        """Execute a named/stored query by its ID."""
        reg     = get_query_registry()
        request = reg.build_request(query_id, **overrides)
        return self.execute_query(request)

    # ══════════════════════════════════════════════════════════════════════════
    #  Cache management
    # ══════════════════════════════════════════════════════════════════════════

    def invalidate_cache(self) -> None:
        get_query_cache().clear()

    def invalidate_namespace(self, namespace_uri: str) -> int:
        """Evict all cached results that are scoped to *namespace_uri*."""
        return get_query_cache().invalidate_prefix(namespace_uri)

    # ══════════════════════════════════════════════════════════════════════════
    #  Stats & health
    # ══════════════════════════════════════════════════════════════════════════

    def stats(self) -> dict:
        cache_stats = get_query_cache().stats()
        opt_stats   = get_query_optimizer().stats()
        res_stats   = get_resolution_engine().stats()
        sem_stats   = get_semantic_engine().stats()
        reg_stats   = get_query_registry().stats()
        mgr_stats   = get_registry_manager().stats()

        with self._lock:
            return {
                "initialized":  self._initialized,
                "query_count":  self._query_count,
                "cache_hits":   self._cache_hits,
                "cache":        cache_stats,
                "optimizer":    opt_stats,
                "resolution":   res_stats,
                "semantic":     sem_stats,
                "registry":     reg_stats,
                "ontology":     mgr_stats,
            }

    def health(self) -> dict:
        mgr   = get_registry_manager()
        s     = mgr.stats()
        cache = get_query_cache().stats()
        return {
            "status":          "healthy",
            "initialized":     self._initialized,
            "total_types":     s["total_types"],
            "total_relations": s["total_relationships"],
            "cache_size":      cache["size"],
            "cache_hit_rate":  cache["hit_rate"],
        }

    # ── Private execution ──────────────────────────────────────────────────────

    def _execute(
        self,
        req: QueryRequest,
        mgr,
    ) -> list[OntologyTypeDef]:
        """Route a QueryRequest to the appropriate low-level handler."""
        qt = req.query_type

        if qt == QueryType.TYPE_LOOKUP:
            td = mgr.get_type_or_none(req.target)
            return [td] if td else []

        if qt == QueryType.ANCESTORS:
            return self.ancestors_of(req.target, max_depth=req.options.get("max_depth", 32))

        if qt == QueryType.DESCENDANTS:
            return self.descendants_of(req.target)

        if qt == QueryType.CHILDREN:
            return self.children_of(req.target)

        if qt == QueryType.PARENT:
            p = self.parent_of(req.target)
            return [p] if p else []

        if qt == QueryType.HIERARCHY:
            return self.inheritance_chain(req.target)

        if qt == QueryType.SEARCH:
            return self.search(req.target, req.namespace_hint, req.limit)

        if qt == QueryType.SEMANTIC:
            sem    = get_semantic_engine()
            items  = sem.find_similar(req.target, top_k=req.limit)
            return [s.type_def for s in items]

        if qt == QueryType.NEIGHBORHOOD:
            return self.expand_concept(req.target, radius=req.options.get("radius", 3))

        if qt == QueryType.RELATIONSHIP_LOOKUP:
            rel = mgr.get_relationship(req.target)
            return []   # Relationships are not type objects; caller uses lookup_relationship

        if qt == QueryType.METADATA:
            td = mgr.get_type_or_none(req.target)
            return [td] if td else []

        if qt == QueryType.NAMED:
            inner = get_query_registry().build_request(req.target)
            return self._execute(inner, mgr)

        # Default: full-scan
        candidates = mgr.list_all_types()
        if req.namespace_hint:
            candidates = [t for t in candidates if t.namespace_uri == req.namespace_hint]
        if not req.include_abstract:
            candidates = [t for t in candidates if not t.abstract]
        if not req.include_deprecated:
            candidates = [t for t in candidates if not t.deprecated]
        return candidates

    def _navigate(self, request: NavigationRequest) -> NavigationResult:
        t0      = time.perf_counter()
        factory = get_query_factory()
        mgr     = get_registry_manager()

        visited: list[OntologyTypeDef] = []
        path:    list[str]             = [request.start_uri]
        queue   = [(request.start_uri, 0)]
        seen    = {request.start_uri}

        while queue:
            current_uri, depth = queue.pop(0)
            if depth > request.max_depth:
                return factory.make_navigation_result(
                    request     = request,
                    path        = path,
                    visited     = visited,
                    depth       = depth,
                    duration_ms = (time.perf_counter() - t0) * 1_000.0,
                    truncated   = True,
                )

            td = mgr.get_type_or_none(current_uri)
            if td and current_uri != request.start_uri:
                visited.append(td)

            direction = request.direction
            next_uris: set[str] = set()

            if direction in (NavigationDirection.UP, NavigationDirection.BOTH):
                if td and td.parent_uri:
                    next_uris.add(td.parent_uri)

            if direction in (NavigationDirection.DOWN, NavigationDirection.BOTH):
                next_uris.update(mgr.children_of(current_uri))

            if direction == NavigationDirection.LATERAL:
                if td and td.parent_uri:
                    next_uris = mgr.children_of(td.parent_uri) - {current_uri}

            for nxt in sorted(next_uris):
                if nxt not in seen:
                    if request.stop_at and nxt == request.stop_at:
                        path.append(nxt)
                        nxt_td = mgr.get_type_or_none(nxt)
                        if nxt_td:
                            visited.append(nxt_td)
                        duration = (time.perf_counter() - t0) * 1_000.0
                        return factory.make_navigation_result(
                            request     = request,
                            path        = path,
                            visited     = visited,
                            depth       = depth + 1,
                            duration_ms = duration,
                        )
                    seen.add(nxt)
                    path.append(nxt)
                    queue.append((nxt, depth + 1))

        duration = (time.perf_counter() - t0) * 1_000.0
        return factory.make_navigation_result(
            request     = request,
            path        = path,
            visited     = visited,
            depth       = max((d for _, d in queue), default=0) if queue else 0,
            duration_ms = duration,
        )


# ── Singleton ─────────────────────────────────────────────────────────────────

_mgr_lock = threading.Lock()
_mgr_instance: Optional[QueryManager] = None


def get_query_manager() -> QueryManager:
    global _mgr_instance
    if _mgr_instance is None:
        with _mgr_lock:
            if _mgr_instance is None:
                _mgr_instance = QueryManager()
                _mgr_instance.initialize()
    return _mgr_instance


def reset_query_manager() -> None:
    global _mgr_instance
    with _mgr_lock:
        _mgr_instance = None
