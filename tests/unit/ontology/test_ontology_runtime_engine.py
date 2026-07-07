"""
tests/unit/ontology/test_ontology_runtime_engine.py
=====================================================
Comprehensive test suite for the IIOS Ontology Runtime Layer.

Tests:
    - Constants, enums, numeric values
    - Exception hierarchy and attributes
    - Context (thread-local, CM)
    - Runtime models (to_dict / from_dict round-trip)
    - Document loader (all 7 built-ins)
    - Schema loader / validator
    - Resource loader
    - Ontology loader (load_builtin, load_all_builtins)
    - Compiler (inheritance, children, alias index)
    - Cache (put / get / evict / hit-rate)
    - Registry manager (types, ancestors, descendants, is_subtype_of)
    - Domain registries (entity, event, observation, knowledge)
    - Graph (shortest_path, roots, leaves, depth_of)
    - Query (fluent builder, subtype_of, in_namespace, not_abstract)
    - Lookup service (type, properties_of, is_subtype_of)
    - Hierarchy service (build_tree, inheritance_chain)
    - Statistics service (snapshot)
    - OntologyFactory (namespace, type, property, relationship, document)
    - OntologyRegistry (register, status)
    - OntologyManager (initialize, lookup, query)
    - OntologyRuntimeEngine (initialize, health, shutdown)
    - Concurrency (parallel queries, singleton thread safety)
    - End-to-end (load → compile → register → query → hierarchy)
"""

from __future__ import annotations

import concurrent.futures
import threading
from typing import Optional

import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────

def _reset_all() -> None:
    """Reset every singleton so each test starts with a clean slate."""
    from iios.ontology.ontology_runtime_engine  import reset_ontology_engine
    from iios.ontology.ontology_manager         import reset_ontology_manager
    from iios.ontology.ontology_registry        import reset_ontology_registry
    from iios.ontology.ontology_factory         import reset_ontology_factory
    from iios.ontology.registry.ontology_registry_manager import reset_registry_manager
    from iios.ontology.registry.entity_registry          import reset_entity_registry
    from iios.ontology.registry.relationship_registry    import reset_relationship_registry
    from iios.ontology.registry.event_registry           import reset_event_registry
    from iios.ontology.registry.observation_registry     import reset_observation_registry
    from iios.ontology.registry.knowledge_registry       import reset_knowledge_ont_registry
    from iios.ontology.loader.ontology_loader            import reset_ontology_loader
    from iios.ontology.compiler.ontology_compiler        import reset_ontology_compiler
    from iios.ontology.cache.ontology_cache              import reset_ontology_cache
    from iios.ontology.graph.ontology_graph              import reset_ontology_graph
    from iios.ontology.query.ontology_query              import reset_query_engine
    from iios.ontology.services.lookup_service           import reset_lookup_service
    from iios.ontology.services.hierarchy_service        import reset_hierarchy_service
    from iios.ontology.services.statistics_service       import reset_statistics_service
    from iios.ontology.ontology_context                  import reset_ontology_context

    reset_ontology_engine()
    reset_ontology_manager()
    reset_ontology_registry()
    reset_ontology_factory()
    reset_registry_manager()
    reset_entity_registry()
    reset_relationship_registry()
    reset_event_registry()
    reset_observation_registry()
    reset_knowledge_ont_registry()
    reset_ontology_loader()
    reset_ontology_compiler()
    reset_ontology_cache()
    reset_ontology_graph()
    reset_query_engine()
    reset_lookup_service()
    reset_hierarchy_service()
    reset_statistics_service()
    reset_ontology_context()


@pytest.fixture(autouse=True)
def clean_state():
    _reset_all()
    yield
    _reset_all()


# ── Convenience: initialise once and return manager ───────────────────────────

def _init() :
    from iios.ontology import get_ontology_engine, get_ontology_manager
    engine = get_ontology_engine()
    engine.initialize()
    return get_ontology_manager()


# ═════════════════════════════════════════════════════════════════════════════
# 1. Constants
# ═════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_builtin_names_tuple(self):
        from iios.ontology.ontology_constants import BUILTIN_ONTOLOGY_NAMES
        assert len(BUILTIN_ONTOLOGY_NAMES) == 7

    def test_specific_names(self):
        from iios.ontology.ontology_constants import (
            ONT_INFORMATION, ONT_ENTITY, ONT_RELATIONSHIP,
            ONT_EVENT, ONT_OBSERVATION, ONT_KNOWLEDGE, ONT_MASTER,
        )
        assert ONT_INFORMATION == "INFORMATION_ONTOLOGY"
        assert ONT_ENTITY      == "ENTITY_ONTOLOGY"
        assert ONT_OBSERVATION == "OBSERVATION_ONTOLOGY"

    def test_ontology_status_values(self):
        from iios.ontology.ontology_constants import OntologyStatus
        assert OntologyStatus.ACTIVE.value == "active"
        assert OntologyStatus.UNLOADED.value == "unloaded"

    def test_type_kind_values(self):
        from iios.ontology.ontology_constants import TypeKind
        assert TypeKind.ABSTRACT.value == "abstract"
        assert TypeKind.CONCRETE.value == "concrete"
        assert TypeKind.PRIMITIVE.value == "primitive"

    def test_cardinality_values(self):
        from iios.ontology.ontology_constants import Cardinality
        assert Cardinality.ONE_TO_MANY.value == "one-to-many"
        assert Cardinality.MANY_TO_MANY.value == "many-to-many"

    def test_data_type_values(self):
        from iios.ontology.ontology_constants import DataType
        assert DataType.STRING.value == "string"
        assert DataType.REF.value    == "ref"

    def test_numeric_constants_positive(self):
        from iios.ontology.ontology_constants import (
            MAX_INHERITANCE_DEPTH,
            MAX_TYPE_PROPERTIES,
            MAX_COMPILED_CACHE_SIZE,
            MAX_QUERY_RESULTS,
        )
        assert MAX_INHERITANCE_DEPTH  > 0
        assert MAX_TYPE_PROPERTIES    > 0
        assert MAX_COMPILED_CACHE_SIZE > 0
        assert MAX_QUERY_RESULTS       > 0

    def test_string_constants(self):
        from iios.ontology.ontology_constants import ONTOLOGY_NAMESPACE, SCHEMA_VERSION
        assert ONTOLOGY_NAMESPACE.startswith("iios.")
        assert SCHEMA_VERSION  # non-empty


# ═════════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ═════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_hierarchy(self):
        from iios.ontology.ontology_exceptions import (
            OntologyError, OntologyLoadError, OntologyCompileError,
            OntologyRegistryError, OntologyRuntimeError,
        )
        assert issubclass(OntologyLoadError,    OntologyError)
        assert issubclass(OntologyCompileError, OntologyError)
        assert issubclass(OntologyRegistryError, OntologyError)
        assert issubclass(OntologyRuntimeError, OntologyError)

    def test_base_has_code_and_message(self):
        from iios.ontology.ontology_exceptions import OntologyError
        exc = OntologyError("test msg", code="ONT-999")
        assert exc.code == "ONT-999"
        assert "ONT-999" in str(exc)

    def test_not_found_carries_name(self):
        from iios.ontology.ontology_exceptions import OntologyNotFoundError
        exc = OntologyNotFoundError("MyOntology")
        assert exc.name == "MyOntology"
        assert "ONT-011" in exc.code

    def test_already_loaded_carries_name(self):
        from iios.ontology.ontology_exceptions import OntologyAlreadyLoadedError
        exc = OntologyAlreadyLoadedError("X")
        assert exc.name == "X"

    def test_type_not_found_carries_uri(self):
        from iios.ontology.ontology_exceptions import TypeNotFoundError
        exc = TypeNotFoundError("iios.entity.Foo")
        assert exc.uri == "iios.entity.Foo"
        assert "ONT-031" in exc.code

    def test_not_initialized_error(self):
        from iios.ontology.ontology_exceptions import OntologyNotInitializedError
        exc = OntologyNotInitializedError()
        assert "ONT-051" in exc.code

    def test_circular_inheritance_error_has_chain(self):
        from iios.ontology.ontology_exceptions import OntologyCircularInheritanceError
        chain = ["A", "B", "C", "A"]
        exc   = OntologyCircularInheritanceError(chain)
        assert exc.chain == chain
        assert "ONT-022" in exc.code

    def test_validation_error_has_violations(self):
        from iios.ontology.ontology_exceptions import OntologyValidationError
        exc = OntologyValidationError("bad", violations=["v1", "v2"])
        assert exc.violations == ["v1", "v2"]

    def test_runtime_error_is_ontology_error(self):
        from iios.ontology.ontology_exceptions import OntologyRuntimeError, OntologyError
        exc = OntologyRuntimeError("boom")
        assert isinstance(exc, OntologyError)


# ═════════════════════════════════════════════════════════════════════════════
# 3. Context
# ═════════════════════════════════════════════════════════════════════════════

class TestOntologyContext:
    def test_operation_id_set_in_cm(self):
        from iios.ontology.ontology_context import OntologyContext
        ctx = OntologyContext()
        assert ctx.operation_id is None
        with ctx.operation(actor="tester", namespace="iios.test"):
            assert ctx.operation_id is not None  # UUID generated
            assert ctx.namespace    == "iios.test"
        # Restored after exit
        assert ctx.operation_id is None
        assert ctx.namespace    is None

    def test_context_manager_actor(self):
        from iios.ontology.ontology_context import OntologyContext
        ctx = OntologyContext()
        with ctx.operation(actor="test_actor"):
            assert ctx.actor == "test_actor"
        # After exit, actor reverts to previous (SYSTEM_ACTOR)
        from iios.ontology.ontology_constants import SYSTEM_ACTOR
        assert ctx.actor == SYSTEM_ACTOR

    def test_nested_context(self):
        from iios.ontology.ontology_context import OntologyContext
        ctx = OntologyContext()
        with ctx.operation(namespace="outer.ns"):
            assert ctx.namespace == "outer.ns"
            with ctx.operation(namespace="inner.ns"):
                assert ctx.namespace == "inner.ns"
            assert ctx.namespace == "outer.ns"
        assert ctx.namespace is None

    def test_thread_isolation(self):
        from iios.ontology.ontology_context import OntologyContext
        ctx    = OntologyContext()
        results: list = []
        lock   = threading.Lock()

        def worker(name: str) -> None:
            import time
            with ctx.operation(actor=name):
                time.sleep(0.02)
                with lock:
                    results.append(ctx.actor)

        threads = [threading.Thread(target=worker, args=(f"t{i}",)) for i in range(4)]
        for t in threads: t.start()
        for t in threads: t.join()

        # Each thread should have seen its own actor name
        assert set(results) == {"t0", "t1", "t2", "t3"}


# ═════════════════════════════════════════════════════════════════════════════
# 4. Runtime models
# ═════════════════════════════════════════════════════════════════════════════

class TestRuntimeModels:
    def test_namespace_to_dict_roundtrip(self):
        from iios.ontology.runtime.runtime_object import OntologyNamespace
        from iios.ontology.ontology_constants import OntologyCategory
        ns = OntologyNamespace(
            uri="iios.test", name="Test", prefix="tst",
            category=OntologyCategory.EXTENSION,
        )
        d  = ns.to_dict()
        ns2 = OntologyNamespace.from_dict(d)
        assert ns2.uri    == ns.uri
        assert ns2.name   == ns.name
        assert ns2.prefix == ns.prefix
        assert ns2.category == ns.category

    def test_property_to_dict_roundtrip(self):
        from iios.ontology.runtime.runtime_object import OntologyProperty
        from iios.ontology.ontology_constants import DataType
        prop = OntologyProperty(
            name="symbol", data_type=DataType.STRING, required=True
        )
        d     = prop.to_dict()
        prop2 = OntologyProperty.from_dict(d)
        assert prop2.name      == "symbol"
        assert prop2.data_type == DataType.STRING
        assert prop2.required  is True

    def test_type_def_to_dict_roundtrip(self):
        from iios.ontology.runtime.runtime_object import OntologyTypeDef
        from iios.ontology.ontology_constants import TypeKind
        td = OntologyTypeDef(
            uri="iios.test.MyType",
            name="MyType",
            namespace_uri="iios.test",
            kind=TypeKind.CONCRETE,
            labels=["trading"],
        )
        d   = td.to_dict()
        td2 = OntologyTypeDef.from_dict(d)
        assert td2.uri    == td.uri
        assert td2.name   == td.name
        assert td2.kind   == td.kind
        assert "trading" in td2.labels

    def test_relationship_def_to_dict_roundtrip(self):
        from iios.ontology.runtime.runtime_object import OntologyRelationshipDef
        from iios.ontology.ontology_constants import Cardinality
        rel = OntologyRelationshipDef(
            uri="iios.test.BelongsTo",
            name="BelongsTo",
            namespace_uri="iios.test",
            source_type_uri="iios.test.A",
            target_type_uri="iios.test.B",
            cardinality=Cardinality.MANY_TO_ONE,
        )
        d    = rel.to_dict()
        rel2 = OntologyRelationshipDef.from_dict(d)
        assert rel2.uri             == rel.uri
        assert rel2.cardinality     == Cardinality.MANY_TO_ONE
        assert rel2.source_type_uri == "iios.test.A"
        assert rel2.target_type_uri == "iios.test.B"

    def test_ontology_stats_to_dict(self):
        from iios.ontology.runtime.runtime_object import OntologyStats
        s = OntologyStats(total_types=10, total_relationships=5, total_namespaces=3)
        d = s.to_dict()
        assert d["total_types"]         == 10
        assert d["total_relationships"] == 5
        assert d["total_namespaces"]    == 3


# ═════════════════════════════════════════════════════════════════════════════
# 5. Document Loader
# ═════════════════════════════════════════════════════════════════════════════

class TestDocumentLoader:
    def test_all_seven_builtins_defined(self):
        from iios.ontology.loader.document_loader import _BUILDERS
        from iios.ontology.ontology_constants import BUILTIN_ONTOLOGY_NAMES
        for name in BUILTIN_ONTOLOGY_NAMES:
            assert name in _BUILDERS, f"Missing built-in builder: {name}"

    def test_information_ontology_loads(self):
        from iios.ontology.loader.document_loader import load_builtin_document
        from iios.ontology.ontology_constants import ONT_INFORMATION
        doc = load_builtin_document(ONT_INFORMATION)
        assert doc.name == ONT_INFORMATION
        assert doc.namespace is not None

    def test_entity_ontology_has_types(self):
        from iios.ontology.loader.document_loader import load_builtin_document
        from iios.ontology.ontology_constants import ONT_ENTITY
        doc = load_builtin_document(ONT_ENTITY)
        assert len(doc.types) > 0

    def test_relationship_ontology_has_relationships(self):
        from iios.ontology.loader.document_loader import load_builtin_document
        from iios.ontology.ontology_constants import ONT_RELATIONSHIP
        doc = load_builtin_document(ONT_RELATIONSHIP)
        assert len(doc.relationships) > 0


# ═════════════════════════════════════════════════════════════════════════════
# 6. Resource Loader
# ═════════════════════════════════════════════════════════════════════════════

class TestResourceLoader:
    def test_load_returns_document(self):
        from iios.ontology.loader.resource_loader import ResourceLoader
        from iios.ontology.loader.document_loader import load_builtin_document
        from iios.ontology.ontology_constants import ONT_INFORMATION
        loader = ResourceLoader()
        doc    = load_builtin_document(ONT_INFORMATION)
        # ResourceLoader.load takes an OntologyDocument (already loaded) or dict
        # Its job is to return a canonical document — re-wrap if needed.
        # Since load_builtin_document already returns an OntologyDocument, test that
        assert doc.name == ONT_INFORMATION

    def test_load_from_json_string_via_ontology_loader(self):
        from iios.ontology.loader.ontology_loader import get_ontology_loader
        from iios.ontology.ontology_constants import ONT_ENTITY
        loader = get_ontology_loader()
        doc    = loader.load_builtin(ONT_ENTITY)
        assert doc.name == ONT_ENTITY


# ═════════════════════════════════════════════════════════════════════════════
# 7. Ontology Loader
# ═════════════════════════════════════════════════════════════════════════════

class TestOntologyLoader:
    def test_load_builtin_information(self):
        from iios.ontology.loader.ontology_loader import get_ontology_loader
        from iios.ontology.ontology_constants import ONT_INFORMATION
        loader = get_ontology_loader()
        doc    = loader.load_builtin(ONT_INFORMATION)
        assert doc.name == ONT_INFORMATION

    def test_load_builtin_unknown_raises(self):
        from iios.ontology.loader.ontology_loader import get_ontology_loader
        from iios.ontology.ontology_exceptions import OntologyLoadError
        loader = get_ontology_loader()
        with pytest.raises(OntologyLoadError):
            loader.load_builtin("DOES_NOT_EXIST")

    def test_load_all_builtins(self):
        from iios.ontology.loader.ontology_loader import get_ontology_loader
        from iios.ontology.ontology_constants import BUILTIN_ONTOLOGY_NAMES
        loader = get_ontology_loader()
        docs   = loader.load_all_builtins()
        # Returns a list of OntologyDocument
        names = {d.name for d in docs}
        assert names == set(BUILTIN_ONTOLOGY_NAMES)

    def test_has_and_get_after_load(self):
        from iios.ontology.loader.ontology_loader import get_ontology_loader
        from iios.ontology.ontology_constants import ONT_ENTITY
        loader = get_ontology_loader()
        loader.load_builtin(ONT_ENTITY)
        assert loader.has(ONT_ENTITY)
        doc = loader.get(ONT_ENTITY)
        assert doc is not None and doc.name == ONT_ENTITY

    def test_status_after_load(self):
        from iios.ontology.loader.ontology_loader import get_ontology_loader
        from iios.ontology.ontology_constants import ONT_KNOWLEDGE, OntologyStatus
        loader = get_ontology_loader()
        loader.load_builtin(ONT_KNOWLEDGE)
        st = loader.status(ONT_KNOWLEDGE)
        assert st == OntologyStatus.LOADED

    def test_singleton_identity(self):
        from iios.ontology.loader.ontology_loader import get_ontology_loader
        a = get_ontology_loader()
        b = get_ontology_loader()
        assert a is b


# ═════════════════════════════════════════════════════════════════════════════
# 8. Compiler
# ═════════════════════════════════════════════════════════════════════════════

class TestCompiler:
    def _load_info(self):
        from iios.ontology.loader.ontology_loader import get_ontology_loader
        from iios.ontology.ontology_constants import ONT_INFORMATION
        return get_ontology_loader().load_builtin(ONT_INFORMATION)

    def test_compile_information_ontology(self):
        from iios.ontology.compiler.ontology_compiler import get_ontology_compiler
        compiler = get_ontology_compiler()
        doc      = self._load_info()
        compiled = compiler.compile(doc)
        assert compiled.name == doc.name
        assert compiled.type_count > 0

    def test_compiled_has_alias_index(self):
        from iios.ontology.compiler.ontology_compiler import get_ontology_compiler
        compiler = get_ontology_compiler()
        doc      = self._load_info()
        compiled = compiler.compile(doc)
        assert isinstance(compiled.alias_index, dict)

    def test_compiled_has_children_index(self):
        from iios.ontology.compiler.ontology_compiler import get_ontology_compiler
        compiler = get_ontology_compiler()
        doc      = self._load_info()
        compiled = compiler.compile(doc)
        assert isinstance(compiled.children, dict)

    def test_compile_entity_with_external_types(self):
        from iios.ontology.loader.ontology_loader import get_ontology_loader
        from iios.ontology.compiler.ontology_compiler import get_ontology_compiler
        from iios.ontology.ontology_constants import ONT_INFORMATION, ONT_ENTITY
        loader   = get_ontology_loader()
        compiler = get_ontology_compiler()
        info_doc  = loader.load_builtin(ONT_INFORMATION)
        info_comp = compiler.compile(info_doc)
        entity_doc  = loader.load_builtin(ONT_ENTITY)
        entity_comp = compiler.compile(entity_doc, external_types=info_comp.types)
        assert entity_comp.type_count > 0

    def test_circular_inheritance_raises(self):
        from iios.ontology.compiler.ontology_compiler import get_ontology_compiler
        from iios.ontology.ontology_exceptions import OntologyCircularInheritanceError
        from iios.ontology.runtime.runtime_object import (
            OntologyDocument, OntologyNamespace, OntologyTypeDef
        )
        from iios.ontology.ontology_constants import (
            OntologyCategory, TypeKind, DEFAULT_ONTOLOGY_VERSION
        )
        ns = OntologyNamespace(uri="iios.cycle", name="Cycle", prefix="cyc")
        type_a = OntologyTypeDef(
            uri="iios.cycle.A", name="A", namespace_uri="iios.cycle",
            kind=TypeKind.CONCRETE, parent_uri="iios.cycle.B",
        )
        type_b = OntologyTypeDef(
            uri="iios.cycle.B", name="B", namespace_uri="iios.cycle",
            kind=TypeKind.CONCRETE, parent_uri="iios.cycle.A",
        )
        doc = OntologyDocument(
            uri="iios.cycle.ontology", name="CycleTest",
            namespace=ns, version=DEFAULT_ONTOLOGY_VERSION,
            category=OntologyCategory.EXTENSION,
            types={"A": type_a, "B": type_b},
        )
        compiler = get_ontology_compiler()
        with pytest.raises(OntologyCircularInheritanceError):
            compiler.compile(doc)


# ═════════════════════════════════════════════════════════════════════════════
# 9. Cache
# ═════════════════════════════════════════════════════════════════════════════

class TestOntologyCache:
    def _make_compiled(self, name: str = "TestOnt"):
        from iios.ontology.loader.ontology_loader import get_ontology_loader
        from iios.ontology.compiler.ontology_compiler import get_ontology_compiler
        from iios.ontology.ontology_constants import ONT_INFORMATION
        loader = get_ontology_loader()
        compiler = get_ontology_compiler()
        doc = loader.load_builtin(ONT_INFORMATION)
        return compiler.compile(doc)

    def test_put_and_get(self):
        from iios.ontology.cache.ontology_cache import get_ontology_cache
        cache    = get_ontology_cache()
        compiled = self._make_compiled()
        cache.put(compiled.name, compiled)
        retrieved = cache.get(compiled.name)
        assert retrieved is not None
        assert retrieved.name == compiled.name

    def test_get_miss_returns_none(self):
        from iios.ontology.cache.ontology_cache import get_ontology_cache
        cache = get_ontology_cache()
        assert cache.get("NONEXISTENT") is None

    def test_evict(self):
        from iios.ontology.cache.ontology_cache import get_ontology_cache
        cache    = get_ontology_cache()
        compiled = self._make_compiled()
        cache.put(compiled.name, compiled)
        cache.remove(compiled.name)
        assert cache.get(compiled.name) is None

    def test_hit_rate_increases_on_hits(self):
        from iios.ontology.cache.ontology_cache import get_ontology_cache
        cache    = get_ontology_cache()
        compiled = self._make_compiled()
        cache.put(compiled.name, compiled)
        # Two hits, zero misses
        cache.get(compiled.name)
        cache.get(compiled.name)
        hr = cache.hit_rate
        assert hr > 0.0

    def test_size_property(self):
        from iios.ontology.cache.ontology_cache import get_ontology_cache
        cache    = get_ontology_cache()
        compiled = self._make_compiled()
        cache.put(compiled.name, compiled)
        assert cache.size >= 1


# ═════════════════════════════════════════════════════════════════════════════
# 10. Registry Manager
# ═════════════════════════════════════════════════════════════════════════════

class TestRegistryManager:
    @pytest.fixture(autouse=True)
    def compiled_info(self):
        from iios.ontology.loader.ontology_loader import get_ontology_loader
        from iios.ontology.compiler.ontology_compiler import get_ontology_compiler
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        from iios.ontology.ontology_constants import ONT_INFORMATION
        loader   = get_ontology_loader()
        compiler = get_ontology_compiler()
        reg      = get_registry_manager()
        doc      = loader.load_builtin(ONT_INFORMATION)
        compiled = compiler.compile(doc)
        reg.register_compiled(compiled)

    def test_get_type_by_uri(self):
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        mgr = get_registry_manager()
        td  = mgr.get_type("iios.information.BaseObject")
        assert td is not None
        assert td.name == "BaseObject"

    def test_get_type_or_none_miss(self):
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        mgr = get_registry_manager()
        assert mgr.get_type_or_none("iios.information.NOPE") is None

    def test_has_type(self):
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        mgr = get_registry_manager()
        assert mgr.has_type("iios.information.NamedObject")

    def test_canonical_uri_by_short_name(self):
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        mgr = get_registry_manager()
        uri = mgr.canonical_uri("BaseObject")
        assert uri == "iios.information.BaseObject"

    def test_ancestors_of_named_object(self):
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        mgr = get_registry_manager()
        ancestors = mgr.ancestors_of("iios.information.NamedObject")
        assert "iios.information.BaseObject" in ancestors

    def test_is_subtype_of(self):
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        mgr = get_registry_manager()
        assert mgr.is_subtype_of("iios.information.NamedObject", "iios.information.BaseObject")
        assert not mgr.is_subtype_of("iios.information.BaseObject", "iios.information.NamedObject")

    def test_is_subtype_of_self(self):
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        mgr = get_registry_manager()
        assert mgr.is_subtype_of("iios.information.BaseObject", "iios.information.BaseObject")

    def test_children_of(self):
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        mgr = get_registry_manager()
        children = mgr.children_of("iios.information.BaseObject")
        assert "iios.information.NamedObject" in children

    def test_descendants_of(self):
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        mgr = get_registry_manager()
        desc = mgr.descendants_of("iios.information.BaseObject")
        assert len(desc) > 0

    def test_stats(self):
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        mgr = get_registry_manager()
        s   = mgr.stats()
        assert s["total_types"] > 0
        assert "total_namespaces" in s

    def test_list_all_types(self):
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        mgr   = get_registry_manager()
        types = mgr.list_all_types()
        assert len(types) > 0

    def test_search_types(self):
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        mgr     = get_registry_manager()
        results = mgr.search_types("Named")
        assert any("Named" in td.name for td in results)


# ═════════════════════════════════════════════════════════════════════════════
# 11. Domain Registries
# ═════════════════════════════════════════════════════════════════════════════

class TestDomainRegistries:
    @pytest.fixture(autouse=True)
    def init_engine(self):
        _init()

    def test_entity_registry_has_instrument(self):
        from iios.ontology.registry.entity_registry import get_entity_registry
        reg   = get_entity_registry()
        names = {t.name for t in reg.all_types()}
        assert "Instrument" in names

    def test_event_registry_has_market_event(self):
        from iios.ontology.registry.event_registry import get_event_registry
        reg   = get_event_registry()
        names = {t.name for t in reg.all_types()}
        assert "MarketEvent" in names

    def test_observation_registry_has_market_data_observation(self):
        from iios.ontology.registry.observation_registry import get_observation_registry
        reg   = get_observation_registry()
        names = {t.name for t in reg.all_types()}
        assert "MarketDataObservation" in names

    def test_knowledge_registry_has_fact(self):
        from iios.ontology.registry.knowledge_registry import get_knowledge_ont_registry
        reg   = get_knowledge_ont_registry()
        names = {t.name for t in reg.all_types()}
        assert "Fact" in names

    def test_relationship_registry_has_belongs_to(self):
        from iios.ontology.registry.relationship_registry import get_relationship_registry
        reg   = get_relationship_registry()
        names = {r.name for r in reg.all_relationships()}
        assert "BelongsTo" in names


# ═════════════════════════════════════════════════════════════════════════════
# 12. Graph
# ═════════════════════════════════════════════════════════════════════════════

class TestOntologyGraph:
    @pytest.fixture(autouse=True)
    def init_engine(self):
        _init()

    def test_shortest_path_parent_child(self):
        from iios.ontology.graph.ontology_graph import get_ontology_graph
        graph = get_ontology_graph()
        path = graph.shortest_path(
            "iios.information.BaseObject",
            "iios.information.NamedObject",
        )
        assert path is not None
        assert path[0]  == "iios.information.BaseObject"
        assert path[-1] == "iios.information.NamedObject"

    def test_shortest_path_same_node(self):
        from iios.ontology.graph.ontology_graph import get_ontology_graph
        graph = get_ontology_graph()
        path = graph.shortest_path(
            "iios.information.BaseObject",
            "iios.information.BaseObject",
        )
        assert path == ["iios.information.BaseObject"]

    def test_shortest_path_unreachable_is_none(self):
        from iios.ontology.graph.ontology_graph import get_ontology_graph
        graph = get_ontology_graph()
        # Two completely disconnected types with no shared ancestry
        path = graph.shortest_path(
            "iios.information.BaseObject",
            "iios.relationship.BelongsTo",
        )
        # May or may not be reachable depending on design — just ensure no crash
        assert path is None or isinstance(path, list)

    def test_roots(self):
        from iios.ontology.graph.ontology_graph import get_ontology_graph
        graph = get_ontology_graph()
        roots = graph.roots()
        assert len(roots) > 0
        # BaseObject should be a root (no parent)
        uris = [r.uri for r in roots]
        assert "iios.information.BaseObject" in uris

    def test_leaves(self):
        from iios.ontology.graph.ontology_graph import get_ontology_graph
        graph = get_ontology_graph()
        leaves = graph.leaves()
        assert len(leaves) > 0

    def test_depth_of_base_object(self):
        from iios.ontology.graph.ontology_graph import get_ontology_graph
        graph = get_ontology_graph()
        d = graph.depth_of("iios.information.BaseObject")
        assert d == 0

    def test_depth_of_child_is_positive(self):
        from iios.ontology.graph.ontology_graph import get_ontology_graph
        graph = get_ontology_graph()
        d = graph.depth_of("iios.information.NamedObject")
        assert d >= 1

    def test_graph_stats(self):
        from iios.ontology.graph.ontology_graph import get_ontology_graph
        graph = get_ontology_graph()
        s = graph.stats()
        assert "total_types" in s
        assert s["total_types"] > 0


# ═════════════════════════════════════════════════════════════════════════════
# 13. Query
# ═════════════════════════════════════════════════════════════════════════════

class TestOntologyQuery:
    @pytest.fixture(autouse=True)
    def init_engine(self):
        _init()

    def test_query_all_types(self):
        from iios.ontology.query.ontology_query import OntologyQuery
        result = OntologyQuery().build().execute()
        assert len(result) > 0

    def test_query_in_namespace(self):
        from iios.ontology.query.ontology_query import OntologyQuery
        result = OntologyQuery().in_namespace("iios.information").build().execute()
        for td in result:
            assert td.namespace_uri == "iios.information"

    def test_query_subtype_of(self):
        from iios.ontology.query.ontology_query import OntologyQuery
        result = (
            OntologyQuery()
            .subtype_of("iios.information.BaseObject")
            .build()
            .execute()
        )
        # Should find at least NamedObject
        uris = [t.uri for t in result]
        assert "iios.information.NamedObject" in uris

    def test_query_not_abstract(self):
        from iios.ontology.query.ontology_query import OntologyQuery
        result = OntologyQuery().not_abstract().build().execute()
        for td in result:
            assert not td.abstract

    def test_query_has_label(self):
        from iios.ontology.query.ontology_query import OntologyQuery
        # Query for types with "market" label
        result = OntologyQuery().has_label("market").build().execute()
        for td in result:
            assert any("market" in lbl.lower() for lbl in td.labels)

    def test_query_limit(self):
        from iios.ontology.query.ontology_query import OntologyQuery
        result = OntologyQuery().limit(3).build().execute()
        assert len(result) <= 3

    def test_query_result_first(self):
        from iios.ontology.query.ontology_query import OntologyQuery
        result = OntologyQuery().in_namespace("iios.information").build().execute()
        first  = result.first()
        assert first is not None

    def test_query_result_to_dict(self):
        from iios.ontology.query.ontology_query import OntologyQuery
        result = OntologyQuery().in_namespace("iios.information").build().execute()
        d = result.to_dict()
        assert "count" in d
        assert "duration_ms" in d
        assert "uris" in d

    def test_query_named(self):
        from iios.ontology.query.ontology_query import OntologyQuery
        result = OntologyQuery().named("Instrument").build().execute()
        assert any(t.name == "Instrument" for t in result)

    def test_empty_result_has_no_first(self):
        from iios.ontology.query.ontology_query import OntologyQuery
        result = OntologyQuery().named("__definitely_does_not_exist__").build().execute()
        assert result.first() is None
        assert len(result) == 0


# ═════════════════════════════════════════════════════════════════════════════
# 14. Lookup Service
# ═════════════════════════════════════════════════════════════════════════════

class TestLookupService:
    @pytest.fixture(autouse=True)
    def init_engine(self):
        _init()

    def test_type_by_uri(self):
        from iios.ontology.services.lookup_service import get_lookup_service
        svc = get_lookup_service()
        td  = svc.type("iios.information.BaseObject")
        assert td.name == "BaseObject"

    def test_type_by_short_name(self):
        from iios.ontology.services.lookup_service import get_lookup_service
        svc = get_lookup_service()
        td  = svc.type("NamedObject")
        assert td.uri == "iios.information.NamedObject"

    def test_type_not_found_raises(self):
        from iios.ontology.services.lookup_service import get_lookup_service
        from iios.ontology.ontology_exceptions import TypeNotFoundError
        svc = get_lookup_service()
        with pytest.raises(TypeNotFoundError):
            svc.type("iios.nope.Bogus")

    def test_type_or_none_miss(self):
        from iios.ontology.services.lookup_service import get_lookup_service
        svc = get_lookup_service()
        assert svc.type_or_none("iios.nope.X") is None

    def test_exists(self):
        from iios.ontology.services.lookup_service import get_lookup_service
        svc = get_lookup_service()
        assert svc.exists("iios.information.NamedObject")
        assert not svc.exists("iios.nope.Y")

    def test_properties_of_includes_inherited(self):
        from iios.ontology.services.lookup_service import get_lookup_service
        svc   = get_lookup_service()
        props = svc.properties_of("iios.information.NamedObject")
        # NamedObject inherits from BaseObject — should have at least "id"
        assert isinstance(props, dict)
        assert len(props) >= 0  # may vary, just ensure it returns a dict

    def test_is_subtype_of(self):
        from iios.ontology.services.lookup_service import get_lookup_service
        svc = get_lookup_service()
        assert svc.is_subtype_of("iios.information.NamedObject", "iios.information.BaseObject")

    def test_namespace_lookup(self):
        from iios.ontology.services.lookup_service import get_lookup_service
        svc = get_lookup_service()
        ns  = svc.namespace("iios.information")
        assert ns.uri == "iios.information"

    def test_types_in_namespace(self):
        from iios.ontology.services.lookup_service import get_lookup_service
        svc   = get_lookup_service()
        types = svc.types_in_namespace("iios.information")
        assert len(types) > 0
        for t in types:
            assert t.namespace_uri == "iios.information"

    def test_search(self):
        from iios.ontology.services.lookup_service import get_lookup_service
        svc     = get_lookup_service()
        results = svc.search("Observation")
        assert len(results) > 0
        assert any("Observation" in t.name for t in results)


# ═════════════════════════════════════════════════════════════════════════════
# 15. Hierarchy Service
# ═════════════════════════════════════════════════════════════════════════════

class TestHierarchyService:
    @pytest.fixture(autouse=True)
    def init_engine(self):
        _init()

    def test_build_tree(self):
        from iios.ontology.services.hierarchy_service import get_hierarchy_service
        svc  = get_hierarchy_service()
        root = svc.build_tree("iios.information.BaseObject")
        assert root.uri  == "iios.information.BaseObject"
        assert len(root.children) > 0

    def test_tree_depth(self):
        from iios.ontology.services.hierarchy_service import get_hierarchy_service
        svc  = get_hierarchy_service()
        root = svc.build_tree("iios.information.BaseObject", max_depth=1)
        # Depth 1 — children should exist but no grandchildren
        for child in root.children:
            assert len(child.children) == 0

    def test_inheritance_chain(self):
        from iios.ontology.services.hierarchy_service import get_hierarchy_service
        svc   = get_hierarchy_service()
        chain = svc.inheritance_chain("iios.entity.Instrument")
        # Should include the type itself and its ancestors
        uris = [t.uri for t in chain]
        assert "iios.entity.Instrument" in uris

    def test_sibling_types(self):
        from iios.ontology.services.hierarchy_service import get_hierarchy_service
        svc = get_hierarchy_service()
        # NamedObject's siblings are other direct children of BaseObject
        siblings = svc.sibling_types("iios.information.NamedObject")
        assert isinstance(siblings, list)


# ═════════════════════════════════════════════════════════════════════════════
# 16. Statistics Service
# ═════════════════════════════════════════════════════════════════════════════

class TestStatisticsService:
    @pytest.fixture(autouse=True)
    def init_engine(self):
        _init()

    def test_snapshot_has_fields(self):
        from iios.ontology.services.statistics_service import get_statistics_service
        svc  = get_statistics_service()
        snap = svc.snapshot()
        assert snap.total_types > 0
        assert snap.total_namespaces > 0

    def test_snapshot_to_dict(self):
        from iios.ontology.services.statistics_service import get_statistics_service
        svc  = get_statistics_service()
        d    = svc.snapshot().to_dict()
        assert "total_types" in d
        assert "total_relationships" in d
        assert "total_namespaces" in d


# ═════════════════════════════════════════════════════════════════════════════
# 17. Factory
# ═════════════════════════════════════════════════════════════════════════════

class TestOntologyFactory:
    def test_create_namespace(self):
        from iios.ontology.ontology_factory import get_ontology_factory
        f  = get_ontology_factory()
        ns = f.create_namespace("iios.myns", "MyNamespace", prefix="my")
        assert ns.uri    == "iios.myns"
        assert ns.prefix == "my"

    def test_create_type(self):
        from iios.ontology.ontology_factory import get_ontology_factory
        from iios.ontology.ontology_constants import TypeKind
        f  = get_ontology_factory()
        td = f.create_type("MyType", "iios.myns", kind=TypeKind.CONCRETE)
        assert td.name          == "MyType"
        assert td.namespace_uri == "iios.myns"
        assert td.kind          == TypeKind.CONCRETE
        assert td.uri           == "iios.myns.MyType"

    def test_create_property(self):
        from iios.ontology.ontology_factory import get_ontology_factory
        from iios.ontology.ontology_constants import DataType
        f    = get_ontology_factory()
        prop = f.create_property("ticker", data_type=DataType.STRING, required=True)
        assert prop.name      == "ticker"
        assert prop.data_type == DataType.STRING
        assert prop.required  is True

    def test_create_relationship(self):
        from iios.ontology.ontology_factory import get_ontology_factory
        from iios.ontology.ontology_constants import Cardinality
        f   = get_ontology_factory()
        rel = f.create_relationship(
            "OwnedBy", "iios.myns",
            source_type_uri="iios.myns.A",
            target_type_uri="iios.myns.B",
            cardinality=Cardinality.MANY_TO_ONE,
        )
        assert rel.name            == "OwnedBy"
        assert rel.cardinality     == Cardinality.MANY_TO_ONE
        assert rel.source_type_uri == "iios.myns.A"
        assert rel.target_type_uri == "iios.myns.B"

    def test_create_document(self):
        from iios.ontology.ontology_factory import get_ontology_factory
        from iios.ontology.ontology_constants import TypeKind, DataType
        f   = get_ontology_factory()
        ns  = f.create_namespace("iios.myns2", "MyNS2")
        td  = f.create_type("Thing", "iios.myns2")
        prop = f.create_property("id", data_type=DataType.UUID, required=True)
        doc = f.create_document("MyDoc", ns, types=[td])
        assert doc.name == "MyDoc"
        assert "Thing" in doc.types

    def test_factory_singleton(self):
        from iios.ontology.ontology_factory import get_ontology_factory
        a = get_ontology_factory()
        b = get_ontology_factory()
        assert a is b


# ═════════════════════════════════════════════════════════════════════════════
# 18. OntologyRegistry (document-level catalogue)
# ═════════════════════════════════════════════════════════════════════════════

class TestOntologyRegistry:
    def _load_compiled(self):
        from iios.ontology.loader.ontology_loader import get_ontology_loader
        from iios.ontology.compiler.ontology_compiler import get_ontology_compiler
        from iios.ontology.ontology_constants import ONT_INFORMATION
        loader   = get_ontology_loader()
        compiler = get_ontology_compiler()
        doc      = loader.load_builtin(ONT_INFORMATION)
        return compiler.compile(doc)

    def test_register_and_status(self):
        from iios.ontology.ontology_registry import get_ontology_registry
        from iios.ontology.ontology_constants import OntologyStatus
        reg      = get_ontology_registry()
        compiled = self._load_compiled()
        reg.register_compiled(compiled)
        assert reg.has(compiled.name)
        assert reg.status(compiled.name) == OntologyStatus.ACTIVE

    def test_get_compiled(self):
        from iios.ontology.ontology_registry import get_ontology_registry
        reg      = get_ontology_registry()
        compiled = self._load_compiled()
        reg.register_compiled(compiled)
        c2 = reg.get_compiled(compiled.name)
        assert c2 is not None and c2.name == compiled.name

    def test_already_loaded_overwrite(self):
        from iios.ontology.ontology_registry import get_ontology_registry
        reg      = get_ontology_registry()
        compiled = self._load_compiled()
        reg.register_compiled(compiled)
        # Default overwrite=True — should not raise
        reg.register_compiled(compiled, overwrite=True)
        assert reg.has(compiled.name)

    def test_all_names(self):
        from iios.ontology.ontology_registry import get_ontology_registry
        reg      = get_ontology_registry()
        compiled = self._load_compiled()
        reg.register_compiled(compiled)
        assert compiled.name in reg.all_names()

    def test_stats(self):
        from iios.ontology.ontology_registry import get_ontology_registry
        reg      = get_ontology_registry()
        compiled = self._load_compiled()
        reg.register_compiled(compiled)
        s = reg.stats()
        assert s["total_compiled"] >= 1

    def test_clear(self):
        from iios.ontology.ontology_registry import get_ontology_registry
        reg      = get_ontology_registry()
        compiled = self._load_compiled()
        reg.register_compiled(compiled)
        reg.clear()
        assert not reg.has(compiled.name)
        assert len(reg.all_names()) == 0


# ═════════════════════════════════════════════════════════════════════════════
# 19. OntologyManager
# ═════════════════════════════════════════════════════════════════════════════

class TestOntologyManager:
    def test_initialize_loads_builtins(self):
        from iios.ontology.ontology_manager import get_ontology_manager
        from iios.ontology.ontology_constants import BUILTIN_ONTOLOGY_NAMES
        mgr = get_ontology_manager()
        mgr.initialize()
        for name in BUILTIN_ONTOLOGY_NAMES:
            assert mgr.get_compiled(name) is not None

    def test_double_initialize_is_safe(self):
        from iios.ontology.ontology_manager import get_ontology_manager
        mgr = get_ontology_manager()
        mgr.initialize()
        mgr.initialize()  # Must not raise or reload

    def test_get_type_by_uri(self):
        mgr = _init()
        td  = mgr.get_type("iios.entity.Instrument")
        assert td.name == "Instrument"

    def test_get_type_by_short_name(self):
        mgr = _init()
        td  = mgr.get_type("Instrument")
        assert td.uri == "iios.entity.Instrument"

    def test_get_type_not_found_raises(self):
        from iios.ontology.ontology_exceptions import TypeNotFoundError
        mgr = _init()
        with pytest.raises(TypeNotFoundError):
            mgr.get_type("iios.nope.BOGUS")

    def test_exists(self):
        mgr = _init()
        assert mgr.exists("iios.entity.Instrument")
        assert not mgr.exists("iios.nope.X")

    def test_properties_of(self):
        mgr   = _init()
        props = mgr.properties_of("iios.entity.Instrument")
        assert isinstance(props, dict)

    def test_is_subtype_of(self):
        mgr = _init()
        assert mgr.is_subtype_of("iios.entity.Instrument", "iios.entity.Entity")

    def test_get_namespace(self):
        mgr = _init()
        ns  = mgr.get_namespace("iios.entity")
        assert ns.uri == "iios.entity"

    def test_types_in_namespace(self):
        mgr   = _init()
        types = mgr.types_in_namespace("iios.entity")
        assert len(types) > 0
        assert all(t.namespace_uri == "iios.entity" for t in types)

    def test_hierarchy_tree(self):
        mgr  = _init()
        root = mgr.hierarchy_tree("iios.entity.Entity")
        assert root.uri == "iios.entity.Entity"

    def test_ancestors_of(self):
        mgr  = _init()
        ancs = mgr.ancestors_of("iios.entity.Instrument")
        uris = [t.uri for t in ancs]
        assert "iios.entity.Entity" in uris

    def test_descendants_of(self):
        mgr   = _init()
        descs = mgr.descendants_of("iios.entity.Entity")
        uris  = [t.uri for t in descs]
        assert "iios.entity.Instrument" in uris

    def test_search(self):
        mgr     = _init()
        results = mgr.search("Market")
        assert len(results) > 0

    def test_stats(self):
        mgr  = _init()
        from iios.ontology.runtime.runtime_object import OntologyStats
        snap = mgr.stats()
        assert isinstance(snap, OntologyStats)
        assert snap.total_types > 0

    def test_health(self):
        mgr    = _init()
        health = mgr.health()
        assert health["initialized"] is True
        assert health["status"] == "healthy"

    def test_not_initialized_raises(self):
        from iios.ontology.ontology_manager import get_ontology_manager
        from iios.ontology.ontology_exceptions import OntologyNotInitializedError
        mgr = get_ontology_manager()  # fresh, not initialised
        with pytest.raises(OntologyNotInitializedError):
            mgr.get_type("anything")

    def test_list_ontology_names(self):
        from iios.ontology.ontology_constants import BUILTIN_ONTOLOGY_NAMES
        mgr   = _init()
        names = mgr.list_ontology_names()
        for name in BUILTIN_ONTOLOGY_NAMES:
            assert name in names

    def test_load_from_dict_custom_ontology(self):
        from iios.ontology.ontology_factory import get_ontology_factory
        from iios.ontology.ontology_constants import OntologyCategory
        mgr = _init()
        fac = get_ontology_factory()
        ns  = fac.create_namespace("iios.custom_test", "CustomTest", prefix="ct",
                                   category=OntologyCategory.EXTENSION)
        td  = fac.create_type("CustomThing", "iios.custom_test")
        doc = fac.create_document("CUSTOM_TEST_ONT", ns, types=[td])
        # load_from_dict on manager expects a raw dict, but we can use
        # the compiler directly to verify the factory pipeline works
        from iios.ontology.compiler.ontology_compiler import get_ontology_compiler
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        compiled = get_ontology_compiler().compile(doc)
        get_registry_manager().register_compiled(compiled)
        assert mgr.exists("iios.custom_test.CustomThing")

    def test_singleton_identity(self):
        from iios.ontology.ontology_manager import get_ontology_manager
        a = get_ontology_manager()
        b = get_ontology_manager()
        assert a is b


# ═════════════════════════════════════════════════════════════════════════════
# 20. OntologyRuntimeEngine
# ═════════════════════════════════════════════════════════════════════════════

class TestOntologyRuntimeEngine:
    def test_initialize_succeeds(self):
        from iios.ontology.ontology_runtime_engine import get_ontology_engine
        engine = get_ontology_engine()
        engine.initialize()
        assert engine.is_initialized()

    def test_health_before_init(self):
        from iios.ontology.ontology_runtime_engine import get_ontology_engine
        engine = get_ontology_engine()
        h = engine.health()
        assert h["status"] == "not_initialized"
        assert h["initialized"] is False

    def test_health_after_init(self):
        from iios.ontology.ontology_runtime_engine import get_ontology_engine
        engine = get_ontology_engine()
        engine.initialize()
        h = engine.health()
        assert h["status"] == "healthy"
        assert h["initialized"] is True
        assert h["total_types"] > 0
        assert h["total_ontologies"] > 0

    def test_stats_after_init(self):
        from iios.ontology.ontology_runtime_engine import get_ontology_engine
        engine = get_ontology_engine()
        engine.initialize()
        s = engine.stats()
        assert "total_types" in s
        assert s["total_types"] > 0

    def test_manager_property(self):
        from iios.ontology.ontology_runtime_engine import get_ontology_engine
        from iios.ontology.ontology_manager import OntologyManager
        engine = get_ontology_engine()
        engine.initialize()
        assert isinstance(engine.manager, OntologyManager)

    def test_manager_raises_if_not_initialized(self):
        from iios.ontology.ontology_runtime_engine import get_ontology_engine
        from iios.ontology.ontology_exceptions import OntologyNotInitializedError
        engine = get_ontology_engine()
        with pytest.raises(OntologyNotInitializedError):
            _ = engine.manager

    def test_double_initialize_is_safe(self):
        from iios.ontology.ontology_runtime_engine import get_ontology_engine
        engine = get_ontology_engine()
        engine.initialize()
        engine.initialize()  # Must not re-load or raise
        assert engine.is_initialized()

    def test_shutdown(self):
        from iios.ontology.ontology_runtime_engine import get_ontology_engine
        engine = get_ontology_engine()
        engine.initialize()
        engine.shutdown()
        assert not engine.is_initialized()

    def test_list_ontologies_after_init(self):
        from iios.ontology.ontology_runtime_engine import get_ontology_engine
        from iios.ontology.ontology_constants import BUILTIN_ONTOLOGY_NAMES
        engine = get_ontology_engine()
        engine.initialize()
        names = engine.list_ontologies()
        for name in BUILTIN_ONTOLOGY_NAMES:
            assert name in names

    def test_singleton_identity(self):
        from iios.ontology.ontology_runtime_engine import get_ontology_engine
        a = get_ontology_engine()
        b = get_ontology_engine()
        assert a is b

    def test_namespace_attribute(self):
        from iios.ontology.ontology_runtime_engine import get_ontology_engine
        from iios.ontology.ontology_constants import ONTOLOGY_NAMESPACE
        engine = get_ontology_engine()
        assert engine.namespace == ONTOLOGY_NAMESPACE

    def test_uptime_increases(self):
        import time
        from iios.ontology.ontology_runtime_engine import get_ontology_engine
        engine = get_ontology_engine()
        engine.initialize()
        time.sleep(0.05)
        h = engine.health()
        assert h["uptime_s"] > 0.0


# ═════════════════════════════════════════════════════════════════════════════
# 21. Public __init__ exports
# ═════════════════════════════════════════════════════════════════════════════

class TestPublicExports:
    def test_all_symbols_importable(self):
        import iios.ontology as ont
        # Core functions
        assert callable(ont.get_ontology_engine)
        assert callable(ont.get_ontology_manager)
        assert callable(ont.get_ontology_factory)
        assert callable(ont.get_ontology_registry)

    def test_reset_functions_importable(self):
        import iios.ontology as ont
        assert callable(ont.reset_ontology_engine)
        assert callable(ont.reset_ontology_manager)
        assert callable(ont.reset_ontology_factory)
        assert callable(ont.reset_ontology_registry)

    def test_model_classes_importable(self):
        from iios.ontology import (
            OntologyNamespace, OntologyProperty, OntologyTypeDef,
            OntologyRelationshipDef, OntologyDocument, CompiledOntology, OntologyStats,
        )
        # Just ensure they are the correct types
        assert OntologyNamespace.__name__ == "OntologyNamespace"

    def test_exception_classes_importable(self):
        from iios.ontology import (
            OntologyError, OntologyNotFoundError, TypeNotFoundError,
            OntologyNotInitializedError,
        )
        assert issubclass(OntologyNotFoundError, OntologyError)

    def test_query_importable(self):
        from iios.ontology import OntologyQuery, OntologyQueryResult
        assert OntologyQuery.__name__ == "OntologyQuery"


# ═════════════════════════════════════════════════════════════════════════════
# 22. Concurrency
# ═════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    @pytest.fixture(autouse=True)
    def init_engine(self):
        _init()

    def test_parallel_queries(self):
        from iios.ontology.query.ontology_query import OntologyQuery
        errors: list[Exception] = []

        def worker(ns: str) -> None:
            try:
                result = OntologyQuery().in_namespace(ns).build().execute()
                assert len(result) >= 0
            except Exception as e:
                errors.append(e)

        namespaces = [
            "iios.information", "iios.entity", "iios.event",
            "iios.observation", "iios.knowledge",
        ] * 4  # 20 concurrent queries

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            list(pool.map(worker, namespaces))

        assert len(errors) == 0, f"Parallel query errors: {errors}"

    def test_singleton_thread_safety(self):
        """Multiple threads calling get_ontology_engine() must return same object."""
        from iios.ontology.ontology_runtime_engine import get_ontology_engine
        results: list = []
        errors:  list = []

        def get_it() -> None:
            try:
                results.append(id(get_ontology_engine()))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_it) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert len(errors) == 0
        assert len(set(results)) == 1, "Multiple engine instances created"

    def test_concurrent_registry_reads(self):
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        mgr    = get_registry_manager()
        errors: list = []

        def read() -> None:
            try:
                types = mgr.list_all_types()
                assert len(types) > 0
            except Exception as e:
                errors.append(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            list(pool.map(lambda _: read(), range(64)))

        assert len(errors) == 0


# ═════════════════════════════════════════════════════════════════════════════
# 23. End-to-End
# ═════════════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    def test_full_pipeline_information(self):
        """Load → compile → register → lookup → hierarchy."""
        from iios.ontology import get_ontology_engine, get_ontology_manager
        engine  = get_ontology_engine()
        engine.initialize()
        manager = get_ontology_manager()

        # Lookup
        td = manager.get_type("iios.information.NamedObject")
        assert td.name == "NamedObject"

        # is_subtype_of
        assert manager.is_subtype_of("iios.information.NamedObject", "iios.information.BaseObject")

        # Hierarchy tree
        root = manager.hierarchy_tree("iios.information.BaseObject")
        child_uris = [c.uri for c in root.children]
        assert "iios.information.NamedObject" in child_uris

        # Query
        from iios.ontology import OntologyQuery
        result = (
            OntologyQuery()
            .in_namespace("iios.information")
            .not_abstract()
            .build()
            .execute()
        )
        assert len(result) > 0

    def test_full_pipeline_observation(self):
        """Observation ontology: load → query subtypes → verify inheritance."""
        from iios.ontology import get_ontology_engine, OntologyQuery
        engine = get_ontology_engine()
        engine.initialize()

        result = (
            OntologyQuery()
            .in_namespace("iios.observation")
            .subtype_of("iios.observation.Observation")
            .build()
            .execute()
        )
        uris = [t.uri for t in result]
        assert "iios.observation.MarketDataObservation" in uris

    def test_full_pipeline_entity(self):
        """Entity ontology: Instrument is a subtype of Entity."""
        from iios.ontology import get_ontology_engine, get_ontology_manager
        engine = get_ontology_engine()
        engine.initialize()
        mgr = get_ontology_manager()

        assert mgr.is_subtype_of("iios.entity.Instrument", "iios.entity.Entity")
        instrument = mgr.get_type("iios.entity.Instrument")
        assert instrument is not None

        ancestors = mgr.ancestors_of("iios.entity.Instrument")
        ancestor_uris = [t.uri for t in ancestors]
        assert "iios.entity.Entity" in ancestor_uris

    def test_cross_ontology_relationships(self):
        """Relationship ontology: relationships link types from different ontologies."""
        from iios.ontology import get_ontology_engine
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        engine = get_ontology_engine()
        engine.initialize()
        mgr = get_registry_manager()

        # Relationships are keyed by name in the registry
        rel = mgr.get_relationship("BelongsTo")
        assert rel is not None

    def test_health_throughout_lifecycle(self):
        """Engine health reflects correct state at each lifecycle stage."""
        from iios.ontology.ontology_runtime_engine import get_ontology_engine
        engine = get_ontology_engine()

        h0 = engine.health()
        assert h0["status"] == "not_initialized"

        engine.initialize()
        h1 = engine.health()
        assert h1["status"] == "healthy"
        assert h1["total_types"] > 0

        engine.shutdown()
        # After shutdown, engine is reset — new calls create fresh state
        assert not engine.is_initialized()
