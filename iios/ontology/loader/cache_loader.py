"""
iios/ontology/loader/cache_loader.py
=======================================
Version-aware cache loader — adds version-keyed cache entries on top of
the memory LRU and integrates with the persistent disk cache.

Supports:
- Version-aware cache keys (name + version → entry)
- TTL-based invalidation
- Eager pre-warming of the cache at startup
- Cache priming from a list of compiled artefacts
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..compiler.compiler_constants import CacheStrategy, WARM_CACHE_MAX_SIZE
from ..compiler.compiler_exceptions import CacheLoaderError
from ..cache.ontology_cache         import get_ontology_cache
from ..compiler.compiler_registry   import get_compiler_registry
from ..runtime.runtime_object       import CompiledOntology

__all__ = [
    "CacheEntry",
    "CacheLoader",
    "get_cache_loader",
    "reset_cache_loader",
]

_LOG  = logging.getLogger("iios.ontology.loader.cache")
_lock = threading.Lock()
_inst: Optional["CacheLoader"] = None


@dataclass
class CacheEntry:
    """A versioned cache entry."""
    name:        str
    version:     str
    compiled:    CompiledOntology
    stored_at:   float = field(default_factory=time.time)
    ttl_seconds: Optional[float] = None

    @property
    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return (time.time() - self.stored_at) > self.ttl_seconds

    @property
    def cache_key(self) -> str:
        return f"{self.name}::{self.version}"


class CacheLoader:
    """
    Versioned cache loader with TTL and pre-warming support.

    Sits on top of OntologyCache (memory LRU) and adds:
    - Version-aware keys: same name, different version = different entry
    - TTL-based invalidation
    - Bulk priming of the cache from a list of compiled artefacts
    - Eager warm-up at startup
    """

    def __init__(
        self,
        default_ttl_seconds: Optional[float] = None,
        max_entries:         int             = WARM_CACHE_MAX_SIZE,
    ) -> None:
        self._lock               = threading.RLock()
        self._default_ttl        = default_ttl_seconds
        self._max_entries        = max_entries
        self._versioned: dict[str, CacheEntry] = {}
        self._hit_count  = 0
        self._miss_count = 0

    # ── Storage ───────────────────────────────────────────────────────────────

    def put(
        self,
        compiled:    CompiledOntology,
        ttl_seconds: Optional[float] = None,
    ) -> None:
        """Store a compiled artefact in the versioned cache."""
        with self._lock:
            version = compiled.document.version
            entry   = CacheEntry(
                name        = compiled.name,
                version     = version,
                compiled    = compiled,
                ttl_seconds = ttl_seconds if ttl_seconds is not None else self._default_ttl,
            )
            self._versioned[entry.cache_key] = entry
            # Also push to the LRU cache for unversioned lookups
            get_ontology_cache().put(compiled.name, compiled)
            # Evict oldest if over limit
            while len(self._versioned) > self._max_entries:
                oldest_key = next(iter(self._versioned))
                del self._versioned[oldest_key]

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get(
        self,
        name:    str,
        version: Optional[str] = None,
    ) -> Optional[CompiledOntology]:
        """
        Retrieve a compiled artefact.

        If *version* is given, looks up the versioned key.
        Otherwise falls back to the LRU cache.
        """
        with self._lock:
            if version:
                key   = f"{name}::{version}"
                entry = self._versioned.get(key)
                if entry:
                    if entry.is_expired:
                        del self._versioned[key]
                        self._miss_count += 1
                        return None
                    self._hit_count += 1
                    return entry.compiled
                self._miss_count += 1
                return None

            # No version — try LRU cache
            cached = get_ontology_cache().get(name)
            if cached:
                self._hit_count += 1
            else:
                self._miss_count += 1
            return cached

    def has(self, name: str, version: Optional[str] = None) -> bool:
        if version:
            with self._lock:
                key   = f"{name}::{version}"
                entry = self._versioned.get(key)
                return entry is not None and not entry.is_expired
        return get_ontology_cache().has(name)

    def invalidate(self, name: str, version: Optional[str] = None) -> None:
        """Remove a specific entry from the versioned cache."""
        with self._lock:
            if version:
                key = f"{name}::{version}"
                self._versioned.pop(key, None)
            else:
                # Remove all versions of this name
                keys = [k for k in self._versioned if k.startswith(f"{name}::")]
                for k in keys:
                    del self._versioned[k]
                get_ontology_cache().remove(name)

    def invalidate_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        with self._lock:
            expired = [k for k, e in self._versioned.items() if e.is_expired]
            for k in expired:
                del self._versioned[k]
            return len(expired)

    # ── Priming ───────────────────────────────────────────────────────────────

    def prime(self, compiled_list: list[CompiledOntology]) -> int:
        """
        Pre-warm the cache with a list of compiled artefacts.

        Returns the count of entries stored.
        """
        stored = 0
        for compiled in compiled_list:
            try:
                self.put(compiled)
                stored += 1
            except Exception as exc:
                _LOG.warning("Cache prime failed for %r: %s", compiled.name, exc)
        _LOG.debug("Cache primed with %d artefacts", stored)
        return stored

    def prime_from_registry(self) -> int:
        """
        Pre-warm from all successfully compiled ontologies in the compiler registry.
        """
        reg     = get_compiler_registry()
        cache   = get_ontology_cache()
        primed  = 0
        for name in reg.successful_names():
            record = reg.get(name)
            if record and record.compiled:
                self.put(record.compiled)
                primed += 1
        _LOG.info("Cache primed from registry: %d entries", primed)
        return primed

    # ── Stats ──────────────────────────────────────────────────────────────────

    @property
    def hit_rate(self) -> float:
        total = self._hit_count + self._miss_count
        return self._hit_count / total if total > 0 else 0.0

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "versioned_entries": len(self._versioned),
                "lru_size":          get_ontology_cache().size,
                "hit_count":         self._hit_count,
                "miss_count":        self._miss_count,
                "hit_rate":          round(self.hit_rate, 4),
                "max_entries":       self._max_entries,
            }

    def clear(self) -> None:
        with self._lock:
            self._versioned.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_cache_loader() -> CacheLoader:
    global _inst
    if _inst is None:
        with _lock:
            if _inst is None:
                _inst = CacheLoader()
    return _inst


def reset_cache_loader() -> None:
    global _inst
    with _lock:
        _inst = None
