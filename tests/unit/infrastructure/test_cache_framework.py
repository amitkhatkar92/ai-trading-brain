"""
tests/unit/infrastructure/test_cache_framework.py
===================================================
Comprehensive test-suite for the IIOS Distributed Caching Framework.
Target: ≥120 tests across all components.
"""

from __future__ import annotations

import threading
import time
import pytest

from iios.infrastructure.cache import (
    # Constants
    CacheLevel, EvictionPolicy, WritePolicy, ReadPolicy,
    CachePriority, DEFAULT_REGION,
    # Exceptions
    CacheMissError, CacheRegionNotFoundError, CacheVersionConflictError,
    CacheConfigError, CacheMissError,
    # Entry
    CacheEntry, make_entry,
    # Policies
    LRUEvictionPolicy, LFUEvictionPolicy, FIFOEvictionPolicy,
    TTLEvictionPolicy, SizeEvictionPolicy, PriorityEvictionPolicy,
    NullEvictionPolicy, make_eviction_policy,
    # Metrics
    CacheMetrics, LatencyTracker,
    # Context
    get_cache_context, current_region, cache_region, reset_cache_context,
    # Registry
    CacheRegionConfig, get_cache_registry, reset_cache_registry,
    # Providers
    L1MemoryProvider, L2SharedProvider, L3DistributedProvider,
    # Engine
    CacheEngine, SyncResult,
    # Factory
    CacheFactory,
    # Manager
    get_ml_cache_manager, reset_ml_cache_manager, MultiLevelCacheManager,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _entries(n: int, base_access: int = 0) -> list[CacheEntry]:
    """Build n CacheEntry objects with predictable LRU/LFU ordering."""
    entries = []
    now = time.time()
    for i in range(n):
        e = make_entry(f"k{i}", f"v{i}")
        e.last_accessed = now + i        # k0 = oldest → first LRU victim
        e.access_count = base_access + i  # k0 = fewest accesses → first LFU victim
        e.created_at = now + i
        e.size_bytes = (n - i) * 10      # k0 = largest → first SIZE victim
        e.priority = 200 - i             # k0 = lowest priority → first PRIO victim
        entries.append(e)
    return entries


# ══════════════════════════════════════════════════════════════════════════════
# 1. CacheEntry
# ══════════════════════════════════════════════════════════════════════════════

class TestCacheEntry:
    def test_make_entry_defaults(self):
        e = make_entry("key", "value")
        assert e.key == "key"
        assert e.value == "value"
        assert e.expires_at is None
        assert not e.is_expired

    def test_make_entry_with_ttl(self):
        e = make_entry("k", "v", ttl=1000.0)
        assert e.expires_at is not None
        assert not e.is_expired
        assert e.remaining_ttl > 999

    def test_expired(self):
        e = make_entry("k", "v", ttl=0.001)
        time.sleep(0.02)
        assert e.is_expired
        assert e.remaining_ttl == 0.0

    def test_touch_increments_access_count(self):
        e = make_entry("k", "v")
        assert e.access_count == 0
        e.touch()
        assert e.access_count == 1
        e.touch()
        assert e.access_count == 2

    def test_touch_extends_sliding_window(self):
        e = make_entry("k", "v", ttl=1.0, sliding_window=10.0)
        original_expires = e.expires_at
        time.sleep(0.01)
        e.touch()
        assert e.expires_at > original_expires

    def test_age_seconds(self):
        e = make_entry("k", "v")
        time.sleep(0.01)
        assert e.age_seconds >= 0.009

    def test_clone_for_level(self):
        e = make_entry("k", "v")
        e.dirty = True
        c = e.clone_for_level(CacheLevel.L2)
        assert c.level == CacheLevel.L2
        assert not c.dirty
        assert c.key == e.key

    def test_bump_version(self):
        e = make_entry("k", "v")
        assert e.version == 1
        e.bump_version()
        assert e.version == 2
        assert e.dirty

    def test_metadata(self):
        e = make_entry("k", "v", tags={"a", "b"})
        m = e.metadata()
        assert m.key == "k"
        assert "a" in m.tags
        assert not m.is_expired

    def test_tags_preserved(self):
        e = make_entry("k", "v", tags={"equity", "live"})
        assert "equity" in e.tags
        assert "live" in e.tags

    def test_priority(self):
        e = make_entry("k", "v", priority=CachePriority.HIGH)
        assert e.priority == int(CachePriority.HIGH)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Eviction Policies
# ══════════════════════════════════════════════════════════════════════════════

class TestLRUPolicy:
    def test_evicts_oldest_accessed(self):
        policy = LRUEvictionPolicy()
        entries = _entries(5)
        victims = policy.select_victims(entries, 2)
        assert victims == ["k0", "k1"]

    def test_empty_returns_empty(self):
        assert LRUEvictionPolicy().select_victims([], 3) == []

    def test_count_capped_at_len(self):
        policy = LRUEvictionPolicy()
        entries = _entries(3)
        victims = policy.select_victims(entries, 10)
        assert len(victims) == 3


class TestLFUPolicy:
    def test_evicts_least_frequent(self):
        policy = LFUEvictionPolicy()
        entries = _entries(4)
        victims = policy.select_victims(entries, 2)
        assert victims == ["k0", "k1"]  # fewest access_count

    def test_tie_broken_by_lru(self):
        policy = LFUEvictionPolicy()
        now = time.time()
        e0 = make_entry("a", 1)
        e0.access_count = 1
        e0.last_accessed = now - 10
        e1 = make_entry("b", 2)
        e1.access_count = 1
        e1.last_accessed = now
        victims = policy.select_victims([e0, e1], 1)
        assert victims == ["a"]  # same access_count, older last_accessed


class TestFIFOPolicy:
    def test_evicts_oldest_created(self):
        policy = FIFOEvictionPolicy()
        entries = _entries(5)
        victims = policy.select_victims(entries, 2)
        assert victims == ["k0", "k1"]


class TestTTLPolicy:
    def test_evicts_expired_first(self):
        policy = TTLEvictionPolicy()
        now = time.time()
        expired = make_entry("expired", 1, ttl=0.001)
        time.sleep(0.01)
        immortal = make_entry("immortal", 2)  # no TTL
        soon = make_entry("soon", 3, ttl=5.0)
        victims = policy.select_victims([immortal, expired, soon], 1)
        assert victims == ["expired"]

    def test_evicts_soonest_expiry_before_immortal(self):
        policy = TTLEvictionPolicy()
        immortal = make_entry("immortal", 1)
        soon = make_entry("soon", 2, ttl=1.0)
        later = make_entry("later", 3, ttl=60.0)
        victims = policy.select_victims([immortal, later, soon], 1)
        assert victims == ["soon"]


class TestSizePolicy:
    def test_evicts_largest_first(self):
        policy = SizeEvictionPolicy()
        entries = _entries(4)
        # k0 has size_bytes = n*10 = 40 (largest)
        victims = policy.select_victims(entries, 1)
        assert victims == ["k0"]


class TestPriorityPolicy:
    def test_evicts_lowest_priority_first(self):
        policy = PriorityEvictionPolicy()
        entries = _entries(4)
        # k0 has priority=200 (lowest = first to evict)
        victims = policy.select_victims(entries, 1)
        assert victims == ["k0"]


class TestNullPolicy:
    def test_never_evicts(self):
        policy = NullEvictionPolicy()
        entries = _entries(10)
        assert policy.select_victims(entries, 5) == []


class TestMakeEvictionPolicy:
    def test_lru(self):
        p = make_eviction_policy(EvictionPolicy.LRU)
        assert isinstance(p, LRUEvictionPolicy)

    def test_lfu(self):
        assert isinstance(make_eviction_policy(EvictionPolicy.LFU), LFUEvictionPolicy)

    def test_fifo(self):
        assert isinstance(make_eviction_policy(EvictionPolicy.FIFO), FIFOEvictionPolicy)

    def test_ttl(self):
        assert isinstance(make_eviction_policy(EvictionPolicy.TTL), TTLEvictionPolicy)

    def test_size(self):
        assert isinstance(make_eviction_policy(EvictionPolicy.SIZE), SizeEvictionPolicy)

    def test_priority(self):
        assert isinstance(make_eviction_policy(EvictionPolicy.PRIORITY), PriorityEvictionPolicy)

    def test_none(self):
        assert isinstance(make_eviction_policy(EvictionPolicy.NONE), NullEvictionPolicy)


# ══════════════════════════════════════════════════════════════════════════════
# 3. LatencyTracker & CacheMetrics
# ══════════════════════════════════════════════════════════════════════════════

class TestLatencyTracker:
    def test_percentiles(self):
        tracker = LatencyTracker(window=100)
        for i in range(1, 101):
            tracker.record(float(i))
        assert tracker.p50 >= 49.0
        assert tracker.p95 >= 94.0
        assert tracker.p99 >= 98.0

    def test_empty(self):
        tracker = LatencyTracker()
        assert tracker.p50 == 0.0
        assert tracker.avg == 0.0

    def test_reset(self):
        tracker = LatencyTracker()
        tracker.record(100.0)
        tracker.reset()
        assert tracker.p50 == 0.0


class TestCacheMetrics:
    def test_hit_ratio(self):
        m = CacheMetrics()
        m.record_hit(1.0)
        m.record_hit(1.0)
        m.record_miss()
        assert abs(m.hit_ratio - 2 / 3) < 0.01

    def test_miss_ratio(self):
        m = CacheMetrics()
        m.record_miss()
        assert m.miss_ratio == 1.0

    def test_zero_traffic(self):
        m = CacheMetrics()
        assert m.hit_ratio == 0.0

    def test_snapshot_keys(self):
        m = CacheMetrics("test")
        snap = m.snapshot()
        assert snap["hits"] == 0
        assert "latency_p50_ms" in snap
        assert "hit_ratio" in snap

    def test_level_tracking(self):
        m = CacheMetrics()
        m.record_hit(1.0, level="l1")
        m.record_hit(2.0, level="l2")
        snap = m.snapshot()
        assert snap["l1_hits"] == 1
        assert snap["l2_hits"] == 1

    def test_region_metrics(self):
        m = CacheMetrics()
        m.record_hit(1.0, region="quotes")
        m.record_miss(region="quotes")
        rm = m.region_snapshot("quotes")
        assert rm is not None
        assert rm["hits"] == 1
        assert rm["misses"] == 1

    def test_reset(self):
        m = CacheMetrics()
        m.record_hit(1.0)
        m.record_miss()
        m.reset()
        assert m.hit_ratio == 0.0
        assert m.snapshot()["hits"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# 4. CacheContext
# ══════════════════════════════════════════════════════════════════════════════

class TestCacheContext:
    def setup_method(self):
        reset_cache_context()

    def test_default_region(self):
        assert current_region() == DEFAULT_REGION

    def test_cache_region_cm(self):
        with cache_region("quotes"):
            assert current_region() == "quotes"
        assert current_region() == DEFAULT_REGION

    def test_nested_regions(self):
        with cache_region("outer"):
            assert current_region() == "outer"
            with cache_region("inner"):
                assert current_region() == "inner"
            assert current_region() == "outer"

    def test_set_region(self):
        from iios.infrastructure.cache import set_region
        set_region("trades")
        assert current_region() == "trades"

    def test_loader_registration(self):
        ctx = get_cache_context()
        ctx.register_loader("quotes", lambda k: f"loaded:{k}")
        loader = ctx.get_loader("quotes")
        assert loader is not None
        assert loader("KEY") == "loaded:KEY"

    def test_batch_mode(self):
        ctx = get_cache_context()
        assert not ctx.is_batch_mode()
        ctx.enter_batch()
        assert ctx.is_batch_mode()
        ctx.exit_batch()
        assert not ctx.is_batch_mode()


# ══════════════════════════════════════════════════════════════════════════════
# 5. CacheRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestCacheRegistry:
    def setup_method(self):
        reset_cache_registry()

    def test_default_regions_registered(self):
        reg = get_cache_registry()
        assert reg.has(DEFAULT_REGION)
        assert reg.has("system")
        assert reg.has("metrics")

    def test_register_and_get(self):
        reg = get_cache_registry()
        cfg = CacheRegionConfig(name="quotes", l1_max_size=5000, default_ttl=30.0)
        reg.register(cfg)
        fetched = reg.get("quotes")
        assert fetched.l1_max_size == 5000

    def test_not_found_raises(self):
        reg = get_cache_registry()
        with pytest.raises(CacheRegionNotFoundError):
            reg.get("nonexistent")

    def test_get_optional(self):
        reg = get_cache_registry()
        assert reg.get_optional("nonexistent") is None

    def test_unregister(self):
        reg = get_cache_registry()
        reg.register(CacheRegionConfig(name="temp"))
        assert reg.has("temp")
        assert reg.unregister("temp")
        assert not reg.has("temp")

    def test_list_names(self):
        reg = get_cache_registry()
        names = reg.list_names()
        assert DEFAULT_REGION in names

    def test_singleton(self):
        r1 = get_cache_registry()
        r2 = get_cache_registry()
        assert r1 is r2

    def test_invalid_config_rejected(self):
        with pytest.raises(CacheConfigError):
            CacheRegionConfig(name="bad", l1_max_size=0).validate()


# ══════════════════════════════════════════════════════════════════════════════
# 6. L1MemoryProvider
# ══════════════════════════════════════════════════════════════════════════════

class TestL1MemoryProvider:
    def test_put_and_get(self):
        p = L1MemoryProvider(max_size=100)
        entry = make_entry("k", "v")
        p.put("k", entry)
        result = p.get("k")
        assert result is not None
        assert result.value == "v"

    def test_miss_returns_none(self):
        p = L1MemoryProvider()
        assert p.get("missing") is None

    def test_expired_returns_none(self):
        p = L1MemoryProvider()
        entry = make_entry("k", "v", ttl=0.001)
        p.put("k", entry)
        time.sleep(0.02)
        assert p.get("k") is None

    def test_delete(self):
        p = L1MemoryProvider()
        p.put("k", make_entry("k", "v"))
        assert p.delete("k")
        assert p.get("k") is None

    def test_exists(self):
        p = L1MemoryProvider()
        p.put("k", make_entry("k", "v"))
        assert p.exists("k")
        assert not p.exists("missing")

    def test_clear(self):
        p = L1MemoryProvider()
        for i in range(5):
            p.put(f"k{i}", make_entry(f"k{i}", i))
        n = p.clear()
        assert n == 5
        assert p.size() == 0

    def test_eviction_on_overflow(self):
        p = L1MemoryProvider(max_size=3, policy=EvictionPolicy.LRU)
        for i in range(5):
            p.put(f"k{i}", make_entry(f"k{i}", i))
        # Should have evicted to stay at/near max_size
        assert p.size() <= 3

    def test_stats_hit_miss(self):
        p = L1MemoryProvider()
        p.put("k", make_entry("k", "v"))
        p.get("k")     # hit
        p.get("nope")  # miss
        s = p.stats()
        assert s.hits == 1
        assert s.misses == 1

    def test_atomic_increment(self):
        p = L1MemoryProvider()
        v = p.atomic_increment("counter", delta=1, default=0)
        assert v == 1
        v = p.atomic_increment("counter", delta=5)
        assert v == 6

    def test_keys_excludes_expired(self):
        p = L1MemoryProvider()
        p.put("live", make_entry("live", "v", ttl=1000))
        p.put("dead", make_entry("dead", "v", ttl=0.001))
        time.sleep(0.02)
        assert "live" in p.keys()
        assert "dead" not in p.keys()

    def test_purge_expired(self):
        p = L1MemoryProvider()
        p.put("live", make_entry("live", "v", ttl=1000))
        p.put("dead", make_entry("dead", "v", ttl=0.001))
        time.sleep(0.02)
        n = p.purge_expired()
        assert n >= 1


# ══════════════════════════════════════════════════════════════════════════════
# 7. L2SharedProvider
# ══════════════════════════════════════════════════════════════════════════════

class TestL2SharedProvider:
    def test_basic_put_get(self):
        p = L2SharedProvider(max_size=100)
        p.put("k", make_entry("k", {"price": 100}))
        result = p.get("k")
        assert result is not None
        assert result.value == {"price": 100}

    def test_eviction(self):
        p = L2SharedProvider(max_size=3, policy=EvictionPolicy.LRU)
        for i in range(5):
            p.put(f"k{i}", make_entry(f"k{i}", i))
        assert p.size() <= 3

    def test_compression_roundtrip(self):
        from iios.infrastructure.cache import CompressionAlgo
        p = L2SharedProvider(max_size=100, compression=True, compress_algo=CompressionAlgo.ZLIB)
        original = {"symbol": "RELIANCE", "price": 2500, "data": list(range(100))}
        entry = make_entry("k", original)
        p.put("k", entry)
        result = p.get("k")
        assert result is not None
        assert result.value == original

    def test_expired_returns_none(self):
        p = L2SharedProvider(max_size=100)
        p.put("k", make_entry("k", "v", ttl=0.001))
        time.sleep(0.02)
        assert p.get("k") is None


# ══════════════════════════════════════════════════════════════════════════════
# 8. L3DistributedProvider
# ══════════════════════════════════════════════════════════════════════════════

class TestL3DistributedProvider:
    def test_always_misses(self):
        p = L3DistributedProvider()
        assert p.get("k") is None

    def test_put_pretends_success(self):
        p = L3DistributedProvider()
        assert p.put("k", make_entry("k", "v"))

    def test_exists_false(self):
        p = L3DistributedProvider()
        assert not p.exists("k")

    def test_level(self):
        p = L3DistributedProvider()
        assert p.level == CacheLevel.L3


# ══════════════════════════════════════════════════════════════════════════════
# 9. CacheEngine — single level
# ══════════════════════════════════════════════════════════════════════════════

class TestCacheEngineSingleLevel:
    def _engine(self, max_size=100, ttl=300.0, policy=EvictionPolicy.LRU):
        l1 = L1MemoryProvider(max_size=max_size, policy=policy)
        return CacheEngine(l1=l1, region="test", default_ttl=ttl)

    def test_put_and_get(self):
        eng = self._engine()
        eng.put("k", "v")
        assert eng.get("k") == "v"

    def test_miss_returns_none(self):
        eng = self._engine()
        assert eng.get("nope") is None

    def test_ttl_expiry(self):
        eng = self._engine(ttl=0.01)
        eng.put("k", "v")
        time.sleep(0.05)
        assert eng.get("k") is None

    def test_explicit_ttl_override(self):
        eng = self._engine(ttl=1000)
        eng.put("k", "v", ttl=0.01)
        time.sleep(0.05)
        assert eng.get("k") is None

    def test_delete(self):
        eng = self._engine()
        eng.put("k", "v")
        assert eng.delete("k")
        assert eng.get("k") is None

    def test_exists(self):
        eng = self._engine()
        eng.put("k", "v")
        assert eng.exists("k")
        assert not eng.exists("nope")

    def test_replace_existing(self):
        eng = self._engine()
        eng.put("k", "old")
        assert eng.replace("k", "new")
        assert eng.get("k") == "new"

    def test_replace_missing_noop(self):
        eng = self._engine()
        assert not eng.replace("missing", "v")

    def test_get_multi(self):
        eng = self._engine()
        eng.put("a", 1)
        eng.put("b", 2)
        result = eng.get_multi(["a", "b", "c"])
        assert result == {"a": 1, "b": 2}

    def test_put_multi(self):
        eng = self._engine()
        n = eng.put_multi({"x": 1, "y": 2, "z": 3})
        assert n == 3
        assert eng.get("y") == 2

    def test_delete_multi(self):
        eng = self._engine()
        eng.put_multi({"a": 1, "b": 2, "c": 3})
        n = eng.delete_multi(["a", "b"])
        assert n == 2
        assert eng.get("c") == 3

    def test_increment(self):
        eng = self._engine()
        assert eng.increment("counter") == 1
        assert eng.increment("counter", 4) == 5

    def test_decrement(self):
        eng = self._engine()
        eng.put("counter", 10)
        assert eng.decrement("counter", 3) == 7

    def test_tag_invalidation(self):
        eng = self._engine()
        eng.put("a", 1, tags={"equities"})
        eng.put("b", 2, tags={"equities"})
        eng.put("c", 3, tags={"bonds"})
        n = eng.invalidate_by_tag("equities")
        assert n == 2
        assert eng.get("a") is None
        assert eng.get("b") is None
        assert eng.get("c") == 3

    def test_namespace_clear(self):
        eng = self._engine()
        eng.put("trades:RELIANCE", 1)
        eng.put("trades:TCS", 2)
        eng.put("portfolio:main", 3)
        n = eng.clear_namespace("trades")
        assert n == 2
        assert eng.get("portfolio:main") == 3

    def test_clear_region(self):
        eng = self._engine()
        eng.put("a", 1)
        eng.put("b", 2)
        n = eng.clear_region()
        assert n >= 2

    def test_warm_up(self):
        eng = self._engine()
        n = eng.warm_up({"a": 1, "b": 2, "c": 3})
        assert n == 3
        assert eng.get("b") == 2

    def test_versioned_update(self):
        eng = self._engine()
        eng.put("k", "v1")
        entry = eng.get_entry("k")
        assert entry is not None
        eng.update("k", "v2", expected_version=entry.version)
        assert eng.get("k") == "v2"

    def test_versioned_conflict_raises(self):
        eng = self._engine()
        eng.put("k", "v1")
        with pytest.raises(CacheVersionConflictError):
            eng.update("k", "v2", expected_version=999)

    def test_metrics_hit_ratio(self):
        eng = self._engine()
        eng.put("k", "v")
        eng.get("k")   # hit
        eng.get("x")   # miss
        snap = eng.stats_snapshot()
        assert snap["hits"] == 1
        assert snap["misses"] == 1

    def test_read_through_loader(self):
        l1 = L1MemoryProvider(max_size=100)
        eng = CacheEngine(
            l1=l1,
            read_policy=ReadPolicy.READ_THROUGH,
            loader=lambda k: f"loaded:{k}",
            region="rt",
        )
        val = eng.get("mykey")
        assert val == "loaded:mykey"
        # Second call should hit cache
        val2 = eng.get("mykey")
        assert val2 == "loaded:mykey"


# ══════════════════════════════════════════════════════════════════════════════
# 10. CacheEngine — multi-level (L1+L2)
# ══════════════════════════════════════════════════════════════════════════════

class TestCacheEngineMultiLevel:
    def _engine(self, write_policy=WritePolicy.WRITE_THROUGH):
        l1 = L1MemoryProvider(max_size=10, policy=EvictionPolicy.LRU)
        l2 = L2SharedProvider(max_size=100)
        return CacheEngine(l1=l1, l2=l2, write_policy=write_policy, region="ml")

    def test_write_through_stores_in_both_levels(self):
        eng = self._engine(WritePolicy.WRITE_THROUGH)
        eng.put("k", "v")
        # Read directly from L1 provider
        assert eng._l1.get("k") is not None
        # Read directly from L2 provider
        assert eng._l2.get("k") is not None

    def test_write_back_stores_only_l1(self):
        eng = self._engine(WritePolicy.WRITE_BACK)
        eng.put("k", "v")
        assert eng._l1.get("k") is not None
        # L2 should NOT have it yet
        assert eng._l2.get("k") is None

    def test_write_back_sync_flushes_to_l2(self):
        eng = self._engine(WritePolicy.WRITE_BACK)
        eng.put("k", "v")
        result = eng.sync()
        assert result.flushed >= 1
        assert eng._l2.get("k") is not None

    def test_l1_eviction_then_l2_promotion(self):
        """Evict key from L1 by overflow, then confirm it's still in L2."""
        l1 = L1MemoryProvider(max_size=3, policy=EvictionPolicy.LRU)
        l2 = L2SharedProvider(max_size=100)
        eng = CacheEngine(l1=l1, l2=l2, write_policy=WritePolicy.WRITE_THROUGH, region="ml2")
        eng.put("target", "value")
        # Fill L1 to evict "target"
        for i in range(10):
            eng.put(f"filler{i}", f"val{i}")
        # L1 should have evicted "target", but L2 should still have it
        assert l2.get("target") is not None
        # Getting "target" should find it in L2 and promote to L1
        val = eng.get("target")
        assert val == "value"

    def test_l2_stats_tracked(self):
        eng = self._engine()
        eng.put("k", "v")
        # Evict from L1 manually
        eng._l1.delete("k")
        eng.get("k")  # should hit L2
        snap = eng.stats_snapshot()
        assert snap["l2_hits"] >= 1


# ══════════════════════════════════════════════════════════════════════════════
# 11. Write-back sync result
# ══════════════════════════════════════════════════════════════════════════════

class TestSyncResult:
    def test_success_when_no_failures(self):
        r = SyncResult(flushed=5, failed=0)
        assert r.success

    def test_failure_when_any_failure(self):
        r = SyncResult(flushed=3, failed=1)
        assert not r.success


# ══════════════════════════════════════════════════════════════════════════════
# 12. CacheFactory
# ══════════════════════════════════════════════════════════════════════════════

class TestCacheFactory:
    def setup_method(self):
        CacheFactory.reset_shared_l2()

    def test_simple(self):
        eng = CacheFactory.simple("test", max_size=50)
        assert isinstance(eng, CacheEngine)
        eng.put("k", "v")
        assert eng.get("k") == "v"

    def test_two_level(self):
        eng = CacheFactory.two_level("test_2l", l1_max=10, l2_max=100, shared_l2=False)
        assert eng._l2 is not None

    def test_create_engine_from_config(self):
        cfg = CacheRegionConfig(
            name="test_region",
            levels=[CacheLevel.L1, CacheLevel.L2],
            l1_max_size=200,
            l2_max_size=2000,
        )
        eng = CacheFactory.create_engine(cfg, shared_l2=False)
        assert eng._l2 is not None

    def test_shared_l2_same_instance(self):
        cfg = CacheRegionConfig(name="shared_test", l1_max_size=100)
        l2_a = CacheFactory.create_l2(cfg, shared=True)
        l2_b = CacheFactory.create_l2(cfg, shared=True)
        assert l2_a is l2_b

    def test_create_from_name(self):
        reset_cache_registry()
        eng = CacheFactory.create_from_name(DEFAULT_REGION)
        assert isinstance(eng, CacheEngine)


# ══════════════════════════════════════════════════════════════════════════════
# 13. MultiLevelCacheManager
# ══════════════════════════════════════════════════════════════════════════════

class TestMultiLevelCacheManager:
    def setup_method(self):
        reset_ml_cache_manager()
        CacheFactory.reset_shared_l2()

    def teardown_method(self):
        reset_ml_cache_manager()

    def test_put_and_get(self):
        mgr = get_ml_cache_manager()
        mgr.put("k", "v")
        assert mgr.get("k") == "v"

    def test_default_region(self):
        mgr = get_ml_cache_manager()
        mgr.put("key1", 42)
        assert mgr.get("key1", DEFAULT_REGION) == 42

    def test_custom_region(self):
        mgr = get_ml_cache_manager()
        cfg = CacheRegionConfig(name="quotes", l1_max_size=1000)
        mgr.register_region(cfg)
        mgr.put("RELIANCE", 2500, region="quotes")
        assert mgr.get("RELIANCE", region="quotes") == 2500

    def test_delete(self):
        mgr = get_ml_cache_manager()
        mgr.put("k", "v")
        assert mgr.delete("k")
        assert mgr.get("k") is None

    def test_exists(self):
        mgr = get_ml_cache_manager()
        mgr.put("k", "v")
        assert mgr.exists("k")
        assert not mgr.exists("missing")

    def test_replace(self):
        mgr = get_ml_cache_manager()
        mgr.put("k", "old")
        assert mgr.replace("k", "new")
        assert mgr.get("k") == "new"

    def test_replace_missing(self):
        mgr = get_ml_cache_manager()
        assert not mgr.replace("missing", "v")

    def test_increment(self):
        mgr = get_ml_cache_manager()
        assert mgr.increment("cnt") == 1
        assert mgr.increment("cnt", 9) == 10

    def test_decrement(self):
        mgr = get_ml_cache_manager()
        mgr.put("cnt", 10)
        assert mgr.decrement("cnt", 3) == 7

    def test_get_multi(self):
        mgr = get_ml_cache_manager()
        mgr.put_multi({"a": 1, "b": 2})
        result = mgr.get_multi(["a", "b", "c"])
        assert result == {"a": 1, "b": 2}

    def test_put_multi(self):
        mgr = get_ml_cache_manager()
        n = mgr.put_multi({"x": 1, "y": 2})
        assert n == 2

    def test_delete_multi(self):
        mgr = get_ml_cache_manager()
        mgr.put_multi({"a": 1, "b": 2, "c": 3})
        assert mgr.delete_multi(["a", "b"]) == 2
        assert mgr.get("c") == 3

    def test_invalidate_by_tag(self):
        mgr = get_ml_cache_manager()
        mgr.put("t1", 1, tags={"live"})
        mgr.put("t2", 2, tags={"live"})
        mgr.put("t3", 3, tags={"historic"})
        n = mgr.invalidate_by_tag("live")
        assert n == 2
        assert mgr.get("t1") is None
        assert mgr.get("t3") == 3

    def test_clear_namespace(self):
        mgr = get_ml_cache_manager()
        mgr.put("orders:1", "a")
        mgr.put("orders:2", "b")
        mgr.put("trades:1", "c")
        n = mgr.clear_namespace("orders")
        assert n == 2
        assert mgr.get("trades:1") == "c"

    def test_clear_region(self):
        mgr = get_ml_cache_manager()
        mgr.put_multi({"a": 1, "b": 2, "c": 3})
        n = mgr.clear_region()
        assert n >= 3

    def test_warm_up(self):
        mgr = get_ml_cache_manager()
        n = mgr.warm_up({"p1": 100, "p2": 200, "p3": 300})
        assert n == 3
        assert mgr.get("p2") == 200

    def test_ttl_expiry(self):
        mgr = get_ml_cache_manager()
        mgr.put("k", "v", ttl=0.01)
        time.sleep(0.05)
        assert mgr.get("k") is None

    def test_stats(self):
        mgr = get_ml_cache_manager()
        mgr.put("k", "v")
        mgr.get("k")
        snap = mgr.stats()
        assert snap["hits"] >= 1

    def test_all_stats(self):
        mgr = get_ml_cache_manager()
        cfg = CacheRegionConfig(name="stat_region")
        mgr.register_region(cfg)
        mgr.put("k", "v", region="stat_region")
        all_stats = mgr.all_stats()
        assert "stat_region" in all_stats

    def test_sync_write_back(self):
        mgr = get_ml_cache_manager()
        cfg = CacheRegionConfig(
            name="wb_region",
            levels=[CacheLevel.L1, CacheLevel.L2],
            write_policy=WritePolicy.WRITE_BACK,
        )
        mgr.register_region(cfg)
        mgr.put("k", "v", region="wb_region")
        result_map = mgr.sync(region="wb_region")
        assert "wb_region" in result_map

    def test_singleton(self):
        mgr1 = get_ml_cache_manager()
        mgr2 = get_ml_cache_manager()
        assert mgr1 is mgr2

    def test_clear_all(self):
        mgr = get_ml_cache_manager()
        mgr.put("a", 1)
        mgr.put("b", 2)
        cleared = mgr.clear_all()
        assert DEFAULT_REGION in cleared


# ══════════════════════════════════════════════════════════════════════════════
# 14. Concurrency
# ══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_puts_l1(self):
        p = L1MemoryProvider(max_size=500)
        errors = []

        def _write(n: int) -> None:
            try:
                for i in range(50):
                    p.put(f"thread{n}:k{i}", make_entry(f"thread{n}:k{i}", i))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_write, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_concurrent_increment(self):
        eng = CacheFactory.simple("incr_test", max_size=100)
        eng.put("counter", 0)
        results = []
        lock = threading.Lock()

        def _inc() -> None:
            v = eng.increment("counter")
            with lock:
                results.append(v)

        threads = [threading.Thread(target=_inc) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # Final counter should equal number of threads
        assert eng.get("counter") == 20

    def test_concurrent_read_write(self):
        p = L1MemoryProvider(max_size=100)
        stop = threading.Event()
        errors = []

        def _writer():
            i = 0
            while not stop.is_set():
                p.put(f"k{i % 10}", make_entry(f"k{i % 10}", i))
                i += 1

        def _reader():
            while not stop.is_set():
                try:
                    p.get("k5")
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=_writer)] + [threading.Thread(target=_reader) for _ in range(3)]
        for t in threads:
            t.start()
        time.sleep(0.1)
        stop.set()
        for t in threads:
            t.join()
        assert not errors


# ══════════════════════════════════════════════════════════════════════════════
# 15. Performance / reliability
# ══════════════════════════════════════════════════════════════════════════════

class TestPerformanceReliability:
    def test_bulk_put_1000(self):
        eng = CacheFactory.simple("bulk", max_size=2000)
        data = {f"k{i}": i for i in range(1000)}
        n = eng.put_multi(data)
        assert n == 1000

    def test_bulk_get_1000(self):
        eng = CacheFactory.simple("bulk2", max_size=2000)
        data = {f"k{i}": i for i in range(1000)}
        eng.put_multi(data)
        keys = [f"k{i}" for i in range(1000)]
        result = eng.get_multi(keys)
        assert len(result) == 1000

    def test_eviction_stability(self):
        """Write 5x max_size entries — cache should not raise, just evict."""
        p = L1MemoryProvider(max_size=100, policy=EvictionPolicy.LRU)
        for i in range(500):
            p.put(f"k{i}", make_entry(f"k{i}", i))
        assert p.size() <= 100

    def test_ttl_mass_expiry(self):
        eng = CacheFactory.simple("ttl_mass", max_size=200)
        for i in range(50):
            eng.put(f"short{i}", i, ttl=0.01)
        for i in range(50):
            eng.put(f"long{i}", i, ttl=1000)
        time.sleep(0.05)
        # Short entries should be gone
        for i in range(50):
            assert eng.get(f"short{i}") is None
        # Long entries should still be present
        for i in range(50):
            assert eng.get(f"long{i}") == i

    def test_write_through_latency_reasonable(self):
        """Single put+get should complete in well under 10ms."""
        l1 = L1MemoryProvider(max_size=1000)
        l2 = L2SharedProvider(max_size=5000)
        eng = CacheEngine(l1=l1, l2=l2, region="perf")
        t0 = time.monotonic()
        for _ in range(100):
            eng.put("k", "v")
            eng.get("k")
        elapsed_ms = (time.monotonic() - t0) * 1000
        assert elapsed_ms < 500  # 100 put+get cycles in < 500ms
