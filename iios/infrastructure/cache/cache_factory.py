"""
iios/infrastructure/cache/cache_factory.py
==========================================
Factory for creating cache providers and engines from region configuration.
"""

from __future__ import annotations

import threading
from typing import Optional

from .cache_constants import CacheLevel, EvictionPolicy, WritePolicy, ReadPolicy, DEFAULT_TTL
from .cache_provider import L1MemoryProvider, L2SharedProvider, L3DistributedProvider, BaseCacheProvider
from .cache_engine import CacheEngine
from .cache_registry import CacheRegionConfig, get_cache_registry

__all__ = ["CacheFactory"]

# Shared L2 providers (keyed by region name) — multiple engines can share the same L2
_shared_l2_lock = threading.Lock()
_shared_l2: dict[str, L2SharedProvider] = {}


class CacheFactory:
    """Creates CacheEngine instances from CacheRegionConfig.

    Usage::

        engine = CacheFactory.create_engine(CacheRegionConfig(
            name="quotes",
            levels=[CacheLevel.L1, CacheLevel.L2],
            l1_max_size=2000,
            l2_max_size=20000,
            default_ttl=30.0,
        ))
    """

    @staticmethod
    def create_l1(config: CacheRegionConfig) -> L1MemoryProvider:
        return L1MemoryProvider(
            max_size=config.l1_max_size,
            policy=config.eviction_policy,
            name=f"l1:{config.name}",
        )

    @staticmethod
    def create_l2(config: CacheRegionConfig, shared: bool = True) -> L2SharedProvider:
        """Create (or return the existing shared) L2 provider for the region."""
        if shared:
            with _shared_l2_lock:
                if config.name not in _shared_l2:
                    _shared_l2[config.name] = L2SharedProvider(
                        max_size=config.l2_max_size,
                        policy=config.eviction_policy,
                        compression=config.compression,
                        compress_algo=config.compress_algo,
                        name=f"l2:{config.name}",
                    )
                return _shared_l2[config.name]
        return L2SharedProvider(
            max_size=config.l2_max_size,
            policy=config.eviction_policy,
            compression=config.compression,
            compress_algo=config.compress_algo,
            name=f"l2:{config.name}",
        )

    @staticmethod
    def create_l3(config: CacheRegionConfig) -> L3DistributedProvider:
        return L3DistributedProvider(name=f"l3:{config.name}")

    @staticmethod
    def create_engine(
        config: CacheRegionConfig,
        shared_l2: bool = True,
    ) -> CacheEngine:
        """Build a CacheEngine from a CacheRegionConfig."""
        l1 = CacheFactory.create_l1(config)
        l2: Optional[L2SharedProvider] = None
        l3: Optional[L3DistributedProvider] = None

        if CacheLevel.L2 in config.levels:
            l2 = CacheFactory.create_l2(config, shared=shared_l2)
        if CacheLevel.L3 in config.levels:
            l3 = CacheFactory.create_l3(config)

        return CacheEngine(
            l1=l1,
            l2=l2,
            l3=l3,
            write_policy=config.write_policy,
            read_policy=config.read_policy,
            region=config.name,
            default_ttl=config.default_ttl,
        )

    @staticmethod
    def create_from_name(region_name: str) -> CacheEngine:
        """Look up region config in the global registry and create an engine."""
        cfg = get_cache_registry().get_or_default(region_name)
        return CacheFactory.create_engine(cfg)

    @staticmethod
    def simple(
        name: str = "simple",
        max_size: int = 1000,
        ttl: Optional[float] = DEFAULT_TTL,
        policy: EvictionPolicy = EvictionPolicy.LRU,
    ) -> CacheEngine:
        """Convenience factory for a single-level L1 cache engine."""
        l1 = L1MemoryProvider(max_size=max_size, policy=policy, name=name)
        return CacheEngine(l1=l1, region=name, default_ttl=ttl)

    @staticmethod
    def two_level(
        name: str = "two_level",
        l1_max: int = 1000,
        l2_max: int = 10000,
        ttl: Optional[float] = DEFAULT_TTL,
        policy: EvictionPolicy = EvictionPolicy.LRU,
        shared_l2: bool = False,
    ) -> CacheEngine:
        """Convenience factory for a two-level (L1+L2) cache engine."""
        l1 = L1MemoryProvider(max_size=l1_max, policy=policy, name=f"l1:{name}")
        cfg = CacheRegionConfig(name=name, l2_max_size=l2_max, eviction_policy=policy)
        l2 = CacheFactory.create_l2(cfg, shared=shared_l2)
        return CacheEngine(l1=l1, l2=l2, region=name, default_ttl=ttl)

    @staticmethod
    def reset_shared_l2() -> None:
        """Clear all shared L2 providers (for testing)."""
        with _shared_l2_lock:
            _shared_l2.clear()
