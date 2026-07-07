"""
iios/infrastructure/cache/cache_provider.py
============================================
Cache provider implementations: L1 (in-process), L2 (shared in-process),
L3 (distributed stub). All providers share the BaseCacheProvider interface.
"""

from __future__ import annotations

import gzip
import logging
import pickle
import threading
import time
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .cache_constants import (
    CacheLevel, CompressionAlgo, SerializationFormat,
    COMPRESSION_THRESHOLD, EVICTION_BATCH_SIZE, DEFAULT_L1_MAX_SIZE,
    DEFAULT_L2_MAX_SIZE, DEFAULT_L3_MAX_SIZE, EvictionPolicy,
)
from .cache_entry import CacheEntry, make_entry
from .cache_policy import BaseEvictionPolicy, LRUEvictionPolicy, make_eviction_policy
from .cache_exceptions import (
    CacheSerializationError, CacheDeserializationError,
    CacheCompressionError, CacheFullError, CacheProviderError,
)

__all__ = [
    "ProviderStats",
    "BaseCacheProvider",
    "L1MemoryProvider",
    "L2SharedProvider",
    "L3DistributedProvider",
]

_LOG = logging.getLogger("iios.infrastructure.cache.provider")


@dataclass
class ProviderStats:
    level: str
    hits: int = 0
    misses: int = 0
    writes: int = 0
    deletes: int = 0
    evictions: int = 0
    expirations: int = 0
    current_size: int = 0
    total_bytes: int = 0

    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


class BaseCacheProvider(ABC):
    """Abstract base for all cache providers."""

    @property
    @abstractmethod
    def level(self) -> CacheLevel:
        """Return the cache level this provider implements."""

    @abstractmethod
    def get(self, key: str) -> Optional[CacheEntry]:
        """Return the CacheEntry for *key*, or None if absent/expired."""

    @abstractmethod
    def put(self, key: str, entry: CacheEntry) -> bool:
        """Store *entry*. Returns True on success."""

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Remove *key*. Returns True if it existed."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check key presence without touching access stats."""

    @abstractmethod
    def clear(self) -> int:
        """Remove all entries. Returns count removed."""

    @abstractmethod
    def size(self) -> int:
        """Number of (non-expired) entries currently stored."""

    @abstractmethod
    def keys(self) -> list[str]:
        """List all currently valid keys."""

    @abstractmethod
    def stats(self) -> ProviderStats:
        """Return current provider statistics."""

    def get_multi(self, keys: list[str]) -> dict[str, CacheEntry]:
        """Bulk-get entries. Default: sequential calls to get()."""
        result: dict[str, CacheEntry] = {}
        for k in keys:
            entry = self.get(k)
            if entry is not None:
                result[k] = entry
        return result

    def put_multi(self, entries: dict[str, CacheEntry]) -> int:
        """Bulk-put entries. Returns count successfully written."""
        count = 0
        for key, entry in entries.items():
            if self.put(key, entry):
                count += 1
        return count

    def delete_multi(self, keys: list[str]) -> int:
        """Bulk-delete. Returns count deleted."""
        return sum(1 for k in keys if self.delete(k))

    def purge_expired(self) -> int:
        """Remove expired entries proactively. Returns count removed."""
        expired = [k for k in self.keys() if self._is_expired(k)]
        return self.delete_multi(expired)

    def _is_expired(self, key: str) -> bool:
        entry = self.get(key)
        return entry is None  # get() already removes expired entries


class L1MemoryProvider(BaseCacheProvider):
    """Fast in-process memory cache (L1). Stores Python objects as-is."""

    def __init__(
        self,
        max_size: int = DEFAULT_L1_MAX_SIZE,
        policy: EvictionPolicy = EvictionPolicy.LRU,
        name: str = "l1",
    ) -> None:
        self._max_size = max_size
        self._policy_impl: BaseEvictionPolicy = make_eviction_policy(policy)
        self._name = name
        self._store: dict[str, CacheEntry] = {}
        self._stats = ProviderStats(level=CacheLevel.L1.value)
        self._lock = threading.RLock()

    @property
    def level(self) -> CacheLevel:
        return CacheLevel.L1

    def get(self, key: str) -> Optional[CacheEntry]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._stats.misses += 1
                return None
            if entry.is_expired:
                del self._store[key]
                self._stats.misses += 1
                self._stats.expirations += 1
                self._stats.current_size = len(self._store)
                return None
            entry.touch()
            self._stats.hits += 1
            return entry

    def put(self, key: str, entry: CacheEntry) -> bool:
        with self._lock:
            is_update = key in self._store
            if not is_update and len(self._store) >= self._max_size:
                victims = self._policy_impl.select_victims(
                    list(self._store.values()), EVICTION_BATCH_SIZE
                )
                for vk in victims:
                    self._store.pop(vk, None)
                    self._stats.evictions += 1
                if len(self._store) >= self._max_size and not victims:
                    return False  # NullPolicy — can't evict
            entry.level = CacheLevel.L1
            self._store[key] = entry
            self._stats.writes += 1
            self._stats.current_size = len(self._store)
            self._stats.total_bytes += entry.size_bytes
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            entry = self._store.pop(key, None)
            if entry is not None:
                self._stats.deletes += 1
                self._stats.current_size = len(self._store)
                return True
            return False

    def exists(self, key: str) -> bool:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                del self._store[key]
                self._stats.current_size = len(self._store)
                return False
            return True

    def clear(self) -> int:
        with self._lock:
            n = len(self._store)
            self._store.clear()
            self._stats.current_size = 0
            return n

    def size(self) -> int:
        with self._lock:
            # Purge expired inline
            expired = [k for k, e in self._store.items() if e.is_expired]
            for k in expired:
                del self._store[k]
                self._stats.expirations += 1
            self._stats.current_size = len(self._store)
            return len(self._store)

    def keys(self) -> list[str]:
        with self._lock:
            return [k for k, e in self._store.items() if not e.is_expired]

    def purge_expired(self) -> int:
        """Remove all expired entries directly from the store (avoids lazy-delete double-count)."""
        with self._lock:
            expired = [k for k, e in self._store.items() if e.is_expired]
            for k in expired:
                del self._store[k]
                self._stats.expirations += 1
            self._stats.current_size = len(self._store)
            return len(expired)

    def stats(self) -> ProviderStats:
        with self._lock:
            self._stats.current_size = len(self._store)
            return ProviderStats(
                level=self._stats.level,
                hits=self._stats.hits,
                misses=self._stats.misses,
                writes=self._stats.writes,
                deletes=self._stats.deletes,
                evictions=self._stats.evictions,
                expirations=self._stats.expirations,
                current_size=self._stats.current_size,
                total_bytes=self._stats.total_bytes,
            )

    def atomic_increment(self, key: str, delta: int = 1, default: int = 0) -> int:
        """Atomically increment a numeric value. Creates entry if absent."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None or entry.is_expired:
                new_val = default + delta
            else:
                current = entry.value
                if not isinstance(current, (int, float)):
                    raise TypeError(f"Cannot increment non-numeric cache value at '{key}'")
                new_val = current + delta
            if entry is not None:
                entry.value = new_val
                entry.bump_version()
            else:
                new_entry = make_entry(key, new_val)
                self._store[key] = new_entry
            return new_val


class L2SharedProvider(BaseCacheProvider):
    """Larger shared in-memory cache (L2). Optional pickle serialization.

    Designed to be shared across multiple L1-owning engines within the same
    process. Uses the same dict-based store as L1 but with larger capacity
    and optional compression.
    """

    def __init__(
        self,
        max_size: int = DEFAULT_L2_MAX_SIZE,
        policy: EvictionPolicy = EvictionPolicy.LRU,
        compression: bool = False,
        compress_algo: CompressionAlgo = CompressionAlgo.ZLIB,
        name: str = "l2",
    ) -> None:
        self._max_size = max_size
        self._policy_impl: BaseEvictionPolicy = make_eviction_policy(policy)
        self._compression = compression
        self._compress_algo = compress_algo
        self._name = name
        self._store: dict[str, CacheEntry] = {}
        self._stats = ProviderStats(level=CacheLevel.L2.value)
        self._lock = threading.RLock()

    @property
    def level(self) -> CacheLevel:
        return CacheLevel.L2

    def get(self, key: str) -> Optional[CacheEntry]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._stats.misses += 1
                return None
            if entry.is_expired:
                del self._store[key]
                self._stats.misses += 1
                self._stats.expirations += 1
                self._stats.current_size = len(self._store)
                return None
            # Decompress if needed
            if entry.compressed:
                entry = self._decompress_entry(entry)
            entry.touch()
            self._stats.hits += 1
            return entry

    def put(self, key: str, entry: CacheEntry) -> bool:
        with self._lock:
            is_update = key in self._store
            if not is_update and len(self._store) >= self._max_size:
                victims = self._policy_impl.select_victims(
                    list(self._store.values()), EVICTION_BATCH_SIZE
                )
                for vk in victims:
                    self._store.pop(vk, None)
                    self._stats.evictions += 1
                if len(self._store) >= self._max_size and not victims:
                    return False
            stored = entry.clone_for_level(CacheLevel.L2)
            if self._compression and not stored.compressed:
                stored = self._compress_entry(stored)
            self._store[key] = stored
            self._stats.writes += 1
            self._stats.current_size = len(self._store)
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            if self._store.pop(key, None) is not None:
                self._stats.deletes += 1
                self._stats.current_size = len(self._store)
                return True
            return False

    def exists(self, key: str) -> bool:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                del self._store[key]
                self._stats.current_size = len(self._store)
                return False
            return True

    def clear(self) -> int:
        with self._lock:
            n = len(self._store)
            self._store.clear()
            self._stats.current_size = 0
            return n

    def size(self) -> int:
        with self._lock:
            expired = [k for k, e in self._store.items() if e.is_expired]
            for k in expired:
                del self._store[k]
                self._stats.expirations += 1
            self._stats.current_size = len(self._store)
            return len(self._store)

    def keys(self) -> list[str]:
        with self._lock:
            return [k for k, e in self._store.items() if not e.is_expired]

    def stats(self) -> ProviderStats:
        with self._lock:
            self._stats.current_size = len(self._store)
            return ProviderStats(
                level=self._stats.level,
                hits=self._stats.hits,
                misses=self._stats.misses,
                writes=self._stats.writes,
                deletes=self._stats.deletes,
                evictions=self._stats.evictions,
                expirations=self._stats.expirations,
                current_size=self._stats.current_size,
                total_bytes=self._stats.total_bytes,
            )

    def _compress_entry(self, entry: CacheEntry) -> CacheEntry:
        try:
            raw = pickle.dumps(entry.value, protocol=4)
            if self._compress_algo == CompressionAlgo.GZIP:
                compressed = gzip.compress(raw)
            else:  # ZLIB
                compressed = zlib.compress(raw)
            import copy
            e = copy.copy(entry)
            e.value = compressed
            e.size_bytes = len(compressed)
            e.compressed = True
            e.serialized = True
            e.compress_algo = self._compress_algo
            e.serial_format = SerializationFormat.PICKLE
            return e
        except Exception as exc:
            raise CacheCompressionError(entry.key, str(exc)) from exc

    def _decompress_entry(self, entry: CacheEntry) -> CacheEntry:
        try:
            compressed = entry.value
            if entry.compress_algo == CompressionAlgo.GZIP:
                raw = gzip.decompress(compressed)
            else:
                raw = zlib.decompress(compressed)
            value = pickle.loads(raw)  # noqa: S301
            import copy
            e = copy.copy(entry)
            e.value = value
            e.compressed = False
            e.serialized = False
            return e
        except Exception as exc:
            raise CacheDeserializationError(entry.key, str(exc)) from exc


class L3DistributedProvider(BaseCacheProvider):
    """Stub for distributed cache (Redis, Memcached, etc.).

    All get() calls return None — the stub does not persist anything.
    Replace with a real implementation when a distributed backend is available.
    """

    def __init__(self, name: str = "l3") -> None:
        self._name = name
        self._stats = ProviderStats(level=CacheLevel.L3.value)

    @property
    def level(self) -> CacheLevel:
        return CacheLevel.L3

    def get(self, key: str) -> Optional[CacheEntry]:
        self._stats.misses += 1
        _LOG.debug("L3 stub: get('%s') — always misses", key)
        return None

    def put(self, key: str, entry: CacheEntry) -> bool:
        self._stats.writes += 1
        _LOG.debug("L3 stub: put('%s') — discarded", key)
        return True  # pretend success

    def delete(self, key: str) -> bool:
        self._stats.deletes += 1
        return True

    def exists(self, key: str) -> bool:
        return False

    def clear(self) -> int:
        return 0

    def size(self) -> int:
        return 0

    def keys(self) -> list[str]:
        return []

    def stats(self) -> ProviderStats:
        return ProviderStats(
            level=self._stats.level,
            misses=self._stats.misses,
            writes=self._stats.writes,
            deletes=self._stats.deletes,
        )
