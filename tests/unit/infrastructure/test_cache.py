"""
tests/unit/infrastructure/test_cache.py
========================================
Tests for the iios.infrastructure.cache subpackage.
"""

from __future__ import annotations

import time
import pytest

from iios.infrastructure.cache import (
    MemoryCache, CacheManager, get_cache_manager, reset_cache_manager,
    LRUPolicy, LFUPolicy, FIFOPolicy,
)
from iios.infrastructure.infrastructure_constants import CachePolicy
from iios.infrastructure.infrastructure_exceptions import CacheError


class TestLRUPolicy:
    def test_evict_lru(self):
        p = LRUPolicy()
        p.on_insert("a")
        p.on_insert("b")
        p.on_insert("c")
        p.on_access("a")  # a is now most recent
        victim = p.evict_key()
        assert victim == "b"  # b is least recently used

    def test_delete(self):
        p = LRUPolicy()
        p.on_insert("a")
        p.on_delete("a")
        assert p.evict_key() is None


class TestLFUPolicy:
    def test_evict_lfu(self):
        p = LFUPolicy()
        p.on_insert("a")
        p.on_insert("b")
        p.on_access("a")
        p.on_access("a")
        victim = p.evict_key()
        assert victim == "b"


class TestFIFOPolicy:
    def test_evict_fifo(self):
        p = FIFOPolicy()
        p.on_insert("a")
        p.on_insert("b")
        p.on_insert("c")
        assert p.evict_key() == "a"


class TestMemoryCache:
    def test_set_and_get(self):
        cache: MemoryCache[int] = MemoryCache()
        cache.set("k", 42)
        assert cache.get("k") == 42

    def test_get_missing(self):
        cache: MemoryCache[int] = MemoryCache()
        assert cache.get("missing") is None

    def test_ttl_expiry(self):
        cache: MemoryCache[int] = MemoryCache(default_ttl=0.05)
        cache.set("k", 1)
        time.sleep(0.1)
        assert cache.get("k") is None

    def test_no_ttl(self):
        cache: MemoryCache[int] = MemoryCache(default_ttl=0)
        cache.set("k", 1)
        assert cache.get("k") == 1  # no expiry

    def test_lru_eviction(self):
        cache: MemoryCache[int] = MemoryCache(max_size=3, policy=CachePolicy.LRU)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.get("a")  # access a → b is now LRU
        cache.set("d", 4)  # should evict b
        assert cache.get("b") is None
        assert cache.get("a") == 1

    def test_delete(self):
        cache: MemoryCache[int] = MemoryCache()
        cache.set("k", 99)
        assert cache.delete("k") is True
        assert cache.get("k") is None

    def test_exists(self):
        cache: MemoryCache[str] = MemoryCache()
        cache.set("k", "v")
        assert cache.exists("k")
        assert not cache.exists("missing")

    def test_keys(self):
        cache: MemoryCache[int] = MemoryCache()
        cache.set("a", 1)
        cache.set("b", 2)
        assert set(cache.keys()) == {"a", "b"}

    def test_get_or_set(self):
        calls = []
        cache: MemoryCache[int] = MemoryCache()
        result = cache.get_or_set("k", lambda: (calls.append(1), 42)[1])
        assert result == 42
        result2 = cache.get_or_set("k", lambda: (calls.append(2), 99)[1])
        assert result2 == 42
        assert len(calls) == 1

    def test_stats_hits_misses(self):
        cache: MemoryCache[int] = MemoryCache()
        cache.set("k", 1)
        cache.get("k")
        cache.get("missing")
        stats = cache.stats()
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.hit_rate == 0.5

    def test_purge_expired(self):
        cache: MemoryCache[int] = MemoryCache(default_ttl=0.05)
        cache.set("a", 1)
        cache.set("b", 2)
        time.sleep(0.1)
        n = cache.purge_expired()
        assert n == 2
        assert cache.size() == 0

    def test_clear(self):
        cache: MemoryCache[int] = MemoryCache()
        cache.set("a", 1)
        cache.clear()
        assert cache.size() == 0

    def test_ttl_override(self):
        cache: MemoryCache[int] = MemoryCache(default_ttl=60)
        cache.set("k", 1, ttl=0.05)
        time.sleep(0.1)
        assert cache.get("k") is None

    def test_max_size_capacity(self):
        cache: MemoryCache[int] = MemoryCache(max_size=5)
        for i in range(10):
            cache.set(str(i), i)
        assert cache.size() <= 5

    def test_lfu_eviction(self):
        cache: MemoryCache[int] = MemoryCache(max_size=3, policy=CachePolicy.LFU)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.get("a")
        cache.get("a")
        cache.get("b")
        # c and b have fewer accesses than a
        cache.set("d", 4)  # evict least frequent
        # "c" should be evicted (freq=0) or "b" (freq=1) before "a" (freq=2)
        assert cache.get("a") == 1


class TestCacheManager:
    def setup_method(self):
        reset_cache_manager()

    def teardown_method(self):
        reset_cache_manager()

    def test_create_and_get(self):
        mgr = get_cache_manager()
        mgr.create("quotes", max_size=100)
        cache = mgr.get("quotes")
        assert cache is not None

    def test_get_missing_raises(self):
        mgr = get_cache_manager()
        with pytest.raises(CacheError):
            mgr.get("nonexistent")

    def test_create_duplicate_raises(self):
        mgr = get_cache_manager()
        mgr.create("quotes")
        with pytest.raises(CacheError):
            mgr.create("quotes")

    def test_create_with_override(self):
        mgr = get_cache_manager()
        mgr.create("quotes", max_size=10)
        mgr.create("quotes", max_size=20, allow_override=True)
        assert mgr.get("quotes").max_size == 20

    def test_get_or_create(self):
        mgr = get_cache_manager()
        c1 = mgr.get_or_create("test")
        c2 = mgr.get_or_create("test")
        assert c1 is c2

    def test_names(self):
        mgr = get_cache_manager()
        mgr.create("a")
        mgr.create("b")
        assert set(mgr.names()) >= {"a", "b"}

    def test_clear_all(self):
        mgr = get_cache_manager()
        mgr.create("a")
        mgr.get("a").set("k", 1)
        mgr.clear_all()
        assert mgr.get("a").size() == 0

    def test_all_stats(self):
        mgr = get_cache_manager()
        mgr.create("a")
        stats = mgr.all_stats()
        assert "a" in stats

    def test_total_entries(self):
        mgr = get_cache_manager()
        mgr.create("a")
        mgr.create("b")
        mgr.get("a").set("k1", 1)
        mgr.get("b").set("k2", 2)
        assert mgr.total_entries() == 2

    def test_singleton(self):
        m1 = get_cache_manager()
        m2 = get_cache_manager()
        assert m1 is m2
