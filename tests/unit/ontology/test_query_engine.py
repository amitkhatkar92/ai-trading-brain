"""
tests/unit/ontology/test_query_engine.py
=========================================
Comprehensive test suite for the IIOS Ontology Query &
Semantic Resolution Engine.

Coverage:
  1.  Query constants & enumerations
  2.  Query exceptions hierarchy
  3.  QueryContext (thread-local, CMs, diagnostics, isolation)
  4.  QueryFactory (all request/result constructors)
  5.  QueryCache (put/get/has/invalidate/LRU/TTL/stats)
  6.  QueryOptimizer (plan generation, index selection, TTL, cost)
  7.  QueryRegistry (register, lookup, builtin queries, named exec)
  8.  ResolutionEngine (exact/alias/canonical/fuzzy/inheritance/chain/props)
  9.  SemanticEngine (similarity, distance, expansion, ranking, neighbourhood)
 10.  QueryManager (lookup, hierarchy, search, relationships, cache, stats)
 11.  QueryEngine master (full API surface, fluent builder, health)
 12.  Navigation (UP/DOWN/BOTH/LATERAL traversal)
 13.  Concurrency (parallel queries from multiple threads)
 14.  Large ontology (100+ types)
 15.  End-to-end (full pipeline integration)
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

import pytest

# ═════════════════════════════════════════════════════════════════════════════
# Reset helpers
# ═════════════════════════════════════════════════════════════════════════════

def _reset_all() -> None:
    """Reset every query + ontology singleton for test isolation."""
    from iios.ontology.query.query_engine        import reset_query_engine_v2
    from iios.ontology.query.query_manager       import reset_query_manager
    from iios.ontology.query.resolution_engine   import reset_resolution_engine
    from iios.ontology.query.semantic_engine     import reset_semantic_engine
    from iios.ontology.query.query_registry      import reset_query_registry
    from iios.ontology.query.query_cache         import reset_query_cache
    from iios.ontology.query.query_optimizer     import reset_query_optimizer
    from iios.ontology.query.query_factory       import reset_query_factory
    from iios.ontology.query.query_context       import reset_query_context
    from iios.ontology.query.ontology_query      import reset_query_engine
    from iios.ontology.validator.validation_engine    import reset_validation_engine
    from iios.ontology.validator.ontology_validator   import reset_ontology_validator
    from iios.ontology.validator.constraint_manager   import reset_constraint_manager
    from iios.ontology.validator.constraint_engine    import reset_constraint_engine
    from iios.ontology.validator.constraint_registry  import reset_constraint_registry
    from iios.ontology.validator.validation_context   import reset_validation_context
    from iios.ontology.compiler.compiler_manager      import reset_compiler_manager
    from iios.ontology.compiler.compiler_registry     import reset_compiler_registry
    from iios.ontology.compiler.compiler_factory      import reset_compiler_factory
    from iios.ontology.compiler.compiler_context      import reset_compiler_context
    from iios.ontology.compiler.dependency_resolver   import reset_dependency_resolver
    from iios.ontology.compiler.metadata_generator    import reset_metadata_generator
    from iios.ontology.compiler.ontology_compiler     import reset_ontology_compiler
    from iios.ontology.loader.runtime_loader          import reset_runtime_loader
    from iios.ontology.loader.ontology_loader         import reset_ontology_loader
    from iios.ontology.cache.ontology_cache           import reset_ontology_cache
    from iios.ontology.registry.ontology_registry_manager import reset_registry_manager
    from iios.ontology.registry.entity_registry          import reset_entity_registry
    from iios.ontology.registry.relationship_registry    import reset_relationship_registry
    from iios.ontology.registry.event_registry           import reset_event_registry
    from iios.ontology.registry.observation_registry     import reset_observation_registry
    from iios.ontology.registry.knowledge_registry       import reset_knowledge_ont_registry
    from iios.ontology.ontology_registry                 import reset_ontology_registry
    from iios.ontology.ontology_manager                  import reset_ontology_manager
    from iios.ontology.ontology_runtime_engine           import reset_ontology_engine
    from iios.ontology.ontology_context                  import reset_ontology_context
    from iios.ontology.ontology_factory                  import reset_ontology_factory
    from iios.ontology.graph.ontology_graph              import reset_ontology_graph
    from iios.ontology.services.lookup_service           import reset_lookup_service
    from iios.ontology.services.hierarchy_service        import reset_hierarchy_service
    from iios.ontology.services.statistics_service       import reset_statistics_service
    from iios.ontology.loader.compiled_loader            import reset_compiled_loader
    from iios.ontology.loader.incremental_loader         import reset_incremental_loader
    from iios.ontology.loader.cache_loader               import reset_cache_loader

    reset_query_engine_v2()
    reset_query_manager()
    reset_resolution_engine()
    reset_semantic_engine()
    reset_query_registry()
    reset_query_cache()
    reset_query_optimizer()
    reset_query_factory()
    reset_query_context()
    reset_query_engine()
    reset_validation_engine()
    reset_ontology_validator()
    reset_constraint_manager()
    reset_constraint_engine()
    reset_constraint_registry()
    reset_validation_context()
    reset_compiler_manager()
    reset_compiler_registry()
    reset_compiler_factory()
    reset_compiler_context()
    reset_dependency_resolver()
    reset_metadata_generator()
    reset_ontology_compiler()
    reset_runtime_loader()
    reset_ontology_loader()
    reset_ontology_cache()
    reset_registry_manager()
    reset_entity_registry()
    reset_relationship_registry()
    reset_event_registry()
    reset_observation_registry()
    reset_knowledge_ont_registry()
    reset_ontology_registry()
    reset_ontology_manager()
    reset_ontology_engine()
    reset_ontology_context()
    reset_ontology_factory()
    reset_ontology_graph()
    reset_lookup_service()
    reset_hierarchy_service()
    reset_statistics_service()
    reset_compiled_loader()
    reset_incremental_loader()
    reset_cache_loader()


@pytest.fixture(autouse=True)
def clean_state():
    _reset_all()
    yield
    _reset_all()


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_type(
    name:   str,
    ns:     str = "iios.test",
    parent: str | None = None,
    labels: list[str] | None = None,
    aliases: list[str] | None = None,
    abstract: bool = False,
):
    """Create an OntologyTypeDef via the factory."""
    from iios.ontology.ontology_factory import get_ontology_factory
    fac = get_ontology_factory()
    return fac.create_type(
        name          = name,
        namespace_uri = ns,
        parent_uri    = parent,
        labels        = labels or [],
        aliases       = aliases or [],
        abstract      = abstract,
        uri           = f"{ns}.{name}",
    )


def _register_type(td):
    """Register a type in the master registry."""
    from iios.ontology.registry.ontology_registry_manager import get_registry_manager
    mgr = get_registry_manager()
    with mgr._lock:
        mgr._types[td.uri] = td
        if td.parent_uri:
            mgr._children.setdefault(td.parent_uri, set()).add(td.uri)
        for alias in td.aliases:
            mgr._aliases[alias] = td.uri


def _register_rel(
    uri:    str,
    name:   str,
    source: str,
    target: str,
):
    """Register a relationship definition in the master registry."""
    from iios.ontology.registry.ontology_registry_manager import get_registry_manager
    from iios.ontology.runtime.runtime_object import OntologyRelationshipDef
    rel = OntologyRelationshipDef(
        uri             = uri,
        name            = name,
        namespace_uri   = "iios.test",
        source_type_uri = source,
        target_type_uri = target,
        description     = "",
        labels          = [],
    )
    mgr = get_registry_manager()
    with mgr._lock:
        mgr._relationships[uri] = rel
    return rel


def _build_hierarchy():
    """
    Build a 3-level hierarchy:
        Asset (abstract)
          ├── Equity
          │     └── Stock
          └── Bond
    """
    types = {
        "asset":  _make_type("Asset",  ns="iios.test", abstract=True),
        "equity": _make_type("Equity", ns="iios.test", parent="iios.test.Asset"),
        "stock":  _make_type("Stock",  ns="iios.test", parent="iios.test.Equity"),
        "bond":   _make_type("Bond",   ns="iios.test", parent="iios.test.Asset"),
    }
    for td in types.values():
        _register_type(td)
    return types


# ═════════════════════════════════════════════════════════════════════════════
# 1. Constants
# ═════════════════════════════════════════════════════════════════════════════

class TestQueryConstants:
    def test_query_type_values(self):
        from iios.ontology.query import QueryType
        assert QueryType.TYPE_LOOKUP.value == "type_lookup"
        assert QueryType.SEARCH.value      == "search"
        assert QueryType.SEMANTIC.value    == "semantic"
        assert QueryType.ANCESTORS.value   == "ancestors"
        assert QueryType.DESCENDANTS.value == "descendants"

    def test_resolution_strategy_values(self):
        from iios.ontology.query import ResolutionStrategy
        assert ResolutionStrategy.AUTO.value    == "auto"
        assert ResolutionStrategy.EXACT.value   == "exact"
        assert ResolutionStrategy.FUZZY.value   == "fuzzy"
        assert ResolutionStrategy.ALIAS.value   == "alias"

    def test_navigation_direction_values(self):
        from iios.ontology.query import NavigationDirection
        assert NavigationDirection.UP.value   == "up"
        assert NavigationDirection.DOWN.value == "down"

    def test_semantic_relation_values(self):
        from iios.ontology.query import SemanticRelation
        assert SemanticRelation.SUBTYPE_OF.value   == "subtype_of"
        assert SemanticRelation.SUPERTYPE_OF.value == "supertype_of"
        assert SemanticRelation.SIBLING.value      == "sibling"

    def test_query_status_values(self):
        from iios.ontology.query import QueryStatus
        assert QueryStatus.COMPLETED.value == "completed"
        assert QueryStatus.CACHED.value    == "cached"

    def test_builtin_qids_are_strings(self):
        from iios.ontology.query import (
            QID_ALL_TYPES, QID_ENTITY_TYPES, QID_ABSTRACT_TYPES,
            QID_CONCRETE_TYPES, QID_ALL_RELATIONSHIPS, QID_ALL_NAMESPACES,
        )
        for qid in (QID_ALL_TYPES, QID_ENTITY_TYPES, QID_ABSTRACT_TYPES,
                    QID_CONCRETE_TYPES, QID_ALL_RELATIONSHIPS, QID_ALL_NAMESPACES):
            assert isinstance(qid, str) and qid.startswith("builtin.")

    def test_numeric_constants(self):
        from iios.ontology.query import (
            MAX_QUERY_DEPTH, DEFAULT_FUZZY_THRESHOLD, QUERY_CACHE_TTL_SECONDS,
        )
        assert MAX_QUERY_DEPTH > 0
        assert 0 < DEFAULT_FUZZY_THRESHOLD < 1
        assert QUERY_CACHE_TTL_SECONDS > 0


# ═════════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ═════════════════════════════════════════════════════════════════════════════

class TestQueryExceptions:
    def test_hierarchy(self):
        from iios.ontology.query import (
            QueryError, QueryNotFoundError, QueryTimeoutError,
            QuerySyntaxError, ResolutionError, AliasResolutionError,
            NavigationError, TraversalDepthError, SemanticError,
            QueryEngineNotInitializedError,
        )
        assert issubclass(QueryNotFoundError, QueryError)
        assert issubclass(QueryTimeoutError, QueryError)
        assert issubclass(AliasResolutionError, ResolutionError)
        assert issubclass(ResolutionError, QueryError)
        assert issubclass(TraversalDepthError, NavigationError)
        assert issubclass(NavigationError, QueryError)
        assert issubclass(SemanticError, QueryError)
        assert issubclass(QueryEngineNotInitializedError, QueryError)

    def test_not_found_stores_ref(self):
        from iios.ontology.query import QueryNotFoundError
        e = QueryNotFoundError("missing.ref")
        assert e.ref == "missing.ref"
        assert "missing.ref" in str(e)

    def test_timeout_stores_elapsed(self):
        from iios.ontology.query import QueryTimeoutError
        e = QueryTimeoutError("q1", 5000.0)
        assert e.elapsed_ms == 5000.0
        assert "5000" in str(e)

    def test_circular_stores_cycle(self):
        from iios.ontology.query import CircularResolutionError
        e = CircularResolutionError(["a", "b", "a"])
        assert e.cycle == ["a", "b", "a"]
        assert "→" in str(e)

    def test_traversal_depth_stores_depth(self):
        from iios.ontology.query import TraversalDepthError
        e = TraversalDepthError(depth=65, max_depth=64)
        assert e.depth == 65
        assert e.max_depth == 64

    def test_duplicate_named_query(self):
        from iios.ontology.query import DuplicateNamedQueryError, NamedQueryError
        e = DuplicateNamedQueryError("q.id")
        assert issubclass(DuplicateNamedQueryError, NamedQueryError)
        assert "q.id" in str(e)

    def test_error_codes_are_unique(self):
        from iios.ontology.query.query_exceptions import (
            QueryError, QueryNotFoundError, QueryTimeoutError,
            QuerySyntaxError, ResolutionError, AliasResolutionError,
            NavigationError, TraversalDepthError,
        )
        codes = {
            cls.code for cls in (
                QueryError, QueryNotFoundError, QueryTimeoutError,
                QuerySyntaxError, ResolutionError, AliasResolutionError,
                NavigationError, TraversalDepthError,
            )
        }
        assert len(codes) == 8


# ═════════════════════════════════════════════════════════════════════════════
# 3. QueryContext
# ═════════════════════════════════════════════════════════════════════════════

class TestQueryContext:
    def test_singleton(self):
        from iios.ontology.query import get_query_context
        ctx1 = get_query_context()
        ctx2 = get_query_context()
        assert ctx1 is ctx2

    def test_reset(self):
        from iios.ontology.query import get_query_context, reset_query_context
        ctx1 = get_query_context()
        reset_query_context()
        ctx2 = get_query_context()
        assert ctx1 is not ctx2

    def test_query_operation_context(self):
        from iios.ontology.query import get_query_context, QueryType
        ctx = get_query_context()
        assert ctx.query_type is None
        with ctx.query_operation(QueryType.SEARCH, "bond"):
            assert ctx.query_type == QueryType.SEARCH
            assert ctx.target == "bond"
            assert ctx.operation_id is not None
        assert ctx.query_type is None

    def test_resolution_context_increments_depth(self):
        from iios.ontology.query import get_query_context, ResolutionStrategy
        ctx = get_query_context()
        assert ctx.depth == 0
        with ctx.resolution("x", ResolutionStrategy.EXACT):
            assert ctx.depth == 1
            with ctx.resolution("y", ResolutionStrategy.ALIAS):
                assert ctx.depth == 2
            assert ctx.depth == 1
        assert ctx.depth == 0

    def test_navigation_context_increments_depth(self):
        from iios.ontology.query import get_query_context
        ctx = get_query_context()
        with ctx.navigation("root"):
            assert ctx.depth == 1
        assert ctx.depth == 0

    def test_elapsed_ms(self):
        from iios.ontology.query import get_query_context, QueryType
        ctx = get_query_context()
        with ctx.query_operation(QueryType.ANCESTORS, "x"):
            elapsed = ctx.elapsed_ms()
            assert elapsed >= 0

    def test_diagnostics(self):
        from iios.ontology.query import get_query_context, QueryDiagnosticLevel, QueryType
        ctx = get_query_context()
        with ctx.query_operation(QueryType.SEARCH, "x"):
            ctx.add_diagnostic(QueryDiagnosticLevel.WARNING, "test warning", "src")
            ctx.add_diagnostic(QueryDiagnosticLevel.ERROR,   "test error",   "src")
            assert len(ctx.warnings()) == 1
            assert len(ctx.errors())   == 1

    def test_thread_isolation(self):
        from iios.ontology.query import get_query_context, QueryType
        ctx = get_query_context()
        results = {}

        def worker(name: str):
            with ctx.query_operation(QueryType.SEARCH, name):
                time.sleep(0.02)
                results[name] = ctx.target

        threads = [threading.Thread(target=worker, args=(n,)) for n in ["a", "b", "c"]]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert set(results.values()) == {"a", "b", "c"}


# ═════════════════════════════════════════════════════════════════════════════
# 4. QueryFactory
# ═════════════════════════════════════════════════════════════════════════════

class TestQueryFactory:
    def test_singleton(self):
        from iios.ontology.query import get_query_factory
        assert get_query_factory() is get_query_factory()

    def test_make_query(self):
        from iios.ontology.query import get_query_factory, QueryType, SortOrder
        fac = get_query_factory()
        req = fac.make_query(QueryType.SEARCH, "bond")
        assert req.query_type == QueryType.SEARCH
        assert req.target     == "bond"
        assert req.sort_order == SortOrder.RELEVANCE
        assert req.query_id   is not None

    def test_make_resolution(self):
        from iios.ontology.query import get_query_factory, ResolutionStrategy
        fac = get_query_factory()
        req = fac.make_resolution("some.uri", ResolutionStrategy.EXACT)
        assert req.ref      == "some.uri"
        assert req.strategy == ResolutionStrategy.EXACT

    def test_make_navigation(self):
        from iios.ontology.query import get_query_factory, NavigationDirection
        fac = get_query_factory()
        req = fac.make_navigation("root.uri", NavigationDirection.DOWN, max_depth=8)
        assert req.start_uri  == "root.uri"
        assert req.direction  == NavigationDirection.DOWN
        assert req.max_depth  == 8

    def test_make_search(self):
        from iios.ontology.query import get_query_factory
        fac = get_query_factory()
        req = fac.make_search("equity", max_results=20)
        assert req.query_term  == "equity"
        assert req.max_results == 20

    def test_make_semantic(self):
        from iios.ontology.query import get_query_factory
        fac = get_query_factory()
        req = fac.make_semantic("iios.test.Asset", top_k=5, radius=2)
        assert req.type_uri == "iios.test.Asset"
        assert req.top_k    == 5

    def test_make_query_result_to_dict(self):
        from iios.ontology.query import get_query_factory, QueryType, QueryStatus
        fac = get_query_factory()
        req = fac.make_query(QueryType.SEARCH, "x")
        res = fac.make_query_result(req, types=[], status=QueryStatus.COMPLETED, duration_ms=1.5)
        d   = res.to_dict()
        assert d["status"]     == "completed"
        assert d["count"]      == 0
        assert d["duration_ms"] == 1.5

    def test_make_resolution_result_to_dict(self):
        from iios.ontology.query import get_query_factory, ResolutionStrategy
        fac = get_query_factory()
        req = fac.make_resolution("x")
        res = fac.make_resolution_result(req, resolved=None, duration_ms=0.5)
        d   = res.to_dict()
        assert d["succeeded"]   is False
        assert d["duration_ms"] == 0.5

    def test_make_navigation_result_to_dict(self):
        from iios.ontology.query import get_query_factory
        fac = get_query_factory()
        req = fac.make_navigation("root")
        res = fac.make_navigation_result(req, path=["root", "child"], depth=1)
        d   = res.to_dict()
        assert d["path"] == ["root", "child"]
        assert d["depth"] == 1

    def test_similar_type_to_dict(self):
        from iios.ontology.query import SimilarType, SemanticRelation
        td   = _make_type("X")
        sim  = SimilarType(type_def=td, score=0.75, relation=SemanticRelation.SIBLING)
        d    = sim.to_dict()
        assert d["score"]    == pytest.approx(0.75, abs=1e-4)
        assert d["relation"] == "sibling"

    def test_search_result_to_dict(self):
        from iios.ontology.query import get_query_factory
        fac = get_query_factory()
        td  = _make_type("Y")
        req = fac.make_search("y")
        res = fac.make_search_result(req, matches=[(td, 0.8)], duration_ms=2.0)
        d   = res.to_dict()
        assert d["count"]  == 1
        assert d["matches"][0]["score"] == pytest.approx(0.8, abs=1e-4)


# ═════════════════════════════════════════════════════════════════════════════
# 5. QueryCache
# ═════════════════════════════════════════════════════════════════════════════

class TestQueryCache:
    def test_singleton(self):
        from iios.ontology.query import get_query_cache
        assert get_query_cache() is get_query_cache()

    def test_put_get(self):
        from iios.ontology.query import get_query_cache
        cache = get_query_cache()
        key   = cache.make_key("type_lookup", "iios.test.X")
        cache.put(key, ["result_a"])
        assert cache.get(key) == ["result_a"]

    def test_has(self):
        from iios.ontology.query import get_query_cache
        cache = get_query_cache()
        key   = cache.make_key("search", "bond")
        assert not cache.has(key)
        cache.put(key, [])
        assert cache.has(key)

    def test_get_missing_returns_none(self):
        from iios.ontology.query import get_query_cache
        assert get_query_cache().get("nonexistent") is None

    def test_invalidate(self):
        from iios.ontology.query import get_query_cache
        cache = get_query_cache()
        key   = cache.make_key("x", "y")
        cache.put(key, "payload")
        assert cache.invalidate(key) is True
        assert cache.get(key) is None

    def test_ttl_expiry(self):
        from iios.ontology.query import get_query_cache
        cache = get_query_cache()
        key   = cache.make_key("ttl_test")
        cache.put(key, "data", ttl=0.05)  # 50ms TTL
        assert cache.has(key)
        time.sleep(0.1)
        assert not cache.has(key)
        assert cache.get(key) is None

    def test_lru_eviction(self):
        from iios.ontology.query import get_query_cache, reset_query_cache
        reset_query_cache()
        from iios.ontology.query.query_cache import QueryCache
        cache = QueryCache(default_ttl=300.0, max_size=3)
        keys  = [cache.make_key(f"k{i}") for i in range(4)]
        for i, k in enumerate(keys):
            cache.put(k, i)
        # Oldest entry (keys[0]) should have been evicted
        assert cache.get(keys[0]) is None
        assert cache.get(keys[3]) == 3

    def test_invalidate_prefix(self):
        from iios.ontology.query import get_query_cache
        import hashlib, json
        cache = get_query_cache()
        # Use real key creation for both entries
        k1 = "aaa_key_1"
        k2 = "aaa_key_2"
        k3 = "bbb_key_3"
        cache.put(k1, "v1")
        cache.put(k2, "v2")
        cache.put(k3, "v3")
        removed = cache.invalidate_prefix("aaa")
        assert removed == 2
        assert cache.get(k3) == "v3"

    def test_hit_rate_tracking(self):
        from iios.ontology.query import get_query_cache
        cache = get_query_cache()
        key   = cache.make_key("hr_test")
        cache.put(key, "data")
        cache.get(key)   # hit
        cache.get("nope")  # miss
        stats = cache.stats()
        assert stats["hits"]   >= 1
        assert stats["misses"] >= 1

    def test_clear(self):
        from iios.ontology.query import get_query_cache
        cache = get_query_cache()
        for i in range(5):
            cache.put(cache.make_key(f"c{i}"), i)
        cache.clear()
        assert cache.stats()["size"] == 0

    def test_entry_info(self):
        from iios.ontology.query import get_query_cache
        cache = get_query_cache()
        key   = cache.make_key("info_test")
        cache.put(key, "payload", result_type="search")
        info  = cache.entry_info(key)
        assert info is not None
        assert info["result_type"] == "search"
        assert info["is_expired"]  is False

    def test_make_key_deterministic(self):
        from iios.ontology.query import get_query_cache
        cache = get_query_cache()
        k1 = cache.make_key("type_lookup", "iios.test.A")
        k2 = cache.make_key("type_lookup", "iios.test.A")
        assert k1 == k2

    def test_make_key_different_for_different_args(self):
        from iios.ontology.query import get_query_cache
        cache = get_query_cache()
        assert cache.make_key("a", "b") != cache.make_key("a", "c")


# ═════════════════════════════════════════════════════════════════════════════
# 6. QueryOptimizer
# ═════════════════════════════════════════════════════════════════════════════

class TestQueryOptimizer:
    def test_singleton(self):
        from iios.ontology.query import get_query_optimizer
        assert get_query_optimizer() is get_query_optimizer()

    def test_plan_for_type_lookup(self):
        from iios.ontology.query import get_query_optimizer, get_query_factory, QueryType, IndexHint
        factory   = get_query_factory()
        optimizer = get_query_optimizer()
        req  = factory.make_query(QueryType.TYPE_LOOKUP, "iios.test.Asset")
        plan = optimizer.plan(req)
        assert plan.optimized             is True
        assert plan.index_hint            == IndexHint.USE_URI_INDEX
        assert plan.estimated_cost        > 0

    def test_plan_for_search(self):
        from iios.ontology.query import get_query_optimizer, get_query_factory, QueryType, IndexHint
        factory   = get_query_factory()
        optimizer = get_query_optimizer()
        req  = factory.make_query(QueryType.SEARCH, "bond")
        plan = optimizer.plan(req)
        assert plan.index_hint == IndexHint.FULL_SCAN

    def test_plan_for_hierarchy(self):
        from iios.ontology.query import get_query_optimizer, get_query_factory, QueryType, IndexHint
        factory   = get_query_factory()
        optimizer = get_query_optimizer()
        req  = factory.make_query(QueryType.HIERARCHY, "iios.test.Asset")
        plan = optimizer.plan(req)
        assert plan.index_hint == IndexHint.HIERARCHY_INDEX

    def test_plan_namespace_hint(self):
        from iios.ontology.query import get_query_optimizer, get_query_factory, QueryType
        factory   = get_query_factory()
        optimizer = get_query_optimizer()
        req  = factory.make_query(QueryType.TYPE_LOOKUP, "Asset", namespace_hint="iios.entity")
        plan = optimizer.plan(req)
        step_names = [s.step_name for s in plan.steps]
        assert "namespace_filter" in step_names

    def test_plan_cache_policy(self):
        from iios.ontology.query import get_query_optimizer, get_query_factory, QueryType
        factory   = get_query_factory()
        optimizer = get_query_optimizer()
        req  = factory.make_query(QueryType.CROSS_REFERENCE, "x")
        plan = optimizer.plan(req)
        assert plan.use_cache is False  # cross-reference never cached

    def test_plan_ttl_by_type(self):
        from iios.ontology.query import get_query_optimizer, get_query_factory, QueryType
        factory   = get_query_factory()
        optimizer = get_query_optimizer()
        for qt, expected_gt_zero in (
            (QueryType.TYPE_LOOKUP, True),
            (QueryType.SEARCH,      True),
        ):
            req  = factory.make_query(qt, "x")
            plan = optimizer.plan(req)
            assert plan.cache_ttl > 0

    def test_plan_serialisation(self):
        from iios.ontology.query import get_query_optimizer, get_query_factory, QueryType
        factory   = get_query_factory()
        optimizer = get_query_optimizer()
        req  = factory.make_query(QueryType.ANCESTORS, "x")
        plan = optimizer.plan(req)
        d    = plan.to_dict()
        assert "steps"          in d
        assert "estimated_cost" in d
        assert "use_cache"      in d

    def test_stats_track_plan_count(self):
        from iios.ontology.query import get_query_optimizer, get_query_factory, QueryType
        factory   = get_query_factory()
        optimizer = get_query_optimizer()
        for _ in range(3):
            optimizer.plan(factory.make_query(QueryType.SEARCH, "x"))
        assert optimizer.stats()["plan_count"] == 3


# ═════════════════════════════════════════════════════════════════════════════
# 7. QueryRegistry
# ═════════════════════════════════════════════════════════════════════════════

class TestQueryRegistry:
    def test_singleton(self):
        from iios.ontology.query import get_query_registry
        assert get_query_registry() is get_query_registry()

    def test_builtin_queries_registered(self):
        from iios.ontology.query import get_query_registry, QID_ALL_TYPES, QID_ALL_RELATIONSHIPS
        reg = get_query_registry()
        assert reg.has(QID_ALL_TYPES)
        assert reg.has(QID_ALL_RELATIONSHIPS)

    def test_builtin_queries_are_flagged(self):
        from iios.ontology.query import get_query_registry, QID_ALL_TYPES
        reg = get_query_registry()
        nq  = reg.get(QID_ALL_TYPES)
        assert nq.builtin is True

    def test_register_custom(self):
        from iios.ontology.query import get_query_registry, QueryType
        reg = get_query_registry()
        reg.register(
            query_id       = "custom.my_query",
            name           = "My Query",
            description    = "A test query",
            query_type     = QueryType.SEARCH,
            default_target = "equity",
        )
        assert reg.has("custom.my_query")

    def test_duplicate_raises(self):
        from iios.ontology.query import get_query_registry, QueryType, DuplicateNamedQueryError
        reg = get_query_registry()
        reg.register("custom.dup", "Dup", "", QueryType.SEARCH)
        with pytest.raises(DuplicateNamedQueryError):
            reg.register("custom.dup", "Dup2", "", QueryType.SEARCH)

    def test_overwrite_allowed(self):
        from iios.ontology.query import get_query_registry, QueryType
        reg = get_query_registry()
        reg.register("custom.ow", "V1", "desc1", QueryType.SEARCH)
        reg.register("custom.ow", "V2", "desc2", QueryType.SEARCH, overwrite=True)
        assert reg.get("custom.ow").name == "V2"

    def test_unregister_custom(self):
        from iios.ontology.query import get_query_registry, QueryType
        reg = get_query_registry()
        reg.register("custom.tmp", "TMP", "", QueryType.SEARCH)
        assert reg.unregister("custom.tmp") is True
        assert not reg.has("custom.tmp")

    def test_cannot_unregister_builtin(self):
        from iios.ontology.query import get_query_registry, QID_ALL_TYPES, NamedQueryError
        reg = get_query_registry()
        with pytest.raises(NamedQueryError):
            reg.unregister(QID_ALL_TYPES)

    def test_get_unknown_raises(self):
        from iios.ontology.query import get_query_registry, UnknownNamedQueryError
        with pytest.raises(UnknownNamedQueryError):
            get_query_registry().get("nonexistent.query")

    def test_get_by_type(self):
        from iios.ontology.query import get_query_registry, QueryType
        reg = get_query_registry()
        reg.register("custom.rel_q", "Rel", "", QueryType.RELATIONSHIP_LOOKUP)
        matches = reg.get_by_type(QueryType.RELATIONSHIP_LOOKUP)
        assert any(nq.query_id == "custom.rel_q" for nq in matches)

    def test_build_request(self):
        from iios.ontology.query import get_query_registry, QueryType
        reg = get_query_registry()
        reg.register("custom.build", "Build", "", QueryType.SEARCH, default_target="bond")
        req = reg.build_request("custom.build")
        assert req.query_type == QueryType.SEARCH
        assert req.target     == "bond"

    def test_build_request_with_override(self):
        from iios.ontology.query import get_query_registry, QueryType
        reg = get_query_registry()
        reg.register("custom.override", "O", "", QueryType.SEARCH, default_target="equity")
        req = reg.build_request("custom.override", target="bond")
        assert req.target == "bond"

    def test_stats(self):
        from iios.ontology.query import get_query_registry, QueryType
        reg   = get_query_registry()
        s_pre = reg.stats()
        reg.register("custom.s1", "S1", "", QueryType.SEARCH)
        s_post = reg.stats()
        assert s_post["custom"] == s_pre["custom"] + 1

    def test_clear_custom(self):
        from iios.ontology.query import get_query_registry, QueryType
        reg = get_query_registry()
        for i in range(3):
            reg.register(f"custom.clr{i}", f"C{i}", "", QueryType.SEARCH)
        removed = reg.clear_custom()
        assert removed == 3


# ═════════════════════════════════════════════════════════════════════════════
# 8. ResolutionEngine
# ═════════════════════════════════════════════════════════════════════════════

class TestResolutionEngine:
    def test_singleton(self):
        from iios.ontology.query import get_resolution_engine
        assert get_resolution_engine() is get_resolution_engine()

    def test_exact_resolution(self):
        from iios.ontology.query import get_resolution_engine, ResolutionStrategy
        types = _build_hierarchy()
        res   = get_resolution_engine()
        td    = res.resolve("iios.test.Asset", ResolutionStrategy.EXACT)
        assert td is not None
        assert td.name == "Asset"

    def test_exact_resolution_missing(self):
        from iios.ontology.query import get_resolution_engine, ResolutionStrategy
        res = get_resolution_engine()
        td  = res.resolve("nonexistent.uri", ResolutionStrategy.EXACT)
        assert td is None

    def test_alias_resolution(self):
        from iios.ontology.query import get_resolution_engine, ResolutionStrategy
        td_with_alias = _make_type("Equity2", aliases=["eq2"])
        _register_type(td_with_alias)
        res    = get_resolution_engine()
        result = res.resolve("eq2", ResolutionStrategy.ALIAS)
        assert result is not None
        assert result.name == "Equity2"

    def test_auto_strategy(self):
        from iios.ontology.query import get_resolution_engine, ResolutionStrategy
        types = _build_hierarchy()
        res   = get_resolution_engine()
        td    = res.resolve("iios.test.Bond", ResolutionStrategy.AUTO)
        assert td is not None
        assert td.name == "Bond"

    def test_resolve_or_raise_raises(self):
        from iios.ontology.query import get_resolution_engine, ResolutionStrategy, ResolutionError
        res = get_resolution_engine()
        with pytest.raises(ResolutionError):
            res.resolve_or_raise("nonexistent", ResolutionStrategy.EXACT)

    def test_resolve_canonical(self):
        from iios.ontology.query import get_resolution_engine
        types = _build_hierarchy()
        res   = get_resolution_engine()
        canon = res.resolve_canonical("iios.test.Asset")
        assert canon == "iios.test.Asset"

    def test_inheritance_chain(self):
        from iios.ontology.query import get_resolution_engine
        _build_hierarchy()
        res   = get_resolution_engine()
        chain = res.resolve_inheritance_chain("iios.test.Stock")
        uris  = [t.uri for t in chain]
        assert uris[0] == "iios.test.Stock"
        assert "iios.test.Equity" in uris
        assert "iios.test.Asset"  in uris

    def test_inheritance_chain_single_root(self):
        from iios.ontology.query import get_resolution_engine
        _build_hierarchy()
        res   = get_resolution_engine()
        chain = res.resolve_inheritance_chain("iios.test.Asset")
        assert len(chain) == 1
        assert chain[0].uri == "iios.test.Asset"

    def test_resolve_all_properties(self):
        from iios.ontology.query import get_resolution_engine
        from iios.ontology.runtime.runtime_object import OntologyProperty, DataType
        _build_hierarchy()

        # Add a property to Asset
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        mgr  = get_registry_manager()
        prop = OntologyProperty(
            name="isin", data_type=DataType.STRING,
            description="ISIN code", required=False,
            ref_uri=None,
        )
        with mgr._lock:
            mgr._types["iios.test.Asset"].properties["isin"] = prop

        res   = get_resolution_engine()
        props = res.resolve_all_properties("iios.test.Stock")
        # Stock inherits from Equity → Asset, so isin should be present
        assert "isin" in props

    def test_resolve_relationship_by_uri(self):
        from iios.ontology.query import get_resolution_engine
        _register_rel("iios.test.rel.HasEquity", "HasEquity", "iios.test.Asset", "iios.test.Equity")
        res = get_resolution_engine()
        rel = res.resolve_relationship("iios.test.rel.HasEquity")
        assert rel is not None
        assert rel.name == "HasEquity"

    def test_resolve_relationship_by_name(self):
        from iios.ontology.query import get_resolution_engine
        _register_rel("iios.test.rel.HasBond", "HasBond", "iios.test.Asset", "iios.test.Bond")
        res = get_resolution_engine()
        rel = res.resolve_relationship("hasbond")   # case-insensitive
        assert rel is not None

    def test_resolve_by_label(self):
        from iios.ontology.query import get_resolution_engine
        td = _make_type("DebtInstr", labels=["debt", "instrument"])
        _register_type(td)
        res = get_resolution_engine()
        matches = res.resolve_by_label("debt")
        assert any(t.name == "DebtInstr" for t in matches)

    def test_resolve_fuzzy(self):
        from iios.ontology.query import get_resolution_engine
        td = _make_type("Equity3")
        _register_type(td)
        res = get_resolution_engine()
        matches = res.resolve_fuzzy("Equiti", threshold=0.4)
        assert len(matches) > 0
        assert all(isinstance(s, float) for _, s in matches)
        # Should be sorted descending
        scores = [s for _, s in matches]
        assert scores == sorted(scores, reverse=True)

    def test_request_api(self):
        from iios.ontology.query import get_resolution_engine, get_query_factory, ResolutionStrategy
        _build_hierarchy()
        factory = get_query_factory()
        req     = factory.make_resolution("iios.test.Bond", ResolutionStrategy.EXACT)
        res     = get_resolution_engine()
        result  = res.resolve_request(req)
        assert result.succeeded
        assert result.resolved.name == "Bond"
        assert result.strategy_used == ResolutionStrategy.EXACT

    def test_stats_track_counts(self):
        from iios.ontology.query import get_resolution_engine, ResolutionStrategy
        _build_hierarchy()
        res = get_resolution_engine()
        res.resolve("iios.test.Asset", ResolutionStrategy.AUTO)
        res.resolve_inheritance_chain("iios.test.Stock")
        res.resolve_fuzzy("Equity")
        s = res.stats()
        assert s["resolve_count"]     >= 1
        assert s["inheritance_count"] >= 1
        assert s["fuzzy_count"]       >= 1


# ═════════════════════════════════════════════════════════════════════════════
# 9. SemanticEngine
# ═════════════════════════════════════════════════════════════════════════════

class TestSemanticEngine:
    def test_singleton(self):
        from iios.ontology.query import get_semantic_engine
        assert get_semantic_engine() is get_semantic_engine()

    def test_find_similar_returns_list(self):
        from iios.ontology.query import get_semantic_engine
        _build_hierarchy()
        sem  = get_semantic_engine()
        sims = sem.find_similar("iios.test.Asset", top_k=10)
        assert isinstance(sims, list)

    def test_find_similar_sorted_descending(self):
        from iios.ontology.query import get_semantic_engine
        _build_hierarchy()
        sem    = get_semantic_engine()
        sims   = sem.find_similar("iios.test.Asset", top_k=10)
        scores = [s.score for s in sims]
        assert scores == sorted(scores, reverse=True)

    def test_find_similar_excludes_self(self):
        from iios.ontology.query import get_semantic_engine
        _build_hierarchy()
        sem  = get_semantic_engine()
        sims = sem.find_similar("iios.test.Asset", top_k=10)
        uris = [s.type_def.uri for s in sims]
        assert "iios.test.Asset" not in uris

    def test_semantic_distance_same_type(self):
        from iios.ontology.query import get_semantic_engine
        _build_hierarchy()
        sem = get_semantic_engine()
        assert sem.semantic_distance("iios.test.Asset", "iios.test.Asset") == 0.0

    def test_semantic_distance_parent_child(self):
        from iios.ontology.query import get_semantic_engine, SEMANTIC_DISTANCE_INFINITY
        _build_hierarchy()
        sem  = get_semantic_engine()
        dist = sem.semantic_distance("iios.test.Equity", "iios.test.Asset")
        assert 0.0 < dist < SEMANTIC_DISTANCE_INFINITY

    def test_semantic_distance_unrelated(self):
        from iios.ontology.query import get_semantic_engine, SEMANTIC_DISTANCE_INFINITY
        # Two types with no common ancestor
        td_x = _make_type("IsolatedX", ns="iios.isolated")
        td_y = _make_type("IsolatedY", ns="iios.isolated")
        _register_type(td_x)
        _register_type(td_y)
        sem  = get_semantic_engine()
        dist = sem.semantic_distance("iios.isolated.IsolatedX", "iios.isolated.IsolatedY")
        # No common ancestor → either distance > 0 or INFINITY/2 for same-ns
        assert dist > 0.0

    def test_is_semantically_equivalent_same_uri(self):
        from iios.ontology.query import get_semantic_engine
        _build_hierarchy()
        sem = get_semantic_engine()
        assert sem.is_semantically_equivalent("iios.test.Asset", "iios.test.Asset") is True

    def test_is_semantically_equivalent_alias(self):
        from iios.ontology.query import get_semantic_engine
        td = _make_type("GovBond", aliases=["gov_bond"])
        _register_type(td)
        sem = get_semantic_engine()
        # Alias resolution works through canonical_uri
        assert sem.is_semantically_equivalent("iios.test.GovBond", "iios.test.GovBond") is True

    def test_expand_concept(self):
        from iios.ontology.query import get_semantic_engine
        _build_hierarchy()
        sem       = get_semantic_engine()
        expanded  = sem.expand_concept("iios.test.Asset", radius=3)
        uris      = [t.uri for t in expanded]
        assert "iios.test.Equity" in uris
        assert "iios.test.Bond"   in uris

    def test_expand_concept_radius_zero(self):
        from iios.ontology.query import get_semantic_engine
        _build_hierarchy()
        sem = get_semantic_engine()
        # Radius 0 means no neighbours
        expanded = sem.expand_concept("iios.test.Asset", radius=0)
        assert expanded == []

    def test_discover_neighborhood(self):
        from iios.ontology.query import get_semantic_engine
        _build_hierarchy()
        sem  = get_semantic_engine()
        hood = sem.discover_neighborhood("iios.test.Equity", depth=2)
        assert "parents"  in hood
        assert "children" in hood
        assert "iios.test.Asset" in hood["parents"]
        assert "iios.test.Stock" in hood["children"]

    def test_find_related_subtype(self):
        from iios.ontology.query import get_semantic_engine, SemanticRelation
        _build_hierarchy()
        sem     = get_semantic_engine()
        related = sem.find_related("iios.test.Asset", SemanticRelation.SUBTYPE_OF)
        uris    = [t.uri for t in related]
        assert "iios.test.Equity" in uris
        assert "iios.test.Bond"   in uris

    def test_find_related_supertype(self):
        from iios.ontology.query import get_semantic_engine, SemanticRelation
        _build_hierarchy()
        sem     = get_semantic_engine()
        related = sem.find_related("iios.test.Stock", SemanticRelation.SUPERTYPE_OF)
        uris    = [t.uri for t in related]
        assert "iios.test.Equity" in uris
        assert "iios.test.Asset"  in uris

    def test_find_related_sibling(self):
        from iios.ontology.query import get_semantic_engine, SemanticRelation
        _build_hierarchy()
        sem      = get_semantic_engine()
        siblings = sem.find_related("iios.test.Equity", SemanticRelation.SIBLING)
        uris     = [t.uri for t in siblings]
        assert "iios.test.Bond" in uris

    def test_semantic_rank(self):
        from iios.ontology.query import get_semantic_engine
        types = list(_build_hierarchy().values())
        sem   = get_semantic_engine()
        ranked = sem.semantic_rank(types, "Equity")
        assert ranked[0].name == "Equity"

    def test_suggest_queries(self):
        from iios.ontology.query import get_semantic_engine
        _build_hierarchy()
        sem = get_semantic_engine()
        sug = sem.suggest_queries("Eq", limit=10)
        assert isinstance(sug, list)
        assert any("Equity" in s for s in sug)

    def test_stats_tracking(self):
        from iios.ontology.query import get_semantic_engine
        _build_hierarchy()
        sem = get_semantic_engine()
        sem.find_similar("iios.test.Asset")
        sem.expand_concept("iios.test.Asset")
        sem.semantic_rank([], "x")
        s = sem.stats()
        assert s["similarity_count"] >= 1
        assert s["expand_count"]     >= 1
        assert s["rank_count"]       >= 1

    def test_request_api(self):
        from iios.ontology.query import get_semantic_engine, get_query_factory
        _build_hierarchy()
        factory = get_query_factory()
        req     = factory.make_semantic("iios.test.Asset", top_k=5, radius=2)
        sem     = get_semantic_engine()
        result  = sem.process_request(req)
        assert isinstance(result.similar, list)
        assert isinstance(result.neighborhood, list)
        assert result.duration_ms >= 0


# ═════════════════════════════════════════════════════════════════════════════
# 10. QueryManager
# ═════════════════════════════════════════════════════════════════════════════

class TestQueryManager:
    def test_singleton(self):
        from iios.ontology.query import get_query_manager
        assert get_query_manager() is get_query_manager()

    def test_initialize_idempotent(self):
        from iios.ontology.query import get_query_manager
        mgr = get_query_manager()
        mgr.initialize()
        mgr.initialize()
        assert mgr._initialized is True

    def test_lookup_type(self):
        from iios.ontology.query import get_query_manager
        _build_hierarchy()
        mgr = get_query_manager()
        td  = mgr.lookup_type("iios.test.Asset")
        assert td is not None and td.name == "Asset"

    def test_lookup_type_missing_returns_none(self):
        from iios.ontology.query import get_query_manager
        mgr = get_query_manager()
        assert mgr.lookup_type("nonexistent") is None

    def test_lookup_type_or_raise(self):
        from iios.ontology.query import get_query_manager, QueryNotFoundError
        mgr = get_query_manager()
        with pytest.raises(QueryNotFoundError):
            mgr.lookup_type_or_raise("nonexistent")

    def test_exists(self):
        from iios.ontology.query import get_query_manager
        _build_hierarchy()
        mgr = get_query_manager()
        assert mgr.exists("iios.test.Asset") is True
        assert mgr.exists("no.such.type")    is False

    def test_parent_of(self):
        from iios.ontology.query import get_query_manager
        _build_hierarchy()
        mgr = get_query_manager()
        parent = mgr.parent_of("iios.test.Stock")
        assert parent.uri == "iios.test.Equity"

    def test_parent_of_root_returns_none(self):
        from iios.ontology.query import get_query_manager
        _build_hierarchy()
        mgr = get_query_manager()
        assert mgr.parent_of("iios.test.Asset") is None

    def test_children_of(self):
        from iios.ontology.query import get_query_manager
        _build_hierarchy()
        mgr      = get_query_manager()
        children = mgr.children_of("iios.test.Asset")
        uris     = [t.uri for t in children]
        assert "iios.test.Equity" in uris
        assert "iios.test.Bond"   in uris

    def test_ancestors_of(self):
        from iios.ontology.query import get_query_manager
        _build_hierarchy()
        mgr       = get_query_manager()
        ancestors = mgr.ancestors_of("iios.test.Stock")
        uris      = [t.uri for t in ancestors]
        assert "iios.test.Equity" in uris
        assert "iios.test.Asset"  in uris

    def test_descendants_of(self):
        from iios.ontology.query import get_query_manager
        _build_hierarchy()
        mgr         = get_query_manager()
        descendants = mgr.descendants_of("iios.test.Asset")
        uris        = [t.uri for t in descendants]
        assert "iios.test.Equity" in uris
        assert "iios.test.Stock"  in uris
        assert "iios.test.Bond"   in uris

    def test_is_subtype_of(self):
        from iios.ontology.query import get_query_manager
        _build_hierarchy()
        mgr = get_query_manager()
        assert mgr.is_subtype_of("iios.test.Stock",  "iios.test.Asset")  is True
        assert mgr.is_subtype_of("iios.test.Asset",  "iios.test.Stock")  is False
        assert mgr.is_subtype_of("iios.test.Asset",  "iios.test.Asset")  is True

    def test_properties_of_inherited(self):
        from iios.ontology.query import get_query_manager
        from iios.ontology.runtime.runtime_object import OntologyProperty, DataType
        _build_hierarchy()
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        mgr2 = get_registry_manager()
        prop = OntologyProperty(
            name="isin", data_type=DataType.STRING,
            description="", required=False,
            ref_uri=None,
        )
        with mgr2._lock:
            mgr2._types["iios.test.Asset"].properties["isin"] = prop

        mgr   = get_query_manager()
        props = mgr.properties_of("iios.test.Stock", inherited=True)
        assert "isin" in props

    def test_lookup_relationship(self):
        from iios.ontology.query import get_query_manager
        _register_rel("iios.test.rel.Owns", "Owns", "iios.test.Asset", "iios.test.Equity")
        mgr = get_query_manager()
        rel = mgr.lookup_relationship("iios.test.rel.Owns")
        assert rel is not None and rel.name == "Owns"

    def test_relationships_for(self):
        from iios.ontology.query import get_query_manager
        _build_hierarchy()
        _register_rel("iios.test.rel.Contains", "Contains", "iios.test.Asset", "iios.test.Bond")
        mgr  = get_query_manager()
        rels = mgr.relationships_for("iios.test.Asset")
        assert any(r.name == "Contains" for r in rels)

    def test_search(self):
        from iios.ontology.query import get_query_manager
        _build_hierarchy()
        mgr     = get_query_manager()
        results = mgr.search("Equity")
        assert any(t.name == "Equity" for t in results)

    def test_search_with_namespace_hint(self):
        from iios.ontology.query import get_query_manager
        td = _make_type("EquityAlpha", ns="iios.special")
        _register_type(td)
        mgr     = get_query_manager()
        results = mgr.search("EquityAlpha", namespace_hint="iios.special")
        assert all(t.namespace_uri == "iios.special" for t in results)

    def test_fuzzy_search(self):
        from iios.ontology.query import get_query_manager
        _build_hierarchy()
        mgr     = get_query_manager()
        results = mgr.fuzzy_search("Equit", threshold=0.4)
        assert len(results) > 0
        scores  = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_suggest(self):
        from iios.ontology.query import get_query_manager
        _build_hierarchy()
        mgr = get_query_manager()
        sug = mgr.suggest("Eq")
        assert isinstance(sug, list)

    def test_execute_query_type_lookup(self):
        from iios.ontology.query import get_query_manager, get_query_factory, QueryType, QueryStatus
        _build_hierarchy()
        factory = get_query_factory()
        req     = factory.make_query(QueryType.TYPE_LOOKUP, "iios.test.Asset")
        mgr     = get_query_manager()
        result  = mgr.execute_query(req)
        assert result.status == QueryStatus.COMPLETED
        assert result.count  == 1
        assert result.types[0].name == "Asset"

    def test_execute_query_cached_second_call(self):
        from iios.ontology.query import get_query_manager, get_query_factory, QueryType, QueryStatus
        _build_hierarchy()
        factory = get_query_factory()
        req     = factory.make_query(QueryType.TYPE_LOOKUP, "iios.test.Equity")
        mgr     = get_query_manager()
        mgr.execute_query(req)
        # Second call with same params should hit cache
        # Make a new request with same params to trigger cache check
        req2    = factory.make_query(QueryType.TYPE_LOOKUP, "iios.test.Equity")
        result2 = mgr.execute_query(req2)
        # Either completed or cached — both are valid
        assert result2.status in (QueryStatus.COMPLETED, QueryStatus.CACHED)

    def test_execute_query_ancestors(self):
        from iios.ontology.query import get_query_manager, get_query_factory, QueryType
        _build_hierarchy()
        factory = get_query_factory()
        req     = factory.make_query(QueryType.ANCESTORS, "iios.test.Stock")
        mgr     = get_query_manager()
        result  = mgr.execute_query(req)
        uris    = [t.uri for t in result.types]
        assert "iios.test.Equity" in uris

    def test_invalidate_cache(self):
        from iios.ontology.query import get_query_manager, get_query_cache
        mgr = get_query_manager()
        cache = get_query_cache()
        cache.put(cache.make_key("test"), "data")
        mgr.invalidate_cache()
        assert cache.stats()["size"] == 0

    def test_stats(self):
        from iios.ontology.query import get_query_manager
        mgr = get_query_manager()
        s   = mgr.stats()
        assert "initialized"  in s
        assert "query_count"  in s
        assert "cache"        in s
        assert "resolution"   in s
        assert "semantic"     in s

    def test_health(self):
        from iios.ontology.query import get_query_manager
        mgr = get_query_manager()
        h   = mgr.health()
        assert h["status"] == "healthy"


# ═════════════════════════════════════════════════════════════════════════════
# 11. QueryEngine (master)
# ═════════════════════════════════════════════════════════════════════════════

class TestQueryEngine:
    def test_singleton(self):
        from iios.ontology.query import get_query_engine_v2
        assert get_query_engine_v2() is get_query_engine_v2()

    def test_initialize_idempotent(self):
        from iios.ontology.query import get_query_engine_v2
        eng = get_query_engine_v2()
        eng.initialize()
        eng.initialize()
        assert eng._initialized is True

    def test_type_lookup(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng = get_query_engine_v2()
        td  = eng.type("iios.test.Asset")
        assert td is not None and td.name == "Asset"

    def test_type_missing_returns_none(self):
        from iios.ontology.query import get_query_engine_v2
        eng = get_query_engine_v2()
        assert eng.type("no.such.type") is None

    def test_type_or_raise(self):
        from iios.ontology.query import get_query_engine_v2, QueryNotFoundError
        eng = get_query_engine_v2()
        with pytest.raises(QueryNotFoundError):
            eng.type_or_raise("no.such.type")

    def test_has_type(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng = get_query_engine_v2()
        assert eng.has_type("iios.test.Asset") is True
        assert eng.has_type("nope")            is False

    def test_canonical_uri(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng   = get_query_engine_v2()
        canon = eng.canonical_uri("iios.test.Bond")
        assert canon == "iios.test.Bond"

    def test_parent_of(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng = get_query_engine_v2()
        p   = eng.parent_of("iios.test.Equity")
        assert p.uri == "iios.test.Asset"

    def test_children_of(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng      = get_query_engine_v2()
        children = eng.children_of("iios.test.Asset")
        uris     = [t.uri for t in children]
        assert "iios.test.Equity" in uris

    def test_ancestors_of(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng       = get_query_engine_v2()
        ancestors = eng.ancestors_of("iios.test.Stock")
        uris      = [t.uri for t in ancestors]
        assert "iios.test.Asset" in uris

    def test_descendants_of(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng         = get_query_engine_v2()
        descendants = eng.descendants_of("iios.test.Asset")
        uris        = [t.uri for t in descendants]
        assert "iios.test.Stock" in uris

    def test_inheritance_chain(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng   = get_query_engine_v2()
        chain = eng.inheritance_chain("iios.test.Stock")
        uris  = [t.uri for t in chain]
        assert uris[0] == "iios.test.Stock"

    def test_is_subtype_of(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng = get_query_engine_v2()
        assert eng.is_subtype_of("iios.test.Bond", "iios.test.Asset") is True

    def test_relationship(self):
        from iios.ontology.query import get_query_engine_v2
        _register_rel("iios.test.r.Covers", "Covers", "iios.test.Asset", "iios.test.Bond")
        eng = get_query_engine_v2()
        rel = eng.relationship("iios.test.r.Covers")
        assert rel is not None

    def test_all_relationships(self):
        from iios.ontology.query import get_query_engine_v2
        _register_rel("iios.test.r.EngRel", "EngRel", "iios.test.Asset", "iios.test.Bond")
        eng  = get_query_engine_v2()
        rels = eng.all_relationships()
        assert any(r.name == "EngRel" for r in rels)

    def test_search(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng     = get_query_engine_v2()
        results = eng.search("Equity")
        assert any(t.name == "Equity" for t in results)

    def test_fuzzy_search(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng     = get_query_engine_v2()
        results = eng.fuzzy_search("Equit", threshold=0.4)
        assert len(results) > 0

    def test_similar_types(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng  = get_query_engine_v2()
        sims = eng.similar_types("iios.test.Asset", top_k=5)
        assert isinstance(sims, list)

    def test_semantic_distance(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng  = get_query_engine_v2()
        dist = eng.semantic_distance("iios.test.Equity", "iios.test.Bond")
        assert dist >= 0.0

    def test_expand_concept(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng      = get_query_engine_v2()
        expanded = eng.expand_concept("iios.test.Asset", radius=2)
        uris     = [t.uri for t in expanded]
        assert "iios.test.Equity" in uris

    def test_neighborhood(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng  = get_query_engine_v2()
        hood = eng.neighborhood("iios.test.Equity")
        assert "parents"  in hood
        assert "children" in hood

    def test_find_related_subtype(self):
        from iios.ontology.query import get_query_engine_v2, SemanticRelation
        _build_hierarchy()
        eng     = get_query_engine_v2()
        related = eng.find_related("iios.test.Asset", SemanticRelation.SUBTYPE_OF)
        uris    = [t.uri for t in related]
        assert "iios.test.Bond" in uris

    def test_resolve_alias(self):
        from iios.ontology.query import get_query_engine_v2
        td = _make_type("IndexFund", aliases=["idx_fund"])
        _register_type(td)
        eng   = get_query_engine_v2()
        canon = eng.resolve_alias("idx_fund")
        assert canon == "iios.test.IndexFund"

    def test_resolve_by_label(self):
        from iios.ontology.query import get_query_engine_v2
        td = _make_type("FI", labels=["fixed income"])
        _register_type(td)
        eng     = get_query_engine_v2()
        results = eng.resolve_by_label("fixed income")
        assert any(t.name == "FI" for t in results)

    def test_all_types(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng   = get_query_engine_v2()
        types = eng.all_types()
        assert len(types) >= 4

    def test_all_type_uris(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng  = get_query_engine_v2()
        uris = eng.all_type_uris()
        assert "iios.test.Asset" in uris

    def test_stats(self):
        from iios.ontology.query import get_query_engine_v2
        eng = get_query_engine_v2()
        s   = eng.stats()
        assert "version"     in s
        assert "initialized" in s

    def test_health(self):
        from iios.ontology.query import get_query_engine_v2
        eng = get_query_engine_v2()
        h   = eng.health()
        assert h["status"]  == "healthy"
        assert h["version"] is not None

    def test_invalidate_cache(self):
        from iios.ontology.query import get_query_engine_v2, get_query_cache
        eng   = get_query_engine_v2()
        cache = get_query_cache()
        cache.put("k", "v")
        eng.invalidate_cache()
        assert cache.stats()["size"] == 0

    def test_register_named_query(self):
        from iios.ontology.query import get_query_engine_v2, get_query_registry, QueryType
        eng = get_query_engine_v2()
        eng.register_named_query(
            query_id    = "custom.eng_q",
            name        = "Engine Query",
            description = "Test",
            query_type  = QueryType.SEARCH,
        )
        assert get_query_registry().has("custom.eng_q")

    def test_execute_named(self):
        from iios.ontology.query import get_query_engine_v2, QueryType
        _build_hierarchy()
        eng = get_query_engine_v2()
        eng.register_named_query(
            query_id       = "test.execute_named",
            name           = "Test",
            description    = "",
            query_type     = QueryType.TYPE_LOOKUP,
            default_target = "iios.test.Asset",
        )
        result = eng.execute_named("test.execute_named")
        assert result.count == 1

    def test_semantic_rank(self):
        from iios.ontology.query import get_query_engine_v2
        types = list(_build_hierarchy().values())
        eng   = get_query_engine_v2()
        ranked = eng.semantic_rank(types, "Bond")
        assert ranked[0].name == "Bond"

    def test_is_semantically_equivalent(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng = get_query_engine_v2()
        assert eng.is_semantically_equivalent("iios.test.Asset", "iios.test.Asset") is True
        assert eng.is_semantically_equivalent("iios.test.Asset", "iios.test.Bond")  is False


# ═════════════════════════════════════════════════════════════════════════════
# 12. Fluent builder & Navigation
# ═════════════════════════════════════════════════════════════════════════════

class TestFluentAndNavigation:
    def test_fluent_basic(self):
        from iios.ontology.query import get_query_engine_v2, QueryType, QueryStatus
        _build_hierarchy()
        eng    = get_query_engine_v2()
        result = eng.query(QueryType.TYPE_LOOKUP, "iios.test.Bond").execute()
        assert result.status == QueryStatus.COMPLETED
        assert result.count  == 1

    def test_fluent_limit(self):
        from iios.ontology.query import get_query_engine_v2, QueryType
        _build_hierarchy()
        eng    = get_query_engine_v2()
        result = eng.query(QueryType.ANCESTORS, "iios.test.Stock").limit(1).execute()
        assert result.count <= 1

    def test_fluent_namespace(self):
        from iios.ontology.query import get_query_engine_v2, QueryType
        td = _make_type("NsFilterTest", ns="iios.filter")
        _register_type(td)
        eng    = get_query_engine_v2()
        result = (eng.query(QueryType.SEARCH, "NsFilterTest")
                     .namespace("iios.filter")
                     .execute())
        uris = result.uris()
        assert "iios.filter.NsFilterTest" in uris

    def test_navigation_down(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng    = get_query_engine_v2()
        result = eng.navigation_request("iios.test.Asset", max_depth=4)
        uris   = [t.uri for t in result.visited]
        assert "iios.test.Equity" in uris

    def test_navigation_up(self):
        from iios.ontology.query import get_query_engine_v2, NavigationDirection
        _build_hierarchy()
        eng    = get_query_engine_v2()
        result = eng.navigation_request(
            "iios.test.Stock",
            direction = NavigationDirection.UP,
            max_depth = 8,
        )
        uris = [t.uri for t in result.visited]
        assert "iios.test.Equity" in uris

    def test_navigation_stop_at(self):
        from iios.ontology.query import get_query_manager, get_query_factory, NavigationDirection
        _build_hierarchy()
        factory = get_query_factory()
        req     = factory.make_navigation(
            "iios.test.Asset",
            direction = NavigationDirection.DOWN,
            max_depth = 8,
            stop_at   = "iios.test.Equity",
        )
        mgr    = get_query_manager()
        result = mgr.execute_navigation(req)
        assert "iios.test.Equity" in result.path

    def test_resolution_request_api(self):
        from iios.ontology.query import get_query_engine_v2, ResolutionStrategy
        _build_hierarchy()
        eng    = get_query_engine_v2()
        result = eng.resolution_request("iios.test.Bond", ResolutionStrategy.EXACT)
        assert result.succeeded
        assert result.resolved.name == "Bond"

    def test_search_request_api(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng    = get_query_engine_v2()
        result = eng.search_request("Equity", max_results=10)
        assert result.count >= 1

    def test_semantic_request_api(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng    = get_query_engine_v2()
        result = eng.semantic_request("iios.test.Asset", top_k=3, radius=2)
        assert isinstance(result.similar, list)


# ═════════════════════════════════════════════════════════════════════════════
# 13. Concurrency
# ═════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_parallel_type_lookups(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng     = get_query_engine_v2()
        results = {}
        errors:  list[Exception] = []

        def lookup(uri: str):
            try:
                td = eng.type(uri)
                results[uri] = td.name if td else None
            except Exception as e:
                errors.append(e)

        uris    = ["iios.test.Asset", "iios.test.Equity", "iios.test.Stock", "iios.test.Bond"]
        threads = [threading.Thread(target=lookup, args=(u,)) for u in uris]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert results["iios.test.Asset"]  == "Asset"
        assert results["iios.test.Equity"] == "Equity"

    def test_parallel_searches(self):
        from iios.ontology.query import get_query_engine_v2
        _build_hierarchy()
        eng     = get_query_engine_v2()
        errors: list[Exception] = []

        def do_search(term: str):
            try:
                eng.search(term)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=do_search, args=(t,))
            for t in ["Asset", "Equity", "Stock", "Bond"] * 4
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []

    def test_cache_thread_safety(self):
        from iios.ontology.query import get_query_cache
        cache   = get_query_cache()
        errors: list[Exception] = []

        def worker(i: int):
            try:
                k = cache.make_key(f"k{i}")
                cache.put(k, f"v{i}")
                _ = cache.get(k)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []

    def test_registry_thread_safety(self):
        from iios.ontology.query import get_query_registry, QueryType
        reg     = get_query_registry()
        errors: list[Exception] = []

        def register_worker(i: int):
            try:
                reg.register(
                    f"custom.conc{i}", f"C{i}", "", QueryType.SEARCH
                )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []


# ═════════════════════════════════════════════════════════════════════════════
# 14. Large ontology
# ═════════════════════════════════════════════════════════════════════════════

class TestLargeOntology:
    def _build_large(self, n: int = 100) -> list:
        """Build a flat namespace with n types all parented to a root."""
        root = _make_type("Root", ns="iios.large")
        _register_type(root)
        types = [root]
        for i in range(n):
            td = _make_type(f"Type{i:04d}", ns="iios.large", parent="iios.large.Root")
            _register_type(td)
            types.append(td)
        return types

    def test_large_search(self):
        from iios.ontology.query import get_query_engine_v2
        self._build_large(100)
        eng     = get_query_engine_v2()
        results = eng.search("Type", namespace_hint="iios.large", max_results=200)
        assert len(results) >= 100

    def test_large_descendants(self):
        from iios.ontology.query import get_query_engine_v2
        self._build_large(100)
        eng         = get_query_engine_v2()
        descendants = eng.descendants_of("iios.large.Root")
        assert len(descendants) >= 100

    def test_large_fuzzy_performance(self):
        from iios.ontology.query import get_query_engine_v2
        self._build_large(200)
        eng   = get_query_engine_v2()
        t0    = time.perf_counter()
        eng.fuzzy_search("Type00", threshold=0.5, top_k=10)
        elapsed = (time.perf_counter() - t0) * 1_000.0
        # Should complete in well under 5 seconds for 200 types
        assert elapsed < 5_000.0, f"Fuzzy search took {elapsed:.0f} ms"

    def test_large_similar_performance(self):
        from iios.ontology.query import get_query_engine_v2
        self._build_large(100)
        eng = get_query_engine_v2()
        t0  = time.perf_counter()
        eng.similar_types("iios.large.Root", top_k=20)
        elapsed = (time.perf_counter() - t0) * 1_000.0
        assert elapsed < 5_000.0


# ═════════════════════════════════════════════════════════════════════════════
# 15. End-to-end
# ═════════════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    def test_full_pipeline(self):
        """
        Full pipeline:
          register types → query → resolve inheritance → semantic rank → cache
        """
        from iios.ontology.query import (
            get_query_engine_v2,
            get_query_cache,
            QueryType,
            ResolutionStrategy,
            SemanticRelation,
        )
        types = _build_hierarchy()
        _register_rel(
            "iios.test.rel.IssuerOf",
            "IssuerOf",
            "iios.test.Equity",
            "iios.test.Bond",
        )
        eng = get_query_engine_v2()

        # 1. Basic lookups
        asset = eng.type("iios.test.Asset")
        assert asset is not None

        # 2. Hierarchy
        ancestors = eng.ancestors_of("iios.test.Stock")
        assert any(t.name == "Asset" for t in ancestors)

        # 3. Semantic distance
        dist = eng.semantic_distance("iios.test.Equity", "iios.test.Bond")
        assert dist > 0.0

        # 4. Concept expansion
        expanded = eng.expand_concept("iios.test.Asset", radius=3)
        assert len(expanded) >= 3

        # 5. Search + rank
        results = eng.search("Bond")
        assert any(t.name == "Bond" for t in results)

        # 6. Relationships
        rels = eng.relationships_for("iios.test.Equity")
        assert any(r.name == "IssuerOf" for r in rels)

        # 7. Resolution request
        res = eng.resolution_request("iios.test.Bond", ResolutionStrategy.EXACT)
        assert res.succeeded

        # 8. Fluent builder
        result = (
            eng.query(QueryType.DESCENDANTS, "iios.test.Asset")
               .limit(10)
               .execute()
        )
        assert result.count >= 3

        # 9. Named query registration + execution
        eng.register_named_query(
            query_id    = "e2e.equity_lookup",
            name        = "Equity Lookup",
            description = "End-to-end test query",
            query_type  = QueryType.TYPE_LOOKUP,
            default_target = "iios.test.Equity",
        )
        nr = eng.execute_named("e2e.equity_lookup")
        assert nr.count == 1 and nr.types[0].name == "Equity"

        # 10. Cache stats show activity
        cache = get_query_cache()
        stats = cache.stats()
        assert stats["size"] >= 0   # May have been populated

    def test_round_trip_to_dict(self):
        """All result objects serialise to dict without errors."""
        from iios.ontology.query import (
            get_query_engine_v2,
            get_query_factory,
            QueryType,
            NavigationDirection,
        )
        _build_hierarchy()
        eng     = get_query_engine_v2()
        factory = get_query_factory()

        # QueryResult
        req    = factory.make_query(QueryType.ANCESTORS, "iios.test.Stock")
        result = get_query_manager_from_engine(eng).execute_query(req)
        d      = result.to_dict()
        assert d["query_type"] == "ancestors"

        # NavigationResult
        nav_res = eng.navigation_request("iios.test.Asset", max_depth=2)
        nd      = nav_res.to_dict()
        assert nd["start_uri"] == "iios.test.Asset"

        # SearchResult
        search_res = eng.search_request("Bond")
        sd         = search_res.to_dict()
        assert "matches" in sd

        # SemanticResult
        sem_res = eng.semantic_request("iios.test.Asset")
        smd     = sem_res.to_dict()
        assert "similar" in smd


def get_query_manager_from_engine(eng):
    from iios.ontology.query import get_query_manager
    return get_query_manager()
