"""
iios/ontology/ontology_runtime_engine.py
==========================================
Master lifecycle controller for the Ontology Runtime Layer.

Manages startup, shutdown, health, and exposes all runtime services
through a single interface.  Follows the same engine pattern used
by KnowledgeEngine and the observation pipeline.

Usage::

    engine = get_ontology_engine()
    engine.initialize()

    manager = get_ontology_manager()
    td = manager.get_type("Instrument")        # returns OntologyTypeDef
    td = manager.get_type("iios.entity.Index") # by full URI
    results = manager.search("price")          # keyword search
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from .ontology_constants   import ONTOLOGY_NAMESPACE
from .ontology_exceptions  import OntologyNotInitializedError, OntologyRuntimeError
from .ontology_manager     import OntologyManager, get_ontology_manager, reset_ontology_manager
from .ontology_registry    import get_ontology_registry, reset_ontology_registry
from .loader.ontology_loader     import get_ontology_loader,    reset_ontology_loader
from .compiler.ontology_compiler import get_ontology_compiler,  reset_ontology_compiler
from .cache.ontology_cache       import get_ontology_cache,     reset_ontology_cache
from .registry.ontology_registry_manager import get_registry_manager, reset_registry_manager
from .registry.entity_registry       import reset_entity_registry
from .registry.relationship_registry import reset_relationship_registry
from .registry.event_registry        import reset_event_registry
from .registry.observation_registry  import reset_observation_registry
from .registry.knowledge_registry    import reset_knowledge_ont_registry
from .graph.ontology_graph           import get_ontology_graph,  reset_ontology_graph
from .query.ontology_query           import reset_query_engine
from .services.lookup_service        import reset_lookup_service
from .services.hierarchy_service     import reset_hierarchy_service
from .services.statistics_service    import reset_statistics_service
from .ontology_context               import reset_ontology_context

__all__ = [
    "OntologyRuntimeEngine",
    "get_ontology_engine",
    "reset_ontology_engine",
]

_LOG  = logging.getLogger("iios.ontology.engine")
_lock = threading.Lock()
_engine: Optional["OntologyRuntimeEngine"] = None


class OntologyRuntimeEngine:
    """
    Master controller for the Ontology Runtime Layer.

    Lifecycle::

        engine = get_ontology_engine()
        engine.initialize()        # loads + compiles all built-in ontologies

        manager = engine.manager   # use manager for all operations
        engine.health()            # {"status": "healthy", ...}
        engine.shutdown()
    """

    def __init__(self) -> None:
        self._lock        = threading.RLock()
        self._initialized = False
        self._started_at: Optional[float] = None
        self.namespace    = ONTOLOGY_NAMESPACE

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def initialize(self, load_builtins: bool = True) -> None:
        """
        Bootstrap the full Ontology Runtime Layer.

        Steps:
        1. Initialise OntologyManager (which triggers loader + compiler)
        2. Mark engine as initialised
        """
        with self._lock:
            if self._initialized:
                _LOG.debug("OntologyRuntimeEngine already initialised, skipping.")
                return

            t0 = time.perf_counter()
            _LOG.info("Initialising OntologyRuntimeEngine …")

            try:
                mgr = get_ontology_manager()
                mgr.initialize(load_builtins=load_builtins)
            except Exception as exc:
                raise OntologyRuntimeError(f"Ontology engine initialisation failed: {exc}") from exc

            elapsed = (time.perf_counter() - t0) * 1_000.0
            stats   = get_registry_manager().stats()
            _LOG.info(
                "OntologyRuntimeEngine initialised in %.1fms "
                "— %d types | %d relationships | %d namespaces",
                elapsed,
                stats["total_types"],
                stats["total_relationships"],
                stats["total_namespaces"],
            )
            self._initialized = True
            self._started_at  = time.time()

    def shutdown(self) -> None:
        """Graceful shutdown — clears all runtime state."""
        with self._lock:
            if not self._initialized:
                return
            _LOG.info("Shutting down OntologyRuntimeEngine …")
            _reset_all_subsystems()
            self._initialized = False
            self._started_at  = None
            _LOG.info("OntologyRuntimeEngine shutdown complete.")

    # ── Manager access ─────────────────────────────────────────────────────────

    @property
    def manager(self) -> OntologyManager:
        self._check_initialized()
        return get_ontology_manager()

    def _check_initialized(self) -> None:
        if not self._initialized:
            raise OntologyNotInitializedError()

    # ── Health ─────────────────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        """Return a health snapshot (does not raise if not initialised)."""
        if not self._initialized:
            return {
                "status":      "not_initialized",
                "initialized": False,
                "uptime_s":    0.0,
            }
        reg   = get_ontology_registry()
        rmgr  = get_registry_manager()
        stats = rmgr.stats()
        return {
            "status":              "healthy",
            "initialized":         True,
            "uptime_s":            round(time.time() - (self._started_at or time.time()), 2),
            "total_ontologies":    len(reg.all_names()),
            "total_types":         stats["total_types"],
            "total_relationships": stats["total_relationships"],
            "total_namespaces":    stats["total_namespaces"],
            "cache_size":          get_ontology_cache().size,
        }

    # ── Stats ──────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        self._check_initialized()
        return get_ontology_manager().stats().to_dict()

    # ── Convenience pass-through ───────────────────────────────────────────────

    def list_ontologies(self) -> list[str]:
        return get_ontology_registry().all_names()

    def is_initialized(self) -> bool:
        return self._initialized


# ── Helper: full subsystem reset ──────────────────────────────────────────────

def _reset_all_subsystems() -> None:
    reset_ontology_manager()
    reset_ontology_registry()
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


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_ontology_engine() -> OntologyRuntimeEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = OntologyRuntimeEngine()
    return _engine


def reset_ontology_engine() -> None:
    global _engine
    with _lock:
        if _engine is not None:
            try:
                _engine.shutdown()
            except Exception:
                pass
        _engine = None
    _reset_all_subsystems()
