"""iios/ontology/services/statistics_service.py — ontology runtime statistics."""
from __future__ import annotations
import threading
import time
from typing import Optional
from ..registry.ontology_registry_manager import get_registry_manager
from ..cache.ontology_cache import get_ontology_cache
from ..query.ontology_query import get_query_engine
from ..runtime.runtime_object import OntologyStats

__all__ = ["StatisticsService", "get_statistics_service", "reset_statistics_service"]

_lock = threading.Lock()
_svc: Optional["StatisticsService"] = None


class StatisticsService:
    def __init__(self) -> None:
        self._started_at = time.time()

    def snapshot(self) -> OntologyStats:
        mgr   = get_registry_manager()
        cache = get_ontology_cache()
        qe    = get_query_engine()
        reg   = mgr.stats()
        cst   = cache.stats()
        return OntologyStats(
            total_ontologies    = reg["compiled_ontologies"],
            total_types         = reg["total_types"],
            total_relationships = reg["total_relationships"],
            total_namespaces    = reg["total_namespaces"],
            compiled_count      = reg["compiled_ontologies"],
            cache_hits          = cst["hits"],
            cache_misses        = cst["misses"],
            query_count         = qe.stats()["query_count"],
            uptime_seconds      = time.time() - self._started_at,
        )

    def report(self) -> dict:
        return self.snapshot().to_dict()


def get_statistics_service() -> StatisticsService:
    global _svc
    if _svc is None:
        with _lock:
            if _svc is None:
                _svc = StatisticsService()
    return _svc


def reset_statistics_service() -> None:
    global _svc
    with _lock:
        _svc = None
