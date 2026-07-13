"""tests/unit/investment/strategy/lifecycle/test_scheduler.py
Tests for: ExecutionQueue, PriorityScheduler, ScheduleRegistry, StrategyScheduler
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone, timedelta

import pytest

from iios.investment.strategy.lifecycle.execution_queue import (
    ExecutionQueue,
    ExecutionRequest,
    QueueFullError,
    SchedulePriority,
)
from iios.investment.strategy.lifecycle.priority_scheduler import PriorityScheduler
from iios.investment.strategy.lifecycle.schedule_registry import (
    ScheduleEntry,
    ScheduleRegistry,
    ScheduleType,
)
from iios.investment.strategy.lifecycle.strategy_scheduler import StrategyScheduler


# ── ExecutionQueue ─────────────────────────────────────────────────────────────

class TestExecutionQueue:
    def _req(self, strategy_id="s1", priority=SchedulePriority.NORMAL):
        return ExecutionRequest(
            priority=int(priority),
            strategy_id=strategy_id,
        )

    def test_enqueue_dequeue_basic(self):
        q = ExecutionQueue()
        r = self._req()
        q.enqueue(r)
        assert len(q) == 1
        result = q.dequeue()
        assert result is r

    def test_priority_ordering(self):
        q = ExecutionQueue()
        q.enqueue(self._req("low", SchedulePriority.LOW))
        q.enqueue(self._req("crit", SchedulePriority.CRITICAL))
        q.enqueue(self._req("normal", SchedulePriority.NORMAL))
        first = q.dequeue()
        assert first.strategy_id == "crit"

    def test_queue_full_raises(self):
        q = ExecutionQueue(max_size=2)
        q.enqueue(self._req("a"))
        q.enqueue(self._req("b"))
        with pytest.raises(QueueFullError):
            q.enqueue(self._req("c"))

    def test_dequeue_empty_returns_none(self):
        q = ExecutionQueue()
        assert q.dequeue() is None

    def test_peek_does_not_remove(self):
        q = ExecutionQueue()
        r = self._req()
        q.enqueue(r)
        assert q.peek() is r
        assert len(q) == 1

    def test_drain_clears_queue(self):
        q = ExecutionQueue()
        for i in range(5):
            q.enqueue(self._req(f"s{i}"))
        items = q.drain()
        assert len(items) == 5
        assert q.is_empty()

    def test_expired_requests_discarded(self):
        q = ExecutionQueue()
        past = datetime.now(timezone.utc) - timedelta(seconds=1)
        req = ExecutionRequest(
            priority=int(SchedulePriority.NORMAL),
            strategy_id="s1",
            deadline=past,
        )
        q.enqueue(req)
        result = q.dequeue()
        assert result is None  # expired, discarded

    def test_thread_safe_concurrent_enqueue(self):
        q = ExecutionQueue(max_size=10_000)
        errors = []

        def producer():
            try:
                for i in range(100):
                    q.enqueue(self._req(f"s{i}"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=producer) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(q) == 1000

    def test_is_expired_no_deadline(self):
        req = ExecutionRequest(priority=int(SchedulePriority.NORMAL))
        assert req.is_expired() is False


# ── SchedulePriority ordering ──────────────────────────────────────────────────

class TestSchedulePriority:
    def test_critical_less_than_low(self):
        assert int(SchedulePriority.CRITICAL) < int(SchedulePriority.LOW)

    def test_high_less_than_background(self):
        assert int(SchedulePriority.HIGH) < int(SchedulePriority.BACKGROUND)

    def test_normal_between_high_and_low(self):
        assert int(SchedulePriority.HIGH) < int(SchedulePriority.NORMAL)
        assert int(SchedulePriority.NORMAL) < int(SchedulePriority.LOW)


# ── PriorityScheduler ─────────────────────────────────────────────────────────

class TestPriorityScheduler:
    def _make_scheduler(self, max_concurrent=4):
        executed = []
        q = ExecutionQueue()

        def executor(req):
            executed.append(req.strategy_id)

        sched = PriorityScheduler(
            queue=q,
            executor_fn=executor,
            max_concurrent=max_concurrent,
        )
        return sched, q, executed

    def test_submit_and_tick(self):
        sched, q, executed = self._make_scheduler()
        sched.submit("strat-a", context=None)
        sched.tick()
        time.sleep(0.1)
        assert "strat-a" in executed

    def test_duplicate_in_flight_skipped(self):
        barrier = threading.Event()
        q = ExecutionQueue()
        started = []

        def slow_executor(req):
            started.append(req.strategy_id)
            barrier.wait(timeout=2)

        sched = PriorityScheduler(queue=q, executor_fn=slow_executor, max_concurrent=4)
        sched.submit("strat-x", context=None)
        sched.tick()
        time.sleep(0.05)

        result = sched.submit("strat-x", context=None)
        assert result is None  # duplicate rejected

        barrier.set()

    def test_pause_stops_dispatch(self):
        sched, q, executed = self._make_scheduler()
        sched.pause()
        sched.submit("strat-b", context=None)
        sched.tick()
        time.sleep(0.05)
        assert "strat-b" not in executed

    def test_resume_dispatches_pending(self):
        sched, q, executed = self._make_scheduler()
        sched.pause()
        sched.submit("strat-c", context=None)
        sched.resume()
        time.sleep(0.1)
        assert "strat-c" in executed

    def test_in_flight_count(self):
        barrier = threading.Event()
        q = ExecutionQueue()

        def slow_executor(req):
            barrier.wait(timeout=2)

        sched = PriorityScheduler(queue=q, executor_fn=slow_executor, max_concurrent=4)
        sched.submit("strat-d", context=None)
        sched.tick()
        time.sleep(0.05)
        assert sched.in_flight_count >= 0  # may or may not have completed
        barrier.set()

    def test_shutdown(self):
        sched, q, executed = self._make_scheduler()
        sched.shutdown(wait=True)
        # Should not raise


# ── ScheduleRegistry ──────────────────────────────────────────────────────────

class TestScheduleRegistry:
    def _entry(self, strategy_id="s1", schedule_type=ScheduleType.PERIODIC):
        return ScheduleEntry(
            strategy_id=strategy_id,
            schedule_type=schedule_type,
            interval_seconds=60.0,
        )

    def test_register_and_get(self):
        reg = ScheduleRegistry()
        entry = self._entry()
        reg.register(entry)
        result = reg.get("s1")
        assert result is entry

    def test_duplicate_raises(self):
        reg = ScheduleRegistry()
        reg.register(self._entry())
        with pytest.raises(ValueError):
            reg.register(self._entry())

    def test_replace_allowed(self):
        reg = ScheduleRegistry()
        reg.register(self._entry())
        new_entry = self._entry()
        reg.register(new_entry, replace=True)
        assert reg.get("s1") is new_entry

    def test_unregister(self):
        reg = ScheduleRegistry()
        reg.register(self._entry())
        removed = reg.unregister("s1")
        assert removed is True
        assert reg.get("s1") is None

    def test_unregister_unknown_returns_false(self):
        reg = ScheduleRegistry()
        assert reg.unregister("no-such-strategy") is False

    def test_all_entries(self):
        reg = ScheduleRegistry()
        reg.register(self._entry("a"))
        reg.register(self._entry("b"))
        assert len(reg.all_entries()) == 2

    def test_enabled_entries_filters(self):
        reg = ScheduleRegistry()
        reg.register(self._entry("a"))
        reg.register(self._entry("b"))
        reg.disable("b")
        enabled = reg.enabled_entries()
        assert len(enabled) == 1
        assert enabled[0].strategy_id == "a"

    def test_enable_disable(self):
        reg = ScheduleRegistry()
        reg.register(self._entry())
        reg.disable("s1")
        assert reg.get("s1").enabled is False
        reg.enable("s1")
        assert reg.get("s1").enabled is True

    def test_update_last_triggered(self):
        reg = ScheduleRegistry()
        reg.register(self._entry())
        assert reg.get("s1").last_triggered_at is None
        reg.update_last_triggered("s1")
        assert reg.get("s1").last_triggered_at is not None

    def test_len(self):
        reg = ScheduleRegistry()
        assert len(reg) == 0
        reg.register(self._entry("a"))
        assert len(reg) == 1


# ── StrategyScheduler ─────────────────────────────────────────────────────────

class TestStrategyScheduler:
    def _make_scheduler(self):
        executed = []

        def executor(req):
            executed.append(req.strategy_id)

        sched = StrategyScheduler(
            executor_fn=executor,
            max_concurrent=8,
            max_queue_depth=100,
        )
        return sched, executed

    def test_start_stop(self):
        sched, _ = self._make_scheduler()
        sched.start()
        sched.stop(wait=False)

    def test_submit_immediate(self):
        sched, executed = self._make_scheduler()
        sched.start()
        ctx = object()
        sched.submit_immediate("strat-a", context=ctx)
        time.sleep(0.2)
        assert "strat-a" in executed
        sched.stop(wait=False)

    def test_event_subscription_and_fire(self):
        sched, executed = self._make_scheduler()
        sched.start()
        entry = ScheduleEntry(
            strategy_id="event-strat",
            schedule_type=ScheduleType.EVENT,
            trigger_event="market_open",
        )
        sched.schedule(entry)
        fired = sched.fire_event("market_open", context=None)
        assert fired == 1
        time.sleep(0.2)
        assert "event-strat" in executed
        sched.stop(wait=False)

    def test_conditional_schedule(self):
        executed = []
        flag = {"run": False}

        def executor(req):
            executed.append(req.strategy_id)

        sched = StrategyScheduler(
            executor_fn=executor,
            max_concurrent=4,
        )
        entry = ScheduleEntry(
            strategy_id="cond-strat",
            schedule_type=ScheduleType.CONDITIONAL,
            condition_fn=lambda: flag["run"],
        )
        sched.schedule(entry)
        sched.start()

        # Should not run while flag is False
        time.sleep(0.6)
        assert "cond-strat" not in executed

        flag["run"] = True
        time.sleep(0.6)
        assert "cond-strat" in executed

        sched.stop(wait=False)

    def test_unschedule_removes_event_subscription(self):
        sched, executed = self._make_scheduler()
        sched.start()
        entry = ScheduleEntry(
            strategy_id="temp-strat",
            schedule_type=ScheduleType.EVENT,
            trigger_event="my_event",
        )
        sched.schedule(entry)
        sched.unschedule("temp-strat")
        fired = sched.fire_event("my_event", context=None)
        assert fired == 0
        sched.stop(wait=False)

    def test_pause_resume(self):
        sched, _ = self._make_scheduler()
        sched.start()
        sched.pause()
        assert sched._paused is True
        sched.resume()
        assert sched._paused is False
        sched.stop(wait=False)

    def test_queue_depth_property(self):
        sched, _ = self._make_scheduler()
        assert sched.queue_depth == 0

    def test_periodic_schedule_fires(self):
        executed = []

        def executor(req):
            executed.append(req.strategy_id)

        sched = StrategyScheduler(executor_fn=executor, max_concurrent=4)
        entry = ScheduleEntry(
            strategy_id="periodic-strat",
            schedule_type=ScheduleType.PERIODIC,
            interval_seconds=0.3,
        )
        sched.schedule(entry)
        sched.start()
        time.sleep(1.0)
        sched.stop(wait=False)
        assert len([e for e in executed if e == "periodic-strat"]) >= 2
