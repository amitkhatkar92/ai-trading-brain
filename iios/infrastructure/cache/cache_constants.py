"""
iios/infrastructure/cache/cache_constants.py
=============================================
Constants and enumerations for the IIOS Distributed Caching Framework.
"""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Final


class CacheLevel(str, Enum):
    """Physical tier of the cache hierarchy."""
    L1 = "l1"   # In-process memory — fastest, smallest
    L2 = "l2"   # Shared in-process memory — larger, slightly slower
    L3 = "l3"   # Distributed / remote (Redis, Memcached) — largest, slowest


class EvictionPolicy(str, Enum):
    LRU = "lru"         # Least Recently Used
    LFU = "lfu"         # Least Frequently Used
    FIFO = "fifo"       # First In, First Out
    TTL = "ttl"         # Evict expired first, then soonest-to-expire
    SIZE = "size"       # Evict largest entries first
    PRIORITY = "priority"  # Evict lowest-priority first
    NONE = "none"       # No eviction — fail silently when full


class WritePolicy(str, Enum):
    WRITE_THROUGH = "write_through"  # write to all levels immediately
    WRITE_BACK = "write_back"        # write to L1 only; flush to deeper levels on sync
    WRITE_AROUND = "write_around"    # skip L1/L2, write only to L3


class ReadPolicy(str, Enum):
    READ_THROUGH = "read_through"    # on miss, engine calls loader function
    READ_ASIDE = "read_aside"        # caller loads on miss (cache-aside pattern)


class SerializationFormat(str, Enum):
    NONE = "none"      # store Python object as-is (L1)
    PICKLE = "pickle"  # Python pickle protocol 4
    JSON = "json"      # UTF-8 JSON bytes


class CompressionAlgo(str, Enum):
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"


class CachePriority(IntEnum):
    """Entry priority — higher priority entries survive eviction longer."""
    CRITICAL = 0
    HIGH = 10
    NORMAL = 50
    LOW = 100
    DISPOSABLE = 200


class SyncStrategy(str, Enum):
    IMMEDIATE = "immediate"   # invalidate across levels immediately
    LAZY = "lazy"             # invalidate on next access
    PERIODIC = "periodic"     # batch sync on schedule


# ── Numeric defaults ────────────────────────────────────────────────────────

DEFAULT_L1_MAX_SIZE: Final[int] = 1_000
DEFAULT_L2_MAX_SIZE: Final[int] = 10_000
DEFAULT_L3_MAX_SIZE: Final[int] = 100_000
DEFAULT_TTL: Final[float] = 300.0             # 5 minutes
DEFAULT_SLIDING_WINDOW: Final[float] = 60.0   # 1 minute sliding extension
COMPRESSION_THRESHOLD: Final[int] = 1_024     # compress if size_bytes > 1 KB
MAX_KEY_LENGTH: Final[int] = 256
MAX_BULK_SIZE: Final[int] = 1_000
EVICTION_BATCH_SIZE: Final[int] = 10          # evict N entries when full
METRICS_WINDOW_SIZE: Final[int] = 1_000       # rolling window for percentiles
WARMUP_BATCH_SIZE: Final[int] = 100
SYNC_BATCH_SIZE: Final[int] = 100
DEFAULT_REGION: Final[str] = "default"
SYSTEM_REGION: Final[str] = "system"
METRICS_REGION: Final[str] = "metrics"
NULL_SENTINEL: Final[str] = "__NULL__"        # cached "not found" marker
KEY_SEPARATOR: Final[str] = ":"
DEFAULT_VERSION: Final[int] = 1
MAX_TAG_COUNT: Final[int] = 32
MAX_DEPENDENCY_DEPTH: Final[int] = 8
