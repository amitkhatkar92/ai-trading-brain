"""
iios/infrastructure/cache/__init__.py
"""

from __future__ import annotations

# ── Legacy exports (preserved) ──────────────────────────────────────────────
from .cache_manager import CacheManager, get_cache_manager, reset_cache_manager
from .cache_policies import CachePolicy, LRUPolicy, LFUPolicy, FIFOPolicy
from .memory_cache import MemoryCache

# ── New framework exports ────────────────────────────────────────────────────
from .cache_constants import (
    CacheLevel, EvictionPolicy, WritePolicy, ReadPolicy,
    SerializationFormat, CompressionAlgo, CachePriority, SyncStrategy,
    DEFAULT_L1_MAX_SIZE, DEFAULT_L2_MAX_SIZE, DEFAULT_TTL,
    DEFAULT_REGION, SYSTEM_REGION, METRICS_REGION,
    EVICTION_BATCH_SIZE, MAX_KEY_LENGTH, NULL_SENTINEL,
)
from .cache_exceptions import (
    CacheError, CacheMissError, CacheFullError, CacheExpiredError,
    CacheSerializationError, CacheDeserializationError, CacheCompressionError,
    CacheProviderError, CacheProviderUnavailableError,
    CacheSyncError, CacheRegionError, CacheRegionNotFoundError,
    CacheKeyError, CacheKeyTooLongError, CacheConfigError,
    CacheBulkError, CacheInvalidationError, CacheVersionConflictError,
)
from .cache_entry import CacheEntry, EntryMetadata, make_entry
from .cache_policy import (
    BaseEvictionPolicy, LRUEvictionPolicy, LFUEvictionPolicy,
    FIFOEvictionPolicy, TTLEvictionPolicy, SizeEvictionPolicy,
    PriorityEvictionPolicy, NullEvictionPolicy, make_eviction_policy,
)
from .cache_metrics import CacheMetrics, RegionMetrics, LatencyTracker
from .cache_context import (
    CacheContext, get_cache_context, current_region,
    set_region, cache_region, reset_cache_context,
)
from .cache_registry import (
    CacheRegionConfig, CacheRegistry,
    get_cache_registry, reset_cache_registry,
)
from .cache_provider import (
    ProviderStats, BaseCacheProvider,
    L1MemoryProvider, L2SharedProvider, L3DistributedProvider,
)
from .cache_engine import CacheEngine, SyncResult
from .cache_factory import CacheFactory
from .cache_manager import (
    MultiLevelCacheManager, get_ml_cache_manager, reset_ml_cache_manager,
)

__all__ = [
    # Legacy
    "CacheManager", "get_cache_manager", "reset_cache_manager",
    "CachePolicy", "LRUPolicy", "LFUPolicy", "FIFOPolicy",
    "MemoryCache",
    # Constants
    "CacheLevel", "EvictionPolicy", "WritePolicy", "ReadPolicy",
    "SerializationFormat", "CompressionAlgo", "CachePriority", "SyncStrategy",
    "DEFAULT_L1_MAX_SIZE", "DEFAULT_L2_MAX_SIZE", "DEFAULT_TTL",
    "DEFAULT_REGION", "SYSTEM_REGION", "METRICS_REGION",
    "EVICTION_BATCH_SIZE", "MAX_KEY_LENGTH", "NULL_SENTINEL",
    # Exceptions
    "CacheError", "CacheMissError", "CacheFullError", "CacheExpiredError",
    "CacheSerializationError", "CacheDeserializationError", "CacheCompressionError",
    "CacheProviderError", "CacheProviderUnavailableError",
    "CacheSyncError", "CacheRegionError", "CacheRegionNotFoundError",
    "CacheKeyError", "CacheKeyTooLongError", "CacheConfigError",
    "CacheBulkError", "CacheInvalidationError", "CacheVersionConflictError",
    # Entry
    "CacheEntry", "EntryMetadata", "make_entry",
    # Policy
    "BaseEvictionPolicy", "LRUEvictionPolicy", "LFUEvictionPolicy",
    "FIFOEvictionPolicy", "TTLEvictionPolicy", "SizeEvictionPolicy",
    "PriorityEvictionPolicy", "NullEvictionPolicy", "make_eviction_policy",
    # Metrics
    "CacheMetrics", "RegionMetrics", "LatencyTracker",
    # Context
    "CacheContext", "get_cache_context", "current_region",
    "set_region", "cache_region", "reset_cache_context",
    # Registry
    "CacheRegionConfig", "CacheRegistry",
    "get_cache_registry", "reset_cache_registry",
    # Providers
    "ProviderStats", "BaseCacheProvider",
    "L1MemoryProvider", "L2SharedProvider", "L3DistributedProvider",
    # Engine + Factory
    "CacheEngine", "SyncResult", "CacheFactory",
    # Manager
    "MultiLevelCacheManager", "get_ml_cache_manager", "reset_ml_cache_manager",
]

