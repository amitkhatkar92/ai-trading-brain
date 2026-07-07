"""
iios/ontology/cache/ontology_cache.py
=======================================
Thread-safe LRU-style cache for CompiledOntology objects.
Avoids repeated recompilation on repeated access.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from typing import Optional

from ..ontology_constants import MAX_COMPILED_CACHE_SIZE
from ..runtime.runtime_object import CompiledOntology

__all__ = [
    "OntologyCache",
    "get_ontology_cache",
    "reset_ontology_cache",
]

_LOG  = logging.getLogger("iios.ontology.cache")
_lock = threading.Lock()
_cache_inst: Optional["OntologyCache"] = None


class OntologyCache:
    """
    LRU cache for compiled ontologies.

    Keys are ontology names (e.g. "OBSERVATION_ONTOLOGY").
    Evicts least-recently-used entries when max_size is reached.
    """

    def __init__(self, max_size: int = MAX_COMPILED_CACHE_SIZE) -> None:
        self._lock     = threading.RLock()
        self._max_size = max_size
        # OrderedDict as LRU: most-recently-used at end
        self._store: OrderedDict[str, CompiledOntology] = OrderedDict()
        self._hits   = 0
        self._misses = 0
        self._stores = 0

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def put(self, name: str, compiled: CompiledOntology) -> None:
        with self._lock:
            if name in self._store:
                self._store.move_to_end(name)
                self._store[name] = compiled
            else:
                self._store[name] = compiled
                self._stores += 1
                if len(self._store) > self._max_size:
                    evicted, _ = self._store.popitem(last=False)
                    _LOG.debug("Cache evicted %r (size limit %d)", evicted, self._max_size)

    def get(self, name: str) -> Optional[CompiledOntology]:
        with self._lock:
            item = self._store.get(name)
            if item is None:
                self._misses += 1
                return None
            self._store.move_to_end(name)
            self._hits += 1
            return item

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._store

    def remove(self, name: str) -> None:
        with self._lock:
            self._store.pop(name, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits   = 0
            self._misses = 0
            self._stores = 0

    # ── Stats ──────────────────────────────────────────────────────────────────

    @property
    def size(self) -> int:
        return len(self._store)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total else 0.0

    def names(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())

    def stats(self) -> dict:
        with self._lock:
            return {
                "size":      len(self._store),
                "max_size":  self._max_size,
                "hits":      self._hits,
                "misses":    self._misses,
                "stores":    self._stores,
                "hit_rate":  round(self.hit_rate, 4),
            }

    def all_compiled(self) -> list[CompiledOntology]:
        with self._lock:
            return list(self._store.values())


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_ontology_cache() -> OntologyCache:
    global _cache_inst
    if _cache_inst is None:
        with _lock:
            if _cache_inst is None:
                _cache_inst = OntologyCache()
    return _cache_inst


def reset_ontology_cache() -> None:
    global _cache_inst
    with _lock:
        _cache_inst = None
