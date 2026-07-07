"""
iios/ontology/ontology_manager.py
====================================
High-level service façade for the Ontology Runtime Layer.

External callers should use OntologyManager as the primary entry point.
It coordinates loader → compiler → cache → registry_manager in a single
call and exposes all runtime services through a clean API.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from .ontology_constants  import BUILTIN_ONTOLOGY_NAMES, OntologyStatus
from .ontology_exceptions import OntologyNotInitializedError, OntologyNotFoundError
from .runtime.runtime_object import (
    CompiledOntology,
    OntologyDocument,
    OntologyNamespace,
    OntologyProperty,
    OntologyRelationshipDef,
    OntologyStats,
    OntologyTypeDef,
)
from .loader.ontology_loader   import get_ontology_loader
from .compiler.ontology_compiler import get_ontology_compiler
from .cache.ontology_cache     import get_ontology_cache
from .registry.ontology_registry_manager import get_registry_manager
from .ontology_registry        import get_ontology_registry
from .query.ontology_query     import OntologyQuery, OntologyQueryResult, get_query_engine
from .services.lookup_service  import get_lookup_service
from .services.hierarchy_service import HierarchyNode, get_hierarchy_service
from .services.statistics_service import get_statistics_service
from .graph.ontology_graph     import get_ontology_graph

__all__ = [
    "OntologyManager",
    "get_ontology_manager",
    "reset_ontology_manager",
]

_LOG  = logging.getLogger("iios.ontology.manager")
_lock = threading.Lock()
_mgr: Optional["OntologyManager"] = None


class OntologyManager:
    """
    Unified façade for all ontology runtime operations.

    Wires together:
    - OntologyLoader        (load raw documents)
    - OntologyCompiler      (compile + resolve inheritance)
    - OntologyCache         (store compiled artefacts)
    - OntologyRegistryManager (type / namespace / relationship lookups)
    - LookupService         (convenient single-call lookups)
    - HierarchyService      (tree traversal)
    - StatisticsService     (runtime stats)
    - OntologyGraph         (graph operations)
    - OntologyQueryEngine   (flexible type queries)
    """

    def __init__(self) -> None:
        self._lock        = threading.RLock()
        self._initialized = False

    # ── Initialisation ─────────────────────────────────────────────────────────

    def initialize(self, load_builtins: bool = True) -> None:
        """
        Bootstrap the ontology runtime.

        Args:
            load_builtins: If True, load and compile all 7 built-in ontologies.
        """
        with self._lock:
            if self._initialized:
                return
            if load_builtins:
                self._load_and_compile_builtins()
            self._initialized = True
            _LOG.info("OntologyManager initialised (builtins=%s)", load_builtins)

    def _load_and_compile_builtins(self) -> None:
        """Load, compile, cache, and register all built-in ontologies."""
        loader   = get_ontology_loader()
        compiler = get_ontology_compiler()
        cache    = get_ontology_cache()
        reg_mgr  = get_registry_manager()
        ont_reg  = get_ontology_registry()

        # Accumulate all compiled external types for cross-document inheritance
        all_types: dict[str, OntologyTypeDef] = {}

        for name in BUILTIN_ONTOLOGY_NAMES:
            try:
                doc      = loader.load_builtin(name)
                compiled = compiler.compile(doc, external_types=all_types)
                cache.put(name, compiled)
                reg_mgr.register_compiled(compiled)
                ont_reg.register_compiled(compiled)
                # Add this ontology's types to the visible pool for next iterations
                all_types.update(compiled.types)
                _LOG.debug("Compiled built-in ontology %r (%d types)", name, compiled.type_count)
            except Exception as exc:
                _LOG.error("Failed to load/compile built-in ontology %r: %s", name, exc)

        _LOG.info(
            "Built-in ontologies loaded: %d ontologies, %d total types",
            len(BUILTIN_ONTOLOGY_NAMES),
            len(all_types),
        )

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def _check_initialized(self) -> None:
        if not self._initialized:
            raise OntologyNotInitializedError()

    # ── Load / compile user ontologies ─────────────────────────────────────────

    def load_from_dict(
        self,
        data:      dict[str, Any],
        name:      Optional[str] = None,
        overwrite: bool          = False,
    ) -> CompiledOntology:
        """Load and compile a user-defined ontology from a dictionary."""
        self._check_initialized()
        loader   = get_ontology_loader()
        compiler = get_ontology_compiler()
        cache    = get_ontology_cache()
        reg_mgr  = get_registry_manager()
        ont_reg  = get_ontology_registry()

        doc      = loader.load_from_dict(data, name=name, overwrite=overwrite)
        ext      = {uri: td for c in get_ontology_registry().all_compiled() for uri, td in c.types.items()}
        compiled = compiler.compile(doc, external_types=ext)
        cache.put(compiled.name, compiled)
        reg_mgr.register_compiled(compiled)
        ont_reg.register_compiled(compiled)
        return compiled

    def load_from_json_file(
        self,
        path:      str,
        name:      Optional[str] = None,
        overwrite: bool          = False,
    ) -> CompiledOntology:
        """Load and compile a user-defined ontology from a JSON file."""
        self._check_initialized()
        loader  = get_ontology_loader()
        compiler = get_ontology_compiler()
        cache   = get_ontology_cache()
        reg_mgr = get_registry_manager()
        ont_reg = get_ontology_registry()

        doc      = loader.load_from_json_file(path, name=name, overwrite=overwrite)
        ext      = {uri: td for c in ont_reg.all_compiled() for uri, td in c.types.items()}
        compiled = compiler.compile(doc, external_types=ext)
        cache.put(compiled.name, compiled)
        reg_mgr.register_compiled(compiled)
        ont_reg.register_compiled(compiled)
        return compiled

    # ── Type lookup ────────────────────────────────────────────────────────────

    def get_type(self, ref: str) -> OntologyTypeDef:
        """Resolve a type by URI, name, or alias. Raises TypeNotFoundError."""
        self._check_initialized()
        return get_lookup_service().type(ref)

    def get_type_or_none(self, ref: str) -> Optional[OntologyTypeDef]:
        self._check_initialized()
        return get_lookup_service().type_or_none(ref)

    def exists(self, ref: str) -> bool:
        self._check_initialized()
        return get_lookup_service().exists(ref)

    def properties_of(self, ref: str) -> dict[str, OntologyProperty]:
        self._check_initialized()
        return get_lookup_service().properties_of(ref)

    def is_subtype_of(self, candidate: str, base: str) -> bool:
        self._check_initialized()
        return get_lookup_service().is_subtype_of(candidate, base)

    # ── Namespace lookup ───────────────────────────────────────────────────────

    def get_namespace(self, uri: str) -> OntologyNamespace:
        self._check_initialized()
        return get_lookup_service().namespace(uri)

    def types_in_namespace(self, ns_uri: str) -> list[OntologyTypeDef]:
        self._check_initialized()
        return get_lookup_service().types_in_namespace(ns_uri)

    # ── Relationship lookup ────────────────────────────────────────────────────

    def get_relationship(self, uri: str) -> Optional[OntologyRelationshipDef]:
        self._check_initialized()
        return get_lookup_service().relationship(uri)

    def relationships_from(self, type_ref: str) -> list[OntologyRelationshipDef]:
        self._check_initialized()
        return get_lookup_service().relationships_from(type_ref)

    # ── Hierarchy ──────────────────────────────────────────────────────────────

    def hierarchy_tree(self, root_uri: str, max_depth: int = 10) -> HierarchyNode:
        self._check_initialized()
        return get_hierarchy_service().build_tree(root_uri, max_depth=max_depth)

    def ancestors_of(self, ref: str) -> list[OntologyTypeDef]:
        self._check_initialized()
        td = self.get_type(ref)
        ancestor_uris = get_registry_manager().ancestors_of(td.uri)
        return [get_registry_manager().get_type_or_none(u) for u in ancestor_uris if get_registry_manager().get_type_or_none(u)]  # type: ignore[misc]

    def descendants_of(self, ref: str) -> list[OntologyTypeDef]:
        self._check_initialized()
        td = self.get_type(ref)
        desc_uris = get_registry_manager().descendants_of(td.uri)
        return [get_registry_manager().get_type_or_none(u) for u in desc_uris if get_registry_manager().get_type_or_none(u)]  # type: ignore[misc]

    # ── Query ──────────────────────────────────────────────────────────────────

    def query(self, q: OntologyQuery) -> OntologyQueryResult:
        self._check_initialized()
        return get_query_engine().execute(q)

    def search(self, text: str, max_results: int = 50) -> list[OntologyTypeDef]:
        self._check_initialized()
        return get_lookup_service().search(text, max_results=max_results)

    # ── Graph ──────────────────────────────────────────────────────────────────

    def graph_stats(self) -> dict:
        self._check_initialized()
        return get_ontology_graph().stats()

    # ── Stats ──────────────────────────────────────────────────────────────────

    def stats(self) -> OntologyStats:
        self._check_initialized()
        return get_statistics_service().snapshot()

    def health(self) -> dict[str, Any]:
        reg = get_ontology_registry()
        return {
            "initialized":    self._initialized,
            "total_ontologies": len(reg.all_names()),
            "compiled":       len(reg.compiled_names()),
            "status":         "healthy" if self._initialized else "not_initialized",
        }

    # ── All compiled ───────────────────────────────────────────────────────────

    def list_ontology_names(self) -> list[str]:
        return get_ontology_registry().all_names()

    def get_compiled(self, name: str) -> Optional[CompiledOntology]:
        return get_ontology_registry().get_compiled(name)


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_ontology_manager() -> OntologyManager:
    global _mgr
    if _mgr is None:
        with _lock:
            if _mgr is None:
                _mgr = OntologyManager()
    return _mgr


def reset_ontology_manager() -> None:
    global _mgr
    with _lock:
        _mgr = None
