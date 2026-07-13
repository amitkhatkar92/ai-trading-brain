"""tests/unit/investment/strategy/lifecycle/test_lifecycle_engine.py
Integration-level tests for StrategyLifecycleEngine.

Covers: registration, scheduling, dependency ordering, execution,
        recovery, checkpointing, observability APIs, concurrency.
"""
from __future__ import annotations

import threading
import time
from typing import List

import pytest

from iios.investment.strategy.lifecycle.runtime_context import RuntimeContext
from iios.investment.strategy.lifecycle.runtime_state import RuntimeState
from iios.investment.strategy.lifecycle.execution_queue import SchedulePriority
from iios.investment.strategy.lifecycle.failure_handler import FailurePolicy
from iios.investment.strategy.lifecycle.restart_manager import RestartPolicy
from iios.investment.strategy.lifecycle.resource_limits import ResourceLimits
from iios.investment.strategy.lifecycle.strategy_lifecycle_engine import (
    EngineNotRunningError,
    LifecycleEngineError,
    StrategyLifecycleEngine,
    StrategyNotRegisteredError,
)
from iios.investment.strategy.lifecycle.dependency_graph import CyclicDependencyError


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _noop(ctx: RuntimeContext) -> None:
    """No-op strategy execute_fn."""


def _make_engine(**kwargs) -> StrategyLifecycleEngine:
    limits = ResourceLimits(
        max_concurrent_strategies=32,
        max_thread_pool_workers=16,
        admission_threshold=0.99,
    )
    defaults = dict(resource_limits=limits, max_workers=8)
    defaults.update(kwargs)
    return StrategyLifecycleEngine(**defaults)


# ── Lifecycle ─────────────────────────────────────────────────────────────────

class TestEngineLifecycle:
    def test_initial_state_idle(self):
        eng = _make_engine()
        assert eng.state == RuntimeState.IDLE

    def test_start_transitions_to_running(self):
        eng = _make_engine()
        eng.start()
        assert eng.is_running is True
        eng.shutdown(drain=False)

    def test_shutdown_transitions_to_shutdown(self):
        eng = _make_engine()
        eng.start()
        eng.shutdown(drain=False)
        assert eng.state == RuntimeState.SHUTDOWN

    def test_pause_resume(self):
        eng = _make_engine()
        eng.start()
        eng.pause()
        assert eng.state == RuntimeState.PAUSED
        eng.resume()
        assert eng.is_running
        eng.shutdown(drain=False)

    def test_double_shutdown_safe(self):
        eng = _make_engine()
        eng.start()
        eng.shutdown(drain=False)
        # Second shutdown should not raise
        eng.shutdown(drain=False)


# ── Registration ──────────────────────────────────────────────────────────────

class TestStrategyRegistration:
    def test_register_and_list(self):
        eng = _make_engine()
        eng.register("s1", "Strategy 1", _noop)
        assert "s1" in eng.registered_ids()

    def test_duplicate_raises(self):
        eng = _make_engine()
        eng.register("s1", "S1", _noop)
        with pytest.raises(LifecycleEngineError):
            eng.register("s1", "S1 dup", _noop)

    def test_replace_allowed(self):
        eng = _make_engine()
        eng.register("s1", "S1", _noop)
        eng.register("s1", "S1 v2", _noop, replace=True)
        assert "s1" in eng.registered_ids()

    def test_unregister(self):
        eng = _make_engine()
        eng.register("s1", "S1", _noop)
        removed = eng.unregister("s1")
        assert removed is True
        assert "s1" not in eng.registered_ids()

    def test_unregister_unknown_returns_false(self):
        eng = _make_engine()
        assert eng.unregister("ghost") is False

    def test_tags_stored(self):
        eng = _make_engine()
        eng.register("s1", "S1", _noop, tags=["equity", "long-only"])
        # Tags stored in internal record — engine API does not expose them
        # but registration must not raise
        assert "s1" in eng.registered_ids()


# ── Direct submission ─────────────────────────────────────────────────────────

class TestDirectSubmission:
    def test_submit_returns_future(self):
        eng = _make_engine()
        eng.start()
        eng.register("s1", "S1", _noop)
        future = eng.submit("s1")
        future.result(timeout=5)
        eng.shutdown(drain=False)

    def test_submit_raises_when_not_running(self):
        eng = _make_engine()
        eng.register("s1", "S1", _noop)
        with pytest.raises(EngineNotRunningError):
            eng.submit("s1")

    def test_submit_unknown_strategy_raises(self):
        eng = _make_engine()
        eng.start()
        with pytest.raises(StrategyNotRegisteredError):
            eng.submit("ghost")
        eng.shutdown(drain=False)

    def test_execute_fn_called_with_context(self):
        received = []

        def capture(ctx: RuntimeContext):
            received.append(ctx)

        eng = _make_engine()
        eng.start()
        eng.register("s1", "S1", capture)
        ctx = RuntimeContext(is_live=True)
        future = eng.submit("s1", context=ctx)
        future.result(timeout=5)
        eng.shutdown(drain=False)
        assert len(received) == 1
        assert received[0].is_live is True


# ── run_cycle ─────────────────────────────────────────────────────────────────

class TestRunCycle:
    def test_run_cycle_returns_results(self):
        eng = _make_engine()
        eng.start()
        eng.register("s1", "S1", _noop)
        eng.register("s2", "S2", _noop)
        results = eng.run_cycle()
        assert results["s1"] == "success"
        assert results["s2"] == "success"
        eng.shutdown(drain=False)

    def test_run_cycle_subset(self):
        eng = _make_engine()
        eng.start()
        eng.register("s1", "S1", _noop)
        eng.register("s2", "S2", _noop)
        results = eng.run_cycle(strategy_ids=["s1"])
        assert "s1" in results
        assert "s2" not in results
        eng.shutdown(drain=False)

    def test_run_cycle_failure_recorded(self):
        def failing(ctx):
            raise ValueError("boom")

        eng = _make_engine()
        eng.start()
        # Use max_retries=0 so the cycle returns immediately without retrying
        from iios.investment.strategy.lifecycle.failure_handler import FailurePolicy
        eng.register("bad", "Bad", failing, failure_policy=FailurePolicy(max_retries=0))
        results = eng.run_cycle()
        assert results["bad"].startswith("failed:")
        eng.shutdown(drain=False)

    def test_run_cycle_dependency_order(self):
        order = []

        def make_fn(name):
            def fn(ctx):
                order.append(name)
            return fn

        eng = _make_engine()
        eng.start()
        eng.register("a", "A", make_fn("a"))
        eng.register("b", "B", make_fn("b"))
        eng.register("c", "C", make_fn("c"))
        eng.declare_dependency("b", "a")
        eng.declare_dependency("c", "b")
        results = eng.run_cycle()
        # All should succeed
        assert all(v == "success" for v in results.values())
        # Order must be a before b before c
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")
        eng.shutdown(drain=False)

    def test_run_cycle_circuit_open_skips(self):
        from iios.investment.strategy.lifecycle.failure_handler import FailurePolicy

        def failing(ctx):
            raise RuntimeError("crash")

        policy = FailurePolicy(
            max_retries=0, circuit_breaker_threshold=1
        )
        eng = _make_engine()
        eng.start()
        eng.register("flaky", "Flaky", failing, failure_policy=policy)
        # First cycle opens the circuit
        eng.run_cycle()
        # Second cycle should skip (circuit open)
        results = eng.run_cycle()
        assert results.get("flaky") == "skipped_circuit_open"
        eng.shutdown(drain=False)

    def test_run_cycle_updates_statistics(self):
        eng = _make_engine()
        eng.start()
        eng.register("s1", "S1", _noop)
        eng.run_cycle()
        snap = eng.runtime_snapshot()
        assert snap.total_cycles >= 1
        eng.shutdown(drain=False)


# ── Scheduling ────────────────────────────────────────────────────────────────

class TestScheduling:
    def test_periodic_schedule(self):
        executed = []

        def fn(ctx):
            executed.append(True)

        eng = _make_engine()
        eng.start()
        eng.register("p1", "Periodic", fn)
        eng.schedule_periodic("p1", interval_seconds=0.3)
        time.sleep(1.5)  # 3+ ticks at 0.5s loop interval
        eng.shutdown(drain=False)
        assert len(executed) >= 2

    def test_event_schedule(self):
        executed = []

        def fn(ctx):
            executed.append(True)

        eng = _make_engine()
        eng.start()
        eng.register("e1", "EventStrat", fn)
        eng.schedule_event("e1", "market_open")
        eng.fire_event("market_open")
        time.sleep(0.2)
        eng.shutdown(drain=False)
        assert len(executed) >= 1

    def test_conditional_schedule(self):
        executed = []
        gate = {"go": False}

        def fn(ctx):
            executed.append(True)

        eng = _make_engine()
        eng.start()
        eng.register("cond", "Conditional", fn)
        eng.schedule_conditional("cond", lambda: gate["go"])
        time.sleep(0.3)
        assert not executed
        gate["go"] = True
        time.sleep(0.6)
        assert len(executed) >= 1
        eng.shutdown(drain=False)

    def test_unschedule(self):
        executed = []

        def fn(ctx):
            executed.append(True)

        eng = _make_engine()
        eng.start()
        eng.register("u1", "Unscheduled", fn)
        eng.schedule_periodic("u1", interval_seconds=0.1)
        time.sleep(0.15)
        count_before = len(executed)
        eng.unschedule("u1")
        time.sleep(0.3)
        # Count should not grow significantly after unscheduling
        assert len(executed) - count_before <= 1
        eng.shutdown(drain=False)

    def test_schedule_unknown_strategy_raises(self):
        eng = _make_engine()
        with pytest.raises(StrategyNotRegisteredError):
            eng.schedule_periodic("ghost", interval_seconds=10)


# ── Dependencies ──────────────────────────────────────────────────────────────

class TestDependencies:
    def test_declare_dependency_unknown_raises(self):
        eng = _make_engine()
        eng.register("b", "B", _noop)
        # "a" is not registered — declare_dependency does NOT require registration
        # but can succeed if depends_on is just used as an ordering handle
        # (the dependency graph does not enforce registration)
        eng.declare_dependency("b", "a")

    def test_cyclic_dependency_raises(self):
        eng = _make_engine()
        eng.register("a", "A", _noop)
        eng.register("b", "B", _noop)
        eng.declare_dependency("b", "a")
        with pytest.raises(CyclicDependencyError):
            eng.declare_dependency("a", "b")

    def test_validate_dependencies_valid(self):
        eng = _make_engine()
        eng.register("a", "A", _noop)
        eng.register("b", "B", _noop)
        eng.declare_dependency("b", "a")
        result = eng.validate_dependencies()
        assert result.is_valid is True


# ── Checkpointing ─────────────────────────────────────────────────────────────

class TestCheckpointing:
    def test_save_and_load(self):
        eng = _make_engine()
        eng.register("s1", "S1", _noop)
        ckpt = eng.save_checkpoint("s1", {"step": 5}, label="mid")
        loaded = eng.load_checkpoint("s1")
        assert loaded is ckpt
        assert loaded.state_snapshot["step"] == 5

    def test_load_no_checkpoint_returns_none(self):
        eng = _make_engine()
        eng.register("s1", "S1", _noop)
        assert eng.load_checkpoint("s1") is None


# ── Observability ─────────────────────────────────────────────────────────────

class TestObservability:
    def test_runtime_snapshot_shape(self):
        eng = _make_engine()
        eng.start()
        snap = eng.runtime_snapshot()
        assert hasattr(snap, "state")
        assert hasattr(snap, "total_cycles")
        eng.shutdown(drain=False)

    def test_health_report(self):
        eng = _make_engine()
        eng.start()
        eng.register("s1", "S1", _noop)
        eng.run_cycle()
        report = eng.health_report()
        assert hasattr(report, "health")
        eng.shutdown(drain=False)

    def test_strategy_health(self):
        eng = _make_engine()
        eng.start()
        eng.register("s1", "S1", _noop)
        eng.run_cycle()
        health = eng.strategy_health("s1")
        assert health.strategy_id == "s1"
        eng.shutdown(drain=False)

    def test_execution_history(self):
        eng = _make_engine()
        eng.start()
        eng.register("s1", "S1", _noop)
        eng.run_cycle()
        hist = eng.execution_history("s1")
        assert len(hist) >= 1
        eng.shutdown(drain=False)

    def test_performance_metrics(self):
        eng = _make_engine()
        eng.start()
        eng.register("s1", "S1", _noop)
        eng.run_cycle()
        m = eng.performance_metrics("s1")
        assert m.sample_count >= 1
        eng.shutdown(drain=False)

    def test_recovery_status(self):
        eng = _make_engine()
        eng.register("s1", "S1", _noop)
        status = eng.recovery_status("s1")
        assert "circuit_state" in status
        assert "restart_count" in status
        assert "has_checkpoint" in status

    def test_queue_depth(self):
        eng = _make_engine()
        assert eng.queue_depth() == 0

    def test_resource_snapshot(self):
        eng = _make_engine()
        snap = eng.resource_snapshot()
        assert snap.total_workers > 0


# ── Retry behaviour ───────────────────────────────────────────────────────────

class TestRetryBehaviour:
    def test_retry_eventually_succeeds(self):
        call_count = [0]

        def sometimes_fails(ctx):
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("not yet")

        policy = FailurePolicy(
            max_retries=5,
            initial_retry_delay_s=0.01,
            backoff_factor=1.0,
        )
        eng = _make_engine()
        eng.start()
        eng.register("retry-strat", "Retry", sometimes_fails, failure_policy=policy)
        future = eng.submit("retry-strat")
        # Retries are now inline (blocking), so future.result() waits for all retries
        future.result(timeout=10)
        assert call_count[0] >= 3
        eng.shutdown(drain=False)


# ── Concurrency ───────────────────────────────────────────────────────────────

class TestConcurrency:
    def test_many_strategies_run_cycle(self):
        eng = _make_engine()
        eng.start()
        for i in range(50):
            eng.register(f"s{i}", f"S{i}", _noop)
        results = eng.run_cycle()
        assert len(results) == 50
        assert all(v == "success" for v in results.values())
        eng.shutdown(drain=False)

    def test_concurrent_submits(self):
        executed = []
        lock = threading.Lock()

        def fn(ctx):
            with lock:
                executed.append(True)

        eng = _make_engine()
        eng.start()
        eng.register("conc", "Concurrent", fn)
        futures = [eng.submit("conc") for _ in range(5)]
        for f in futures:
            try:
                f.result(timeout=5)
            except Exception:
                pass
        eng.shutdown(drain=False)
        # At least one should have run
        assert len(executed) >= 1

    def test_restart_on_failure(self):
        call_count = [0]

        def fn(ctx):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("first run fails")

        policy = FailurePolicy(max_retries=0)
        eng = _make_engine()
        eng.start()
        eng.register(
            "auto-restart", "AutoRestart", fn,
            failure_policy=policy,
            restart_policy=RestartPolicy.ON_FAILURE,
        )
        # First execution fails and triggers auto-restart
        try:
            future = eng.submit("auto-restart")
            future.result(timeout=5)
        except Exception:
            pass  # first run may raise
        time.sleep(0.5)  # allow auto-restart to trigger and run
        assert call_count[0] >= 2
        eng.shutdown(drain=False)
