"""
iios/infrastructure/cache/cache_registry.py
============================================
Registry of named cache regions and their configuration.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from .cache_constants import (
    CacheLevel, CompressionAlgo, EvictionPolicy, ReadPolicy,
    SerializationFormat, SyncStrategy, WritePolicy,
    DEFAULT_L1_MAX_SIZE, DEFAULT_L2_MAX_SIZE, DEFAULT_TTL,
    DEFAULT_REGION, SYSTEM_REGION, METRICS_REGION,
)
from .cache_exceptions import CacheRegionNotFoundError, CacheConfigError

__all__ = [
    "CacheRegionConfig",
    "CacheRegistry",
    "get_cache_registry",
    "reset_cache_registry",
]

_registry_lock = threading.Lock()
_registry: Optional["CacheRegistry"] = None


@dataclass
class CacheRegionConfig:
    """Configuration for a single named cache region.

    Each region has independent sizing, TTL, eviction, and write policy.
    """
    name: str
    levels: list[CacheLevel] = field(default_factory=lambda: [CacheLevel.L1])
    l1_max_size: int = DEFAULT_L1_MAX_SIZE
    l2_max_size: int = DEFAULT_L2_MAX_SIZE
    default_ttl: Optional[float] = DEFAULT_TTL       # None = entries never expire
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    write_policy: WritePolicy = WritePolicy.WRITE_THROUGH
    read_policy: ReadPolicy = ReadPolicy.READ_ASIDE
    serialization: SerializationFormat = SerializationFormat.NONE
    compression: bool = False
    compress_algo: CompressionAlgo = CompressionAlgo.ZLIB
    sync_strategy: SyncStrategy = SyncStrategy.IMMEDIATE
    sliding_window: Optional[float] = None   # if set, TTL slides on access
    namespace: str = ""                       # key prefix for namespace ops
    tags: list[str] = field(default_factory=list)
    description: str = ""

    def validate(self) -> None:
        if not self.name:
            raise CacheConfigError("Region name cannot be empty")
        if self.l1_max_size < 1:
            raise CacheConfigError(f"l1_max_size must be >= 1, got {self.l1_max_size}")
        if self.default_ttl is not None and self.default_ttl < 0:
            raise CacheConfigError("default_ttl must be >= 0 or None")


class CacheRegistry:
    """Global registry of named ``CacheRegionConfig`` instances.

    Usage::

        reg = get_cache_registry()
        reg.register(CacheRegionConfig(name="quotes", l1_max_size=5000, default_ttl=30))
        cfg = reg.get("quotes")
    """

    def __init__(self) -> None:
        self._regions: dict[str, CacheRegionConfig] = {}
        self._lock = threading.RLock()
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(CacheRegionConfig(name=DEFAULT_REGION, description="Default cache region"))
        self.register(CacheRegionConfig(
            name=SYSTEM_REGION,
            default_ttl=None,   # system entries never expire
            eviction_policy=EvictionPolicy.LRU,
            description="System configuration cache",
        ))
        self.register(CacheRegionConfig(
            name=METRICS_REGION,
            l1_max_size=500,
            default_ttl=60.0,
            description="Metrics and monitoring cache",
        ))

    def register(
        self,
        config: CacheRegionConfig,
        allow_override: bool = True,
    ) -> None:
        config.validate()
        with self._lock:
            if config.name in self._regions and not allow_override:
                raise CacheConfigError(f"Region '{config.name}' already registered")
            self._regions[config.name] = config

    def get(self, name: str) -> CacheRegionConfig:
        with self._lock:
            cfg = self._regions.get(name)
        if cfg is None:
            raise CacheRegionNotFoundError(name)
        return cfg

    def get_optional(self, name: str) -> Optional[CacheRegionConfig]:
        with self._lock:
            return self._regions.get(name)

    def get_or_default(self, name: str) -> CacheRegionConfig:
        with self._lock:
            return self._regions.get(name) or self._regions.get(DEFAULT_REGION) or CacheRegionConfig(name=name)

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._regions

    def unregister(self, name: str) -> bool:
        with self._lock:
            return self._regions.pop(name, None) is not None

    def list_all(self) -> list[CacheRegionConfig]:
        with self._lock:
            return list(self._regions.values())

    def list_names(self) -> list[str]:
        with self._lock:
            return list(self._regions.keys())

    def clear(self) -> None:
        with self._lock:
            self._regions.clear()
        self._register_defaults()


def get_cache_registry() -> CacheRegistry:
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = CacheRegistry()
        return _registry


def reset_cache_registry() -> None:
    global _registry
    with _registry_lock:
        _registry = None
