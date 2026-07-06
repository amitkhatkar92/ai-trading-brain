"""
iios/infrastructure/infrastructure_constants.py
=================================================
Constants and enumerations for the IIOS Core Infrastructure Layer.
"""

from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    # Lifecycle scopes
    "LifecycleScope",
    # Event priorities
    "EventPriority",
    # Cache policies
    "CachePolicy",
    "CacheBackend",
    # Scheduler job types
    "JobType",
    "JobStatus",
    # Storage formats
    "StorageFormat",
    "CompressionFormat",
    # Serialization formats
    "SerializationFormat",
    # Network methods
    "HttpMethod",
    # Repository operations
    "RepositoryOp",
    # Numeric limits
    "DEFAULT_CACHE_MAX_SIZE",
    "DEFAULT_CACHE_TTL_SECONDS",
    "DEFAULT_EVENT_QUEUE_SIZE",
    "DEFAULT_RETRY_ATTEMPTS",
    "DEFAULT_RETRY_BACKOFF_SECONDS",
    "DEFAULT_SCHEDULER_TICK_SECONDS",
    "DEFAULT_CIRCUIT_BREAKER_THRESHOLD",
    "DEFAULT_RATE_LIMIT_PER_SECOND",
    "DEFAULT_HTTP_TIMEOUT_SECONDS",
    "DEFAULT_CONNECTION_POOL_SIZE",
    "MAX_DEAD_LETTER_SIZE",
    "MAX_EVENT_SUBSCRIBERS",
]


# ---------------------------------------------------------------------------
# Dependency Injection
# ---------------------------------------------------------------------------


class LifecycleScope(str, Enum):
    SINGLETON  = "singleton"   # One instance for entire process
    SCOPED     = "scoped"      # One instance per scope (request / cycle)
    TRANSIENT  = "transient"   # New instance on every resolve


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class EventPriority(int, Enum):
    LOW      = 10
    NORMAL   = 50
    HIGH     = 100
    CRITICAL = 1000


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


class CachePolicy(str, Enum):
    LRU  = "lru"   # Least Recently Used
    LFU  = "lfu"   # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL  = "ttl"   # Expire by time only


class CacheBackend(str, Enum):
    MEMORY = "memory"
    REDIS  = "redis"
    NULL   = "null"   # No-op (for testing)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class JobType(str, Enum):
    CRON     = "cron"
    INTERVAL = "interval"
    ONCE     = "once"


class JobStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    SUCCEEDED = "succeeded"
    FAILED    = "failed"
    CANCELLED = "cancelled"
    PAUSED    = "paused"


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


class StorageFormat(str, Enum):
    TEXT   = "text"
    JSON   = "json"
    BINARY = "binary"
    PICKLE = "pickle"


class CompressionFormat(str, Enum):
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class SerializationFormat(str, Enum):
    JSON    = "json"
    YAML    = "yaml"
    TOML    = "toml"
    PICKLE  = "pickle"
    MSGPACK = "msgpack"


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------


class HttpMethod(str, Enum):
    GET    = "GET"
    POST   = "POST"
    PUT    = "PUT"
    PATCH  = "PATCH"
    DELETE = "DELETE"
    HEAD   = "HEAD"


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class RepositoryOp(str, Enum):
    FIND_BY_ID  = "find_by_id"
    FIND_ALL    = "find_all"
    SAVE        = "save"
    DELETE      = "delete"
    EXISTS      = "exists"
    COUNT       = "count"


# ---------------------------------------------------------------------------
# Numeric limits / defaults
# ---------------------------------------------------------------------------

DEFAULT_CACHE_MAX_SIZE:            Final[int]   = 1_000
DEFAULT_CACHE_TTL_SECONDS:         Final[int]   = 300        # 5 minutes
DEFAULT_EVENT_QUEUE_SIZE:          Final[int]   = 10_000
DEFAULT_RETRY_ATTEMPTS:            Final[int]   = 3
DEFAULT_RETRY_BACKOFF_SECONDS:     Final[float] = 0.5
DEFAULT_SCHEDULER_TICK_SECONDS:    Final[float] = 1.0
DEFAULT_CIRCUIT_BREAKER_THRESHOLD: Final[int]   = 5          # failures before open
DEFAULT_RATE_LIMIT_PER_SECOND:     Final[int]   = 100
DEFAULT_HTTP_TIMEOUT_SECONDS:      Final[float] = 30.0
DEFAULT_CONNECTION_POOL_SIZE:      Final[int]   = 10
MAX_DEAD_LETTER_SIZE:              Final[int]   = 1_000
MAX_EVENT_SUBSCRIBERS:             Final[int]   = 500
