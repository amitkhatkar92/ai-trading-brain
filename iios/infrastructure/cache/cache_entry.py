"""
iios/infrastructure/cache/cache_entry.py
=========================================
Enhanced CacheEntry for the multi-level IIOS caching framework.

Distinct from infrastructure_models.CacheEntry which uses time.monotonic().
This version uses wall-clock time, tags, versioning, dirty flag, and
compression metadata.
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .cache_constants import (
    CacheLevel, CachePriority, SerializationFormat, CompressionAlgo,
    DEFAULT_REGION, DEFAULT_VERSION,
)

__all__ = ["CacheEntry", "make_entry", "EntryMetadata"]


@dataclass
class EntryMetadata:
    """Lightweight snapshot of entry state without the payload."""
    key: str
    region: str
    level: str
    created_at: float
    expires_at: Optional[float]
    last_accessed: float
    access_count: int
    size_bytes: int
    tags: frozenset[str]
    version: int
    priority: int
    dirty: bool

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at

    @property
    def remaining_ttl(self) -> Optional[float]:
        if self.expires_at is None:
            return None
        return max(0.0, self.expires_at - time.time())


@dataclass
class CacheEntry:
    """A single cached item with full metadata for multi-level cache management.

    Attributes:
        key:            Cache key.
        value:          Cached Python object (or bytes if serialized).
        created_at:     Wall-clock time when entry was created.
        expires_at:     Wall-clock expiry time (None = never expires).
        last_accessed:  Wall-clock time of last cache hit.
        access_count:   Total number of times this entry was accessed.
        size_bytes:     Estimated size of ``value`` in bytes (0 = unknown).
        tags:           Set of string tags for bulk invalidation.
        version:        Optimistic concurrency version counter.
        priority:       Eviction priority (lower int = harder to evict).
        dirty:          True when this write-back entry has not yet been
                        flushed to deeper cache levels.
        compressed:     True when ``value`` is compressed bytes.
        serialized:     True when ``value`` is serialized bytes.
        serial_format:  Format used for serialization.
        compress_algo:  Algorithm used for compression.
        region:         Cache region this entry belongs to.
        level:          Current physical tier of this entry.
        sliding_window: If set, TTL is extended by this many seconds on access.
    """

    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    size_bytes: int = 0
    tags: set[str] = field(default_factory=set)
    version: int = DEFAULT_VERSION
    priority: int = int(CachePriority.NORMAL)
    dirty: bool = False
    compressed: bool = False
    serialized: bool = False
    serial_format: SerializationFormat = SerializationFormat.NONE
    compress_algo: CompressionAlgo = CompressionAlgo.NONE
    region: str = DEFAULT_REGION
    level: CacheLevel = CacheLevel.L1
    sliding_window: Optional[float] = None  # seconds

    # ── Lifecycle ────────────────────────────────────────────────────────────

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at

    @property
    def remaining_ttl(self) -> Optional[float]:
        """Seconds until expiry, or None if immortal. Returns 0.0 if already expired."""
        if self.expires_at is None:
            return None
        return max(0.0, self.expires_at - time.time())

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    @property
    def idle_seconds(self) -> float:
        return time.time() - self.last_accessed

    def touch(self) -> None:
        """Record an access hit; extend TTL if sliding_window is set."""
        self.access_count += 1
        self.last_accessed = time.time()
        if self.sliding_window and self.expires_at is not None:
            self.expires_at = time.time() + self.sliding_window

    def bump_version(self) -> None:
        self.version += 1
        self.dirty = True

    def clone_for_level(self, level: CacheLevel) -> "CacheEntry":
        """Deep-copy this entry and assign to a different cache level."""
        c = copy.copy(self)
        c.level = level
        c.dirty = False
        return c

    def metadata(self) -> EntryMetadata:
        return EntryMetadata(
            key=self.key,
            region=self.region,
            level=self.level.value,
            created_at=self.created_at,
            expires_at=self.expires_at,
            last_accessed=self.last_accessed,
            access_count=self.access_count,
            size_bytes=self.size_bytes,
            tags=frozenset(self.tags),
            version=self.version,
            priority=self.priority,
            dirty=self.dirty,
        )


def make_entry(
    key: str,
    value: Any,
    *,
    ttl: Optional[float] = None,
    tags: Optional[set[str]] = None,
    priority: CachePriority = CachePriority.NORMAL,
    region: str = DEFAULT_REGION,
    level: CacheLevel = CacheLevel.L1,
    sliding_window: Optional[float] = None,
    size_bytes: int = 0,
) -> CacheEntry:
    """Convenience factory for CacheEntry."""
    return CacheEntry(
        key=key,
        value=value,
        expires_at=time.time() + ttl if ttl is not None else None,
        tags=set(tags) if tags else set(),
        priority=int(priority),
        region=region,
        level=level,
        sliding_window=sliding_window,
        size_bytes=size_bytes,
    )
