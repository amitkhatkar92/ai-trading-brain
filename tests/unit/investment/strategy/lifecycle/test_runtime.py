"""tests/unit/investment/strategy/lifecycle/test_runtime.py
Tests for: RuntimeContext, RuntimeState, RuntimeStatistics, RuntimeManager
"""
from __future__ import annotations

import time
import threading
from datetime import datetime, timezone, timedelta

import pytest

from iios.investment.strategy.lifecycle.runtime_context import RuntimeContext
from iios.investment.strategy.lifecycle.runtime_state import (
    RuntimeState,
    RuntimeStateSnapshot,
    validate_runtime_transition,
)
from iios.investment.strategy.lifecycle.runtime_statistics import (
    CycleSample,
    RuntimeStatistics,
)
from iios.investment.strategy.lifecycle.runtime_manager import (
    RuntimeManager,
    RuntimeManagerError,
)


# ── RuntimeContext ─────────────────────────────────────────────────────────────

class TestRuntimeContext:
    def test_default_cycle_id_generated(self):
        ctx = RuntimeContext()
        assert ctx.cycle_id.startswith("cyc-")

    def test_unique_cycle_ids(self):
        ids = {RuntimeContext().cycle_id for _ in range(50)}
        assert len(ids) == 50

    def test_is_paper_default(self):
        ctx = RuntimeContext()
        assert ctx.is_paper is True
        assert ctx.is_live is False
        assert ctx.is_backtest is False

    def test_not_expired_without_deadline(self):
        ctx = RuntimeContext()
        assert ctx.is_expired() is False

    def test_expired_with_past_deadline(self):
        past = datetime.now(timezone.utc) - timedelta(seconds=1)
        ctx = RuntimeContext(deadline=past)
        assert ctx.is_expired() is True

    def test_not_expired_with_future_deadline(self):
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        ctx = RuntimeContext(deadline=future)
        assert ctx.is_expired() is False

    def test_elapsed_ms_positive(self):
        ctx = RuntimeContext()
        time.sleep(0.01)
        assert ctx.elapsed_ms() >= 0

    def test_metadata_get_meta(self):
        ctx = RuntimeContext(metadata={"foo": "bar"})
        assert ctx.get_meta("foo") == "bar"
        assert ctx.get_meta("missing", "default") == "default"

    def test_intelligence_refs_default_none(self):
        ctx = RuntimeContext()
        assert ctx.market_intelligence is None
        assert ctx.company_intelligence is None

    def test_intelligence_refs_settable(self):
        mi = object()
        ci = object()
        ctx = RuntimeContext(market_intelligence=mi, company_intelligence=ci)
        assert ctx.market_intelligence is mi
        assert ctx.company_intelligence is ci


# ── RuntimeState ──────────────────────────────────────────────────────────────

class TestRuntimeState:
    def test_idle_not_accepting(self):
        assert RuntimeState.IDLE.is_accepting() is False

    def test_running_accepting(self):
        assert RuntimeState.RUNNING.is_accepting() is True

    def test_shutdown_terminal(self):
        assert RuntimeState.SHUTDOWN.is_terminal() is True

    def test_idle_not_terminal(self):
        assert RuntimeState.IDLE.is_terminal() is False

    def test_running_can_pause(self):
        assert RuntimeState.RUNNING.can_pause() is True

    def test_paused_can_resume(self):
        assert RuntimeState.PAUSED.can_resume() is True

    def test_running_can_stop(self):
        assert RuntimeState.RUNNING.can_stop() is True

    def test_idle_cannot_stop(self):
        assert RuntimeState.IDLE.can_stop() is False

    def test_valid_transition_idle_to_initializing(self):
        assert validate_runtime_transition(
            RuntimeState.IDLE, RuntimeState.INITIALIZING
        ) is True

    def test_invalid_transition_idle_to_running(self):
        assert validate_runtime_transition(
            RuntimeState.IDLE, RuntimeState.RUNNING
        ) is False

    def test_valid_transition_running_to_paused(self):
        assert validate_runtime_transition(
            RuntimeState.RUNNING, RuntimeState.PAUSED
        ) is True

    def test_valid_transition_paused_to_running(self):
        assert validate_runtime_transition(
            RuntimeState.PAUSED, RuntimeState.RUNNING
        ) is True

    def test_valid_transition_running_to_draining(self):
        assert validate_runtime_transition(
            RuntimeState.RUNNING, RuntimeState.DRAINING
        ) is True

    def test_valid_transition_draining_to_shutdown(self):
        assert validate_runtime_transition(
            RuntimeState.DRAINING, RuntimeState.SHUTDOWN
        ) is True

    def test_shutdown_no_valid_transitions(self):
        for target in RuntimeState:
            if target != RuntimeState.SHUTDOWN:
                assert validate_runtime_transition(
                    RuntimeState.SHUTDOWN, target
                ) is False


class TestRuntimeStateSnapshot:
    def test_success_rate_zero_cycles(self):
        snap = RuntimeStateSnapshot(state=RuntimeState.IDLE, total_cycles=0)
        assert snap.success_rate == 1.0

    def test_success_rate_no_failures(self):
        snap = RuntimeStateSnapshot(
            state=RuntimeState.RUNNING, total_cycles=10, failed_cycles=0
        )
        assert snap.success_rate == 1.0

    def test_success_rate_with_failures(self):
        snap = RuntimeStateSnapshot(
            state=RuntimeState.RUNNING, total_cycles=10, failed_cycles=2
        )
        assert snap.success_rate == pytest.approx(0.8)

    def test_to_dict_contains_keys(self):
        snap = RuntimeStateSnapshot(state=RuntimeState.RUNNING)
        d = snap.to_dict()
        assert "state" in d
        assert "success_rate" in d
        assert "uptime_seconds" in d


# ── RuntimeStatistics ─────────────────────────────────────────────────────────

class TestRuntimeStatistics:
    def _make_sample(self, *, duration_ms=100.0, failures=0):
        return CycleSample(
            cycle_id="cyc-test",
            strategy_count=5,
            duration_ms=duration_ms,
            success_count=5 - failures,
            failure_count=failures,
        )

    def test_initial_state(self):
        stats = RuntimeStatistics()
        assert stats.total_cycles == 0
        assert stats.total_failures == 0
        assert stats.success_rate() == 1.0

    def test_record_increments_counters(self):
        stats = RuntimeStatistics()
        stats.record(self._make_sample())
        assert stats.total_cycles == 1
        assert stats.total_strategies_run == 5

    def test_record_failures(self):
        stats = RuntimeStatistics()
        stats.record(self._make_sample(failures=2))
        assert stats.total_failures == 2

    def test_success_rate(self):
        stats = RuntimeStatistics()
        stats.record(self._make_sample(failures=1))  # 4/5 pass, but cycle counted as 1 with 1 fail
        # success_rate = (total_cycles - total_failures) / total_cycles = (1 - 1) / 1 = 0
        assert stats.success_rate() == 0.0

    def test_latency_percentiles(self):
        stats = RuntimeStatistics()
        for ms in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
            stats.record(self._make_sample(duration_ms=ms))
        assert stats.p50_latency_ms() > 0
        assert stats.p95_latency_ms() >= stats.p50_latency_ms()
        assert stats.p99_latency_ms() >= stats.p95_latency_ms()

    def test_window_limit(self):
        stats = RuntimeStatistics(window=5)
        for i in range(10):
            stats.record(self._make_sample(duration_ms=float(i)))
        assert len(stats.recent_samples()) <= 5

    def test_to_dict(self):
        stats = RuntimeStatistics()
        d = stats.to_dict()
        assert "total_cycles" in d
        assert "success_rate" in d
        assert "p95_latency_ms" in d

    def test_thread_safe_concurrent_records(self):
        stats = RuntimeStatistics(window=1000)
        errors = []

        def worker():
            try:
                for _ in range(50):
                    stats.record(self._make_sample())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert stats.total_cycles == 500


# ── RuntimeManager ────────────────────────────────────────────────────────────

class TestRuntimeManager:
    def test_initial_state_idle(self):
        rm = RuntimeManager()
        assert rm.state == RuntimeState.IDLE

    def test_start_transitions_to_running(self):
        rm = RuntimeManager()
        rm.start()
        assert rm.state == RuntimeState.RUNNING
        assert rm.is_running is True

    def test_pause_transitions_to_paused(self):
        rm = RuntimeManager()
        rm.start()
        rm.pause()
        assert rm.state == RuntimeState.PAUSED
        assert rm.is_paused is True

    def test_resume_transitions_to_running(self):
        rm = RuntimeManager()
        rm.start()
        rm.pause()
        rm.resume()
        assert rm.is_running is True

    def test_stop_transitions_to_shutdown(self):
        rm = RuntimeManager()
        rm.start()
        rm.stop()
        assert rm.state == RuntimeState.SHUTDOWN
        assert rm.is_shutdown is True

    def test_stop_from_paused(self):
        rm = RuntimeManager()
        rm.start()
        rm.pause()
        rm.stop()
        assert rm.is_shutdown is True

    def test_restart(self):
        rm = RuntimeManager()
        rm.start()
        rm.stop()
        rm.restart()
        assert rm.is_running is True

    def test_invalid_transition_raises(self):
        rm = RuntimeManager()
        # Cannot pause from IDLE
        with pytest.raises(RuntimeManagerError):
            rm.pause()

    def test_state_listener_called(self):
        transitions = []
        rm = RuntimeManager()
        rm.add_state_listener(lambda f, t: transitions.append((f, t)))
        rm.start()
        assert (RuntimeState.IDLE, RuntimeState.INITIALIZING) in transitions
        assert (RuntimeState.INITIALIZING, RuntimeState.RUNNING) in transitions

    def test_state_listener_exception_does_not_abort(self):
        def bad_listener(f, t):
            raise ValueError("listener error")

        rm = RuntimeManager()
        rm.add_state_listener(bad_listener)
        rm.start()  # should not raise
        assert rm.is_running

    def test_make_context(self):
        rm = RuntimeManager()
        ctx = rm.make_context(is_live=True)
        assert isinstance(ctx, RuntimeContext)
        assert ctx.is_live is True

    def test_snapshot_uptime(self):
        rm = RuntimeManager()
        rm.start()
        time.sleep(0.05)
        snap = rm.snapshot()
        assert snap.uptime_seconds >= 0

    def test_snapshot_state(self):
        rm = RuntimeManager()
        rm.start()
        snap = rm.snapshot()
        assert snap.state == RuntimeState.RUNNING
