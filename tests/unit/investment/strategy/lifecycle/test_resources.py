"""tests/unit/investment/strategy/lifecycle/test_resources.py
Tests for: ResourceLimits, ResourceStatistics, ResourceAllocator, ResourceManager
"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager

import pytest

from iios.investment.strategy.lifecycle.resource_limits import (
    ResourceLimits,
    ResourceProfile,
)
from iios.investment.strategy.lifecycle.resource_statistics import (
    ResourceSnapshot,
    ResourceStatistics,
)
from iios.investment.strategy.lifecycle.resource_allocator import (
    AllocationError,
    AllocationTicket,
    ResourceAllocator,
)
from iios.investment.strategy.lifecycle.resource_manager import ResourceManager


# ── ResourceLimits ────────────────────────────────────────────────────────────

class TestResourceLimits:
    def test_standard_profile(self):
        lim = ResourceLimits.standard()
        assert lim.max_concurrent_strategies == 32
        assert lim.max_thread_pool_workers == 64

    def test_minimal_profile(self):
        lim = ResourceLimits.minimal()
        assert lim.max_concurrent_strategies == 4
        assert lim.max_thread_pool_workers == 8

    def test_aggressive_profile(self):
        lim = ResourceLimits.aggressive()
        assert lim.max_concurrent_strategies == 256

    def test_unlimited_profile(self):
        lim = ResourceLimits.unlimited()
        assert lim.max_concurrent_strategies == 0
        assert lim.is_unlimited_field(lim.max_concurrent_strategies) is True

    def test_frozen(self):
        lim = ResourceLimits.standard()
        with pytest.raises(Exception):
            lim.max_concurrent_strategies = 99  # type: ignore[misc]

    def test_default_admission_threshold(self):
        lim = ResourceLimits()
        assert lim.admission_threshold == pytest.approx(0.90)

    def test_default_max_retries(self):
        lim = ResourceLimits()
        assert lim.max_retries_per_strategy == 3

    def test_default_max_restarts(self):
        lim = ResourceLimits()
        assert lim.max_restarts_per_strategy == 5


# ── ResourceSnapshot ──────────────────────────────────────────────────────────

class TestResourceSnapshot:
    def test_thread_utilization_no_workers(self):
        snap = ResourceSnapshot(thread_count=0, total_workers=0)
        assert snap.thread_utilization == 0.0

    def test_thread_utilization_half(self):
        snap = ResourceSnapshot(thread_count=5, total_workers=10)
        assert snap.thread_utilization == pytest.approx(0.5)

    def test_thread_utilization_capped_at_one(self):
        snap = ResourceSnapshot(thread_count=20, total_workers=10)
        assert snap.thread_utilization == pytest.approx(1.0)

    def test_to_dict(self):
        snap = ResourceSnapshot(thread_count=2, total_workers=8)
        d = snap.to_dict()
        assert "thread_count" in d
        assert "thread_utilization" in d
        assert "captured_at" in d


# ── ResourceStatistics ────────────────────────────────────────────────────────

class TestResourceStatistics:
    def test_record_and_latest(self):
        stats = ResourceStatistics()
        snap = ResourceSnapshot(active_strategies=3)
        stats.record(snap)
        assert stats.latest() is snap

    def test_latest_empty_returns_none(self):
        stats = ResourceStatistics()
        assert stats.latest() is None

    def test_history_limited(self):
        stats = ResourceStatistics(window=3)
        for i in range(5):
            stats.record(ResourceSnapshot(active_strategies=i))
        assert len(stats.history()) <= 3

    def test_average_thread_utilization(self):
        stats = ResourceStatistics()
        for active in [2, 4, 6]:
            stats.record(ResourceSnapshot(thread_count=active, total_workers=10))
        avg = stats.average_thread_utilization(last_n=3)
        assert 0 < avg <= 1.0

    def test_peak_active_strategies(self):
        stats = ResourceStatistics()
        for a in [1, 5, 3]:
            stats.record(ResourceSnapshot(active_strategies=a))
        assert stats.peak_active_strategies() == 5

    def test_peak_empty_returns_zero(self):
        stats = ResourceStatistics()
        assert stats.peak_active_strategies() == 0


# ── ResourceAllocator ─────────────────────────────────────────────────────────

class TestResourceAllocator:
    def _allocator(self, max_concurrent=4, workers=8):
        limits = ResourceLimits(
            max_concurrent_strategies=max_concurrent,
            max_thread_pool_workers=workers,
            admission_threshold=0.95,
        )
        return ResourceAllocator(limits)

    def test_request_and_release(self):
        alloc = self._allocator()
        ticket = alloc.request("s1")
        assert ticket.strategy_id == "s1"
        assert not ticket.is_released
        assert alloc.active_count == 1
        alloc.release(ticket)
        assert ticket.is_released
        assert alloc.active_count == 0

    def test_max_concurrent_enforced(self):
        alloc = self._allocator(max_concurrent=2)
        t1 = alloc.request("s1")
        t2 = alloc.request("s2")
        with pytest.raises(AllocationError):
            alloc.request("s3")
        alloc.release(t1)
        alloc.release(t2)

    def test_utilization(self):
        alloc = self._allocator(max_concurrent=8, workers=8)
        tickets = [alloc.request(f"s{i}") for i in range(4)]
        assert alloc.utilization == pytest.approx(0.5)
        for t in tickets:
            alloc.release(t)

    def test_is_strategy_allocated(self):
        alloc = self._allocator()
        assert alloc.is_strategy_allocated("s1") is False
        ticket = alloc.request("s1")
        assert alloc.is_strategy_allocated("s1") is True
        alloc.release(ticket)
        assert alloc.is_strategy_allocated("s1") is False

    def test_cpu_weight_limit_enforced(self):
        limits = ResourceLimits(
            max_concurrent_strategies=10,
            max_thread_pool_workers=20,
            cpu_weight_limit=1.0,
            admission_threshold=0.99,
        )
        alloc = ResourceAllocator(limits)
        t1 = alloc.request("s1", cpu_weight=0.6)
        with pytest.raises(AllocationError):
            alloc.request("s2", cpu_weight=0.6)  # 0.6+0.6 > 1.0
        alloc.release(t1)

    def test_active_tickets(self):
        alloc = self._allocator()
        t = alloc.request("s1")
        assert len(alloc.active_tickets()) == 1
        alloc.release(t)

    def test_thread_safe(self):
        alloc = self._allocator(max_concurrent=100, workers=200)
        errors = []

        def worker():
            try:
                ticket = alloc.request(f"s-{threading.get_ident()}")
                time.sleep(0.01)
                alloc.release(ticket)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert alloc.active_count == 0


# ── ResourceManager ───────────────────────────────────────────────────────────

class TestResourceManager:
    def _rm(self, max_concurrent=8):
        limits = ResourceLimits(
            max_concurrent_strategies=max_concurrent,
            max_thread_pool_workers=16,
            admission_threshold=0.95,
        )
        return ResourceManager(limits=limits)

    def test_allocate_context_manager(self):
        rm = self._rm()
        with rm.allocate("s1") as ticket:
            assert ticket.strategy_id == "s1"
            assert rm.active_count == 1
        assert rm.active_count == 0

    def test_allocate_released_on_exception(self):
        rm = self._rm()
        try:
            with rm.allocate("s1") as ticket:
                raise ValueError("test")
        except ValueError:
            pass
        assert rm.active_count == 0

    def test_can_allocate_true_when_space(self):
        rm = self._rm(max_concurrent=4)
        assert rm.can_allocate() is True

    def test_can_allocate_false_when_full(self):
        limits = ResourceLimits(
            max_concurrent_strategies=1,
            max_thread_pool_workers=2,
            admission_threshold=0.99,
        )
        rm = ResourceManager(limits=limits)
        with rm.allocate("s1"):
            assert rm.can_allocate() is False

    def test_utilization(self):
        rm = self._rm()
        assert rm.utilization == 0.0

    def test_snapshot(self):
        rm = self._rm()
        snap = rm.snapshot()
        assert snap.total_workers > 0

    def test_statistics_recorded(self):
        rm = self._rm()
        with rm.allocate("s1"):
            pass
        snaps = rm.statistics.history(10)
        assert len(snaps) > 0

    def test_limits_property(self):
        rm = self._rm()
        assert rm.limits.max_concurrent_strategies == 8

    def test_concurrent_allocation(self):
        limits = ResourceLimits(
            max_concurrent_strategies=50,
            max_thread_pool_workers=100,  # large enough to avoid admission threshold
            admission_threshold=0.95,
        )
        rm = ResourceManager(limits=limits)
        errors = []
        released = []

        def worker(sid):
            try:
                with rm.allocate(sid):
                    time.sleep(0.02)
                released.append(sid)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"s{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(released) == 20
        assert rm.active_count == 0
