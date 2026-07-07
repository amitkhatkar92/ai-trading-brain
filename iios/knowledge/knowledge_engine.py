"""
iios/knowledge/knowledge_engine.py
=====================================
Master lifecycle controller for the Knowledge Engine.
Initialises all subsystems, manages startup/shutdown,
and exposes a health/status API.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from .knowledge_constants import KNOWLEDGE_NAMESPACE
from .knowledge_exceptions import KnowledgeEngineNotInitializedError
from .storage.knowledge_storage   import get_knowledge_storage, reset_knowledge_storage
from .storage.knowledge_cache     import get_knowledge_cache, reset_knowledge_cache
from .indexing.knowledge_index    import get_knowledge_index, reset_knowledge_index
from .repositories.knowledge_repository import get_knowledge_repository, reset_knowledge_repository
from .search.knowledge_search     import get_search_engine, reset_search_engine
from .graph.knowledge_graph       import get_knowledge_graph, reset_knowledge_graph
from .versioning.knowledge_versioning import get_versioning_engine, reset_versioning_engine
from .validators.knowledge_validator  import get_knowledge_validator, reset_knowledge_validator
from .validators.knowledge_constraints import get_constraint_checker, reset_constraint_checker
from .validators.knowledge_integrity  import get_integrity_checker, reset_integrity_checker
from .validators.knowledge_consistency import get_consistency_checker, reset_consistency_checker
from .knowledge_factory  import get_knowledge_factory
from .knowledge_manager  import get_knowledge_manager, reset_knowledge_manager
from .knowledge_context  import get_knowledge_context, reset_knowledge_context

__all__ = [
    "KnowledgeEngine",
    "get_knowledge_engine",
    "reset_knowledge_engine",
]

_LOG = logging.getLogger("iios.knowledge.engine")
_lock = threading.Lock()
_engine: Optional["KnowledgeEngine"] = None


class KnowledgeEngine:
    """Master controller for the Knowledge Engine subsystem.

    Lifecycle::

        engine = get_knowledge_engine()
        engine.initialize()
        # ... use KnowledgeManager for all operations ...
        engine.shutdown()
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized = False
        self._started_at: Optional[float] = None
        self._config: dict[str, Any] = {}
        self.namespace = KNOWLEDGE_NAMESPACE

    def initialize(self, config: Optional[dict[str, Any]] = None) -> None:
        with self._lock:
            if self._initialized:
                return
            self._config = config or {}
            _LOG.info("KnowledgeEngine initializing …")

            # Touch all singletons to ensure they exist
            get_knowledge_storage(self._config.get("persist_path"))
            get_knowledge_cache()
            get_knowledge_index()
            get_knowledge_repository()
            get_search_engine()
            get_knowledge_graph()
            get_versioning_engine()
            get_knowledge_validator()
            get_constraint_checker()
            get_integrity_checker()
            get_consistency_checker()
            get_knowledge_factory()
            get_knowledge_manager()
            get_knowledge_context()

            self._initialized = True
            self._started_at = time.time()
            _LOG.info("KnowledgeEngine initialized — namespace=%s", self.namespace)

    def shutdown(self) -> None:
        with self._lock:
            if not self._initialized:
                return
            _LOG.info("KnowledgeEngine shutting down …")
            try:
                get_knowledge_storage().flush()
            except Exception as exc:
                _LOG.warning("Flush error on shutdown: %s", exc)
            self._initialized = False
            _LOG.info("KnowledgeEngine stopped")

    def status(self) -> dict[str, Any]:
        with self._lock:
            if not self._initialized:
                return {"status": "not_initialized"}
            uptime = time.time() - (self._started_at or time.time())
            repo_stats = get_knowledge_repository().stats()
            cache_stats = get_knowledge_cache().stats()
            return {
                "status":       "running",
                "namespace":    self.namespace,
                "uptime_sec":   round(uptime, 2),
                "total_records": repo_stats.total_items,
                "active_records": repo_stats.active_items,
                "cache_hit_ratio": cache_stats.get("hit_ratio", 0.0),
                "index_size":   get_knowledge_index().count(),
                "graph_nodes":  get_knowledge_graph().node_count(),
                "graph_edges":  get_knowledge_graph().edge_count(),
            }

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def require_initialized(self) -> None:
        if not self._initialized:
            raise KnowledgeEngineNotInitializedError(
                "KnowledgeEngine must be initialized before use",
                code="KE-001",
            )


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_knowledge_engine() -> KnowledgeEngine:
    global _engine
    with _lock:
        if _engine is None:
            _engine = KnowledgeEngine()
        return _engine


def reset_knowledge_engine() -> None:
    global _engine
    with _lock:
        if _engine is not None:
            try:
                _engine.shutdown()
            except Exception:
                pass
        _engine = None
        # Reset all sub-components to clean slate
        reset_knowledge_manager()
        reset_knowledge_context()
        reset_search_engine()
        reset_knowledge_graph()
        reset_versioning_engine()
        reset_knowledge_repository()
        reset_knowledge_index()
        reset_knowledge_cache()
        reset_knowledge_storage()
        reset_knowledge_validator()
        reset_constraint_checker()
        reset_integrity_checker()
        reset_consistency_checker()
