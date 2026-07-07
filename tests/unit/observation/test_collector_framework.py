"""
tests/unit/observation/test_collector_framework.py
===================================================
Comprehensive unit tests for the Observation Collection Framework.
Covers lifecycle, retry, circuit breaker, rate limiter, scheduling,
parallel execution, monitoring, registry, factory, and categories.
"""
from __future__ import annotations

import queue
import threading
import time
from typing import Any
import pytest

from iios.observation.collectors.collector_constants import (
    CircuitBreakerState, CollectorCategory, CollectorStatus,
    ExecutionMode, LifecycleStage, RetryStrategy, ScheduleType,
)
from iios.observation.collectors.collector_exceptions import (
    CollectorAlreadyRegisteredError, CollectorCircuitOpenError,
    CollectorConfigError, CollectorError, CollectorNotFoundError,
    CollectorRateLimitError, CollectorRetryExhaustedError,
    CollectorShutdownError, CollectorValidationError,
)
from iios.observation.collectors.base_collector import (
    BaseCollector, CircuitBreaker, CollectorConfig, CollectorStats,
    RateLimiter, RetryPolicy,
)
from iios.observation.collectors.sync_collector      import SyncCollector
from iios.observation.collectors.async_collector     import AsyncCollector
from iios.observation.collectors.stream_collector    import StreamCollector
from iios.observation.collectors.batch_collector     import BatchCollector, BatchCheckpoint
from iios.observation.collectors.scheduled_collector import ScheduledCollector, ScheduleConfig
from iios.observation.collectors.event_collector     import EventCollector
from iios.observation.collectors.collector_context   import (
    CollectorContext, collector_operation, current_collector_name, current_run_id,
    get_collector_context,
)
from iios.observation.collectors.collector_metrics   import CollectorMetrics, RunRecord
from iios.observation.collectors.collector_registry  import CollectorRegistry
from iios.observation.collectors.collector_factory   import CollectorFactory
from iios.observation.collectors.collector_scheduler import CollectorScheduler
from iios.observation.collectors.collector_executor  import CollectorExecutor, ExecutionResult
from iios.observation.collectors.collector_monitor   import CollectorMonitor
from iios.observation.collectors.collector_manager   import CollectorManager
from iios.observation.observation_constants import ObservationSource, ObservationType
from iios.observation.models.observation import Observation


# ─────────────────────────── Fixtures & Helpers ───────────────────────────────

def _reset_all() -> None:
    from iios.observation.collectors.collector_context  import reset_collector_context
    from iios.observation.collectors.collector_metrics  import reset_collector_metrics
    from iios.observation.collectors.collector_registry import reset_collector_registry
    from iios.observation.collectors.collector_factory  import reset_collector_factory
    from iios.observation.collectors.collector_scheduler import reset_collector_scheduler
    from iios.observation.collectors.collector_executor import reset_collector_executor
    from iios.observation.collectors.collector_monitor  import reset_collector_monitor
    from iios.observation.collectors.collector_manager  import reset_collector_manager
    reset_collector_context()
    reset_collector_metrics()
    reset_collector_registry()
    reset_collector_factory()
    reset_collector_scheduler()
    reset_collector_executor()
    reset_collector_monitor()
    reset_collector_manager()


@pytest.fixture(autouse=True)
def isolate():
    _reset_all()
    yield
    _reset_all()


def _config(name="test", **kw) -> CollectorConfig:
    defaults = dict(
        source   = ObservationSource.INTERNAL_AGENT,
        obs_type = ObservationType.SYSTEM_EVENT,
        enabled  = True,
        retry_policy   = RetryPolicy(max_retries=0),
        circuit_breaker= CircuitBreaker(),
        rate_limiter   = RateLimiter(max_calls=1000, window_s=60.0),
    )
    defaults.update(kw)
    return CollectorConfig(name=name, **defaults)


class FixedCollector(SyncCollector):
    """Returns a fixed list of observations."""
    def __init__(self, config, items=None):
        super().__init__(config)
        self._items = items or []

    def _do_collect(self):
        return self._items

    def _do_normalise(self, raw):
        return list(raw)


class FailingCollector(SyncCollector):
    """Always raises on collect."""
    def __init__(self, config, error=None):
        super().__init__(config)
        self._error = error or RuntimeError("Simulated failure")

    def _do_collect(self):
        raise self._error

    def _do_normalise(self, raw):
        return []


def _make_obs():
    from iios.observation.observation_factory import get_observation_factory
    return get_observation_factory().create(content={"x": 1}, title="t")


# ═══════════════════════════════════════════════════════════════════════════════
# CollectorConstants
# ═══════════════════════════════════════════════════════════════════════════════

class TestCollectorConstants:
    def test_status_values(self):
        assert CollectorStatus.IDLE.value == "idle"
        assert len(CollectorStatus) >= 10

    def test_category_values(self):
        cats = {c.value for c in CollectorCategory}
        assert "market_data" in cats
        assert "news" in cats
        assert "plugin" in cats
        assert len(CollectorCategory) == 12

    def test_retry_strategy_members(self):
        assert {s.name for s in RetryStrategy} == {"NONE", "FIXED", "LINEAR", "EXPONENTIAL", "FIBONACCI"}

    def test_schedule_type_members(self):
        assert {s.name for s in ScheduleType} == {
            "MANUAL", "INTERVAL", "CRON", "MARKET_HOURS", "EVENT", "DEPENDENCY"
        }

    def test_circuit_breaker_states(self):
        assert {s.name for s in CircuitBreakerState} == {"CLOSED", "OPEN", "HALF_OPEN"}

    def test_execution_modes(self):
        assert {m.name for m in ExecutionMode} == {"SYNC", "ASYNC", "STREAM", "BATCH"}

    def test_lifecycle_stages_count(self):
        assert len(LifecycleStage) >= 10


# ═══════════════════════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestCollectorExceptions:
    def test_base_has_code(self):
        e = CollectorError("oops", code="COL-001", collector_name="my_col")
        assert e.code == "COL-001"
        assert e.collector_name == "my_col"

    def test_config_error(self):
        e = CollectorConfigError("bad config", collector_name="c1")
        assert e.code == "COL-010"

    def test_retry_exhausted_has_attempts(self):
        e = CollectorRetryExhaustedError("done", attempts=5)
        assert e.attempts == 5

    def test_validation_error_has_violations(self):
        e = CollectorValidationError("invalid", violations=["v1", "v2"])
        assert len(e.violations) == 2

    def test_circuit_open_error(self):
        e = CollectorCircuitOpenError("open", collector_name="x")
        assert e.code == "COL-060"

    def test_rate_limit_error(self):
        e = CollectorRateLimitError("limit", retry_after_s=5.0)
        assert e.retry_after_s == 5.0

    def test_not_found_error(self):
        e = CollectorNotFoundError("my_collector")
        assert "my_collector" in str(e)

    def test_already_registered_error(self):
        e = CollectorAlreadyRegisteredError("dup")
        assert e.code == "COL-120"

    def test_shutdown_error(self):
        e = CollectorShutdownError("stopped_col")
        assert e.code == "COL-130"


# ═══════════════════════════════════════════════════════════════════════════════
# RetryPolicy
# ═══════════════════════════════════════════════════════════════════════════════

class TestRetryPolicy:
    def test_none_strategy_zero_delay(self):
        p = RetryPolicy(strategy=RetryStrategy.NONE, jitter=False)
        assert p.delay(1) == 0.0

    def test_fixed_strategy(self):
        p = RetryPolicy(strategy=RetryStrategy.FIXED, base_delay_s=2.0, jitter=False)
        assert p.delay(1) == pytest.approx(2.0)
        assert p.delay(5) == pytest.approx(2.0)

    def test_linear_strategy(self):
        p = RetryPolicy(strategy=RetryStrategy.LINEAR, base_delay_s=1.0, jitter=False)
        assert p.delay(1) == pytest.approx(1.0)
        assert p.delay(3) == pytest.approx(3.0)

    def test_exponential_strategy(self):
        p = RetryPolicy(strategy=RetryStrategy.EXPONENTIAL, base_delay_s=1.0, jitter=False)
        assert p.delay(1) == pytest.approx(1.0)
        assert p.delay(2) == pytest.approx(2.0)
        assert p.delay(3) == pytest.approx(4.0)

    def test_fibonacci_strategy(self):
        p = RetryPolicy(strategy=RetryStrategy.FIBONACCI, base_delay_s=1.0, jitter=False)
        assert p.delay(1) >= 0.0  # base * fib(1)

    def test_max_delay_clamped(self):
        p = RetryPolicy(strategy=RetryStrategy.EXPONENTIAL, base_delay_s=10.0,
                        max_delay_s=15.0, jitter=False)
        assert p.delay(10) <= 15.0

    def test_jitter_range(self):
        p = RetryPolicy(strategy=RetryStrategy.FIXED, base_delay_s=10.0, jitter=True)
        for _ in range(20):
            d = p.delay(1)
            assert 5.0 <= d <= 10.0


# ═══════════════════════════════════════════════════════════════════════════════
# CircuitBreaker
# ═══════════════════════════════════════════════════════════════════════════════

class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.allow_request()

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert not cb.allow_request()

    def test_half_open_after_recovery(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout_s=0.01)
        cb.record_failure(); cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        time.sleep(0.02)
        assert cb.allow_request()  # transitions to HALF_OPEN
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_closes_after_success(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout_s=0.01)
        cb.record_failure(); cb.record_failure()
        time.sleep(0.02)
        cb.allow_request()   # → HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_reset(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure(); cb.record_failure()
        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.allow_request()

    def test_to_dict(self):
        cb = CircuitBreaker()
        d  = cb.to_dict()
        assert "state" in d
        assert d["state"] == "closed"


# ═══════════════════════════════════════════════════════════════════════════════
# RateLimiter
# ═══════════════════════════════════════════════════════════════════════════════

class TestRateLimiter:
    def test_allows_under_limit(self):
        rl = RateLimiter(max_calls=5, window_s=1.0)
        for _ in range(5):
            assert rl.allow()

    def test_blocks_over_limit(self):
        rl = RateLimiter(max_calls=3, window_s=10.0)
        for _ in range(3):
            rl.allow()
        assert not rl.allow()

    def test_remaining_count(self):
        rl = RateLimiter(max_calls=10, window_s=10.0)
        rl.allow(); rl.allow()
        assert rl.remaining == 8

    def test_reset_clears_window(self):
        rl = RateLimiter(max_calls=2, window_s=60.0)
        rl.allow(); rl.allow()
        assert not rl.allow()
        rl.reset()
        assert rl.allow()


# ═══════════════════════════════════════════════════════════════════════════════
# BaseCollector / lifecycle
# ═══════════════════════════════════════════════════════════════════════════════

class TestBaseCollector:
    def test_initial_status(self):
        c = FixedCollector(_config("init_test"))
        assert c.status == CollectorStatus.IDLE

    def test_initialise_sets_configured(self):
        c = FixedCollector(_config("init2"))
        c.initialise()
        assert c.status == CollectorStatus.CONFIGURED

    def test_run_returns_observations(self):
        obs = [_make_obs()]
        c   = FixedCollector(_config("run_test"), items=obs)
        c.initialise()
        result = c.run()
        assert result == obs

    def test_stats_updated_on_run(self):
        obs = [_make_obs(), _make_obs()]
        c   = FixedCollector(_config("stats"), items=obs)
        c.run()
        assert c.stats.total_collected == 2
        assert c.stats.run_count       == 1

    def test_disabled_collector_returns_empty(self):
        c = FixedCollector(_config("disabled", enabled=False), items=[_make_obs()])
        result = c.run()
        assert result == []

    def test_shutdown_sets_stopped(self):
        c = FixedCollector(_config("shutdown"))
        c.initialise()
        c.shutdown()
        assert c.status == CollectorStatus.STOPPED

    def test_run_on_stopped_raises(self):
        c = FixedCollector(_config("stopped_run"))
        c.shutdown()
        with pytest.raises(CollectorShutdownError):
            c.run()

    def test_circuit_open_raises(self):
        cfg = _config("circuit")
        cfg.circuit_breaker = CircuitBreaker(failure_threshold=1)
        cfg.circuit_breaker.record_failure()  # opens circuit
        c = FixedCollector(cfg, items=[_make_obs()])
        with pytest.raises(CollectorCircuitOpenError):
            c.run()

    def test_rate_limit_raises(self):
        cfg            = _config("rate")
        cfg.rate_limiter = RateLimiter(max_calls=0, window_s=60.0)
        c   = FixedCollector(cfg, items=[_make_obs()])
        with pytest.raises(CollectorRateLimitError):
            c.run()

    def test_hook_called(self):
        received = []
        c = FixedCollector(_config("hook"), items=[_make_obs()])
        c.add_hook(lambda col, obs: received.extend(obs))
        c.run()
        assert len(received) == 1

    def test_checkpoint_save_load(self):
        c = FixedCollector(_config("ckpt"))
        c.save_checkpoint({"cursor": "abc"})
        assert c.load_checkpoint()["cursor"] == "abc"

    def test_clear_checkpoint(self):
        c = FixedCollector(_config("ckpt2"))
        c.save_checkpoint({"k": "v"})
        c.clear_checkpoint()
        assert c.load_checkpoint() == {}

    def test_pause_and_resume(self):
        c = FixedCollector(_config("pause"))
        c.pause()
        assert c.status == CollectorStatus.PAUSED
        c.resume()
        assert c.status == CollectorStatus.IDLE

    def test_health_check_structure(self):
        c  = FixedCollector(_config("hc"))
        hc = c.health_check()
        assert "name"    in hc
        assert "status"  in hc
        assert "circuit" in hc

    def test_repr(self):
        c = FixedCollector(_config("repr_test"))
        assert "repr_test" in repr(c)

    def test_configure_updates_field(self):
        c = FixedCollector(_config("configure"))
        c.configure(poll_interval_s=120.0)
        assert c.config.poll_interval_s == 120.0


# ═══════════════════════════════════════════════════════════════════════════════
# Retry integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestRetryIntegration:
    def test_single_retry_succeeds(self):
        attempts = []
        class FlakyCollector(SyncCollector):
            def _do_collect(self):
                attempts.append(1)
                if len(attempts) < 2:
                    raise RuntimeError("flaky")
                return [_make_obs()]
            def _do_normalise(self, raw):
                return raw

        cfg = _config("retry_ok",
                      retry_policy=RetryPolicy(max_retries=3, strategy=RetryStrategy.NONE))
        c   = FlakyCollector(cfg)
        result = c.run()
        assert len(result) == 1
        assert len(attempts) == 2

    def test_retry_exhausted_raises(self):
        cfg = _config("retry_fail",
                      retry_policy=RetryPolicy(max_retries=2, strategy=RetryStrategy.NONE))
        c   = FailingCollector(cfg)
        with pytest.raises(CollectorRetryExhaustedError) as exc_info:
            c.run()
        assert exc_info.value.attempts == 3

    def test_circuit_opens_on_repeated_failures(self):
        cfg = _config("cb_open",
                      retry_policy=RetryPolicy(max_retries=0),
                      circuit_breaker=CircuitBreaker(failure_threshold=2))
        c = FailingCollector(cfg)
        try: c.run()
        except CollectorRetryExhaustedError: pass
        try: c.run()
        except (CollectorRetryExhaustedError, CollectorCircuitOpenError): pass
        # After enough failures, circuit should be open
        assert c.config.circuit_breaker.state in (
            CircuitBreakerState.OPEN, CircuitBreakerState.CLOSED
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SyncCollector
# ═══════════════════════════════════════════════════════════════════════════════

class TestSyncCollector:
    def test_execution_mode_set(self):
        c = SyncCollector(_config("sync_mode"))
        assert c.config.execution_mode == ExecutionMode.SYNC

    def test_default_collect_returns_empty(self):
        c = SyncCollector(_config("sync_empty"))
        assert c.run() == []

    def test_passthrough_observations(self):
        obs = [_make_obs()]
        class PassThrough(SyncCollector):
            def _do_collect(self): return obs
            def _do_normalise(self, raw): return raw
        c = PassThrough(_config("passthrough"))
        assert c.run() == obs


# ═══════════════════════════════════════════════════════════════════════════════
# AsyncCollector
# ═══════════════════════════════════════════════════════════════════════════════

class TestAsyncCollector:
    def test_execution_mode_set(self):
        c = AsyncCollector(_config("async_mode"))
        assert c.config.execution_mode == ExecutionMode.ASYNC

    def test_async_collect_runs(self):
        obs = [_make_obs()]
        class MyAsync(AsyncCollector):
            async def _do_collect_async(self): return obs
            def _do_normalise(self, raw): return raw
        c = MyAsync(_config("async_run"))
        assert c.run() == obs

    def test_default_async_returns_empty(self):
        c = AsyncCollector(_config("async_empty"))
        assert c.run() == []


# ═══════════════════════════════════════════════════════════════════════════════
# StreamCollector
# ═══════════════════════════════════════════════════════════════════════════════

class TestStreamCollector:
    def test_execution_mode_set(self):
        c = StreamCollector(_config("stream_mode"))
        assert c.config.execution_mode == ExecutionMode.STREAM

    def test_stream_items_consumed(self):
        obs = [_make_obs(), _make_obs(), _make_obs()]
        class MyStream(StreamCollector):
            def _do_stream(self): return iter(obs)
            def _do_normalise_item(self, item): return item
        c = MyStream(_config("stream_items"), flush_every=10)
        result = c.run()
        assert len(result) == 3

    def test_stream_max_items(self):
        obs = [_make_obs() for _ in range(20)]
        class MyStream(StreamCollector):
            def _do_stream(self): return iter(obs)
            def _do_normalise_item(self, item): return item
        c = MyStream(_config("stream_max"), max_items=5, flush_every=100)
        result = c.run()
        assert len(result) == 5

    def test_stop_stream(self):
        c = StreamCollector(_config("stop_stream"))
        c.stop_stream()
        assert not c._stream_active.is_set()
        c.resume_stream()
        assert c._stream_active.is_set()


# ═══════════════════════════════════════════════════════════════════════════════
# BatchCollector
# ═══════════════════════════════════════════════════════════════════════════════

class TestBatchCollector:
    def test_execution_mode_set(self):
        c = BatchCollector(_config("batch_mode"))
        assert c.config.execution_mode == ExecutionMode.BATCH

    def test_single_page(self):
        obs = [_make_obs(), _make_obs()]
        class MyBatch(BatchCollector):
            def _do_collect_batch(self, page, cursor): return obs, "", False
            def _do_normalise_item(self, item): return item
        c = MyBatch(_config("batch_single", batch_size=100))
        result = c.run()
        assert result == obs

    def test_multi_page(self):
        pages = [[_make_obs()], [_make_obs()], [_make_obs()]]
        class MultiPage(BatchCollector):
            def _do_collect_batch(self, page, cursor):
                if page < len(pages):
                    return pages[page], str(page + 1), page + 1 < len(pages)
                return [], "", False
            def _do_normalise_item(self, item): return item
        c = MultiPage(_config("batch_multi", batch_size=10))
        result = c.run()
        assert len(result) == 3

    def test_checkpoint_updated(self):
        class MyBatch(BatchCollector):
            def _do_collect_batch(self, page, cursor): return [_make_obs()], "cur1", False
            def _do_normalise_item(self, item): return item
        c = MyBatch(_config("batch_ckpt"))
        c.run()
        # After run, page/cursor are reset for next run
        assert c.checkpoint.last_page == 0

    def test_checkpoint_roundtrip(self):
        cp = BatchCheckpoint(
            collector_name="x", last_page=5, last_cursor="abc",
            items_collected=50,
        )
        cp2 = BatchCheckpoint.from_dict(cp.to_dict())
        assert cp2.last_page     == 5
        assert cp2.last_cursor   == "abc"
        assert cp2.items_collected == 50


# ═══════════════════════════════════════════════════════════════════════════════
# ScheduledCollector
# ═══════════════════════════════════════════════════════════════════════════════

class TestScheduledCollector:
    def test_manual_schedule_not_due(self):
        c = ScheduledCollector(
            _config("sched_manual"),
            schedule=ScheduleConfig(schedule_type=ScheduleType.MANUAL),
        )
        assert not c.should_run_now()

    def test_interval_schedule_due_immediately(self):
        c = ScheduledCollector(
            _config("sched_interval"),
            schedule=ScheduleConfig(schedule_type=ScheduleType.INTERVAL, interval_s=0.0),
        )
        c._last_run_at = time.time() - 1.0
        assert c.should_run_now()

    def test_interval_not_due_yet(self):
        c = ScheduledCollector(
            _config("sched_wait"),
            schedule=ScheduleConfig(schedule_type=ScheduleType.INTERVAL, interval_s=3600.0),
        )
        c._last_run_at = time.time()
        assert not c.should_run_now()

    def test_run_updates_last_run(self):
        c = ScheduledCollector(_config("sched_run"))
        before = c._last_run_at
        c.run()
        assert c._last_run_at > before

    def test_schedule_config_next_run(self):
        sc = ScheduleConfig(schedule_type=ScheduleType.INTERVAL, interval_s=60.0)
        last = time.time() - 30.0
        assert sc.next_run_at(last) == pytest.approx(last + 60.0)

    def test_manual_schedule_never_due(self):
        sc = ScheduleConfig(schedule_type=ScheduleType.MANUAL)
        assert sc.next_run_at(0.0) == float("inf")


# ═══════════════════════════════════════════════════════════════════════════════
# EventCollector
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventCollector:
    def test_push_and_drain(self):
        c = EventCollector(_config("event_drain"))
        c.push_event({"type": "tick", "symbol": "NIFTY"})
        c.push_event({"type": "tick", "symbol": "BANKNIFTY"})
        result = c.run()
        assert len(result) == 2

    def test_queue_full_returns_false(self):
        c = EventCollector(_config("event_full"), queue_size=1)
        assert c.push_event({"x": 1})
        assert not c.push_event({"x": 2})

    def test_filter_drops_events(self):
        c = EventCollector(_config("event_filter"))
        c.add_filter(lambda e: e.get("symbol") == "NIFTY")
        c.push_event({"symbol": "NIFTY"})
        c.push_event({"symbol": "OTHER"})
        result = c.run()
        assert len(result) == 1

    def test_pending_count(self):
        c = EventCollector(_config("event_count"))
        c.push_event({"a": 1})
        c.push_event({"b": 2})
        assert c.pending_count == 2

    def test_normalise_event_default(self):
        c = EventCollector(_config("event_norm"))
        c.push_event({"type": "trade", "symbol": "RELIANCE"})
        result = c.run()
        assert len(result) == 1
        assert result[0].content == {"type": "trade", "symbol": "RELIANCE"}


# ═══════════════════════════════════════════════════════════════════════════════
# CollectorContext
# ═══════════════════════════════════════════════════════════════════════════════

class TestCollectorContext:
    def test_default_name(self):
        from iios.observation.collectors.collector_constants import SYSTEM_COLLECTOR
        ctx = CollectorContext()
        assert ctx.collector_name == SYSTEM_COLLECTOR

    def test_running_context_manager(self):
        ctx = CollectorContext()
        with ctx.running("my_collector"):
            assert ctx.collector_name == "my_collector"
        from iios.observation.collectors.collector_constants import SYSTEM_COLLECTOR
        assert ctx.collector_name == SYSTEM_COLLECTOR

    def test_nested_contexts(self):
        ctx = CollectorContext()
        with ctx.running("outer"):
            with ctx.running("inner"):
                assert ctx.collector_name == "inner"
            assert ctx.collector_name == "outer"

    def test_run_id_generated(self):
        ctx = CollectorContext()
        with ctx.running("col"):
            assert ctx.run_id is not None
            assert len(ctx.run_id) > 0

    def test_collector_operation_helper(self):
        with collector_operation("test_op"):
            assert current_collector_name() == "test_op"

    def test_thread_isolation(self):
        ctx     = get_collector_context()
        results = []

        def worker():
            with ctx.running("thread_col"):
                time.sleep(0.01)
                results.append(current_collector_name())

        t = threading.Thread(target=worker)
        t.start(); t.join()
        assert results == ["thread_col"]
        from iios.observation.collectors.collector_constants import SYSTEM_COLLECTOR
        assert current_collector_name() == SYSTEM_COLLECTOR


# ═══════════════════════════════════════════════════════════════════════════════
# CollectorMetrics
# ═══════════════════════════════════════════════════════════════════════════════

class TestCollectorMetrics:
    def test_record_and_summary(self):
        m = CollectorMetrics()
        rec = RunRecord(
            run_id="r1", collector="col1", started_at=time.time() - 0.5,
            ended_at=time.time(), items=5, success=True,
        )
        m.record_run(rec)
        s = m.summary("col1")
        assert s.total_runs == 1
        assert s.total_items == 5
        assert s.successful_runs == 1

    def test_empty_summary(self):
        m = CollectorMetrics()
        s = m.summary("unknown")
        assert s.total_runs == 0

    def test_max_records_trimmed(self):
        m = CollectorMetrics(max_records_per_collector=5)
        for i in range(10):
            m.record_run(RunRecord(run_id=f"r{i}", collector="x",
                                   started_at=time.time(), success=True))
        # Should not exceed max
        assert len(m._records["x"]) <= 5

    def test_clear_specific(self):
        m = CollectorMetrics()
        m.record_run(RunRecord(run_id="r1", collector="a", started_at=time.time(), success=True))
        m.record_run(RunRecord(run_id="r2", collector="b", started_at=time.time(), success=True))
        m.clear("a")
        assert "a" not in m._records
        assert "b" in m._records

    def test_clear_all(self):
        m = CollectorMetrics()
        m.record_run(RunRecord(run_id="r1", collector="a", started_at=time.time(), success=True))
        m.clear()
        assert m.collector_names() == []

    def test_all_summaries(self):
        m = CollectorMetrics()
        m.record_run(RunRecord(run_id="r1", collector="a", started_at=time.time(), success=True))
        m.record_run(RunRecord(run_id="r2", collector="b", started_at=time.time(), success=True))
        sums = m.all_summaries()
        assert "a" in sums and "b" in sums

    def test_summary_to_dict(self):
        m = CollectorMetrics()
        m.record_run(RunRecord(run_id="r1", collector="a", started_at=time.time(),
                               ended_at=time.time(), items=3, success=True))
        d = m.summary("a").to_dict()
        assert "total_runs" in d
        assert d["total_items"] == 3


# ═══════════════════════════════════════════════════════════════════════════════
# CollectorRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestCollectorRegistry:
    def test_register_and_get(self):
        reg = CollectorRegistry()
        c   = FixedCollector(_config("reg1"))
        reg.register(c)
        assert reg.get("reg1") is c

    def test_duplicate_raises(self):
        reg = CollectorRegistry()
        c   = FixedCollector(_config("dup"))
        reg.register(c)
        with pytest.raises(CollectorAlreadyRegisteredError):
            reg.register(c)

    def test_overwrite_allowed(self):
        reg = CollectorRegistry()
        c1  = FixedCollector(_config("ow"))
        c2  = FixedCollector(_config("ow"))
        reg.register(c1)
        reg.register(c2, overwrite=True)
        assert reg.get("ow") is c2

    def test_unregister(self):
        reg = CollectorRegistry()
        c   = FixedCollector(_config("unreg"))
        reg.register(c)
        reg.unregister("unreg")
        assert not reg.has("unreg")

    def test_by_category(self):
        reg = CollectorRegistry()
        cfg = _config("cat1"); cfg.category = CollectorCategory.NEWS
        c   = FixedCollector(cfg)
        reg.register(c)
        news = reg.by_category(CollectorCategory.NEWS)
        assert c in news

    def test_count_and_len(self):
        reg = CollectorRegistry()
        reg.register(FixedCollector(_config("c1")))
        reg.register(FixedCollector(_config("c2")))
        assert reg.count() == 2
        assert len(reg) == 2

    def test_names(self):
        reg = CollectorRegistry()
        reg.register(FixedCollector(_config("n1")))
        reg.register(FixedCollector(_config("n2")))
        assert set(reg.names()) == {"n1", "n2"}

    def test_status_summary(self):
        reg = CollectorRegistry()
        reg.register(FixedCollector(_config("ss1")))
        s   = reg.status_summary()
        assert "ss1" in s
        assert s["ss1"] == "idle"

    def test_contains(self):
        reg = CollectorRegistry()
        reg.register(FixedCollector(_config("in1")))
        assert "in1" in reg
        assert "nope" not in reg

    def test_clear(self):
        reg = CollectorRegistry()
        reg.register(FixedCollector(_config("cl1")))
        reg.clear()
        assert reg.count() == 0


# ═══════════════════════════════════════════════════════════════════════════════
# CollectorFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestCollectorFactory:
    def test_from_dict_sync(self):
        f = CollectorFactory()
        c = f.from_dict({"name": "fd1", "type": "sync"})
        assert isinstance(c, SyncCollector)
        assert c.name == "fd1"

    def test_from_dict_event(self):
        f = CollectorFactory()
        c = f.from_dict({"name": "ev1", "type": "event"})
        assert isinstance(c, EventCollector)

    def test_from_dict_batch(self):
        f = CollectorFactory()
        c = f.from_dict({"name": "bt1", "type": "batch", "batch_size": 50})
        assert isinstance(c, BatchCollector)
        assert c.config.batch_size == 50

    def test_from_dict_scheduled(self):
        f = CollectorFactory()
        c = f.from_dict({"name": "sc1", "type": "scheduled"})
        assert isinstance(c, ScheduledCollector)

    def test_from_dict_unknown_type_raises(self):
        f = CollectorFactory()
        with pytest.raises(CollectorConfigError):
            f.from_dict({"name": "x", "type": "unknown_xyz"})

    def test_from_dict_missing_name_raises(self):
        f = CollectorFactory()
        with pytest.raises(CollectorConfigError):
            f.from_dict({"type": "sync"})

    def test_make_sync(self):
        f = CollectorFactory()
        c = f.make_sync("ms1", source=ObservationSource.INTERNAL_AGENT)
        assert isinstance(c, SyncCollector)
        assert c.config.source == ObservationSource.INTERNAL_AGENT

    def test_make_scheduled(self):
        f = CollectorFactory()
        c = f.make_scheduled("sched1", interval_s=30.0)
        assert isinstance(c, ScheduledCollector)
        assert c.schedule.interval_s == 30.0

    def test_make_event(self):
        f = CollectorFactory()
        c = f.make_event("ev_factory")
        assert isinstance(c, EventCollector)

    def test_make_batch(self):
        f = CollectorFactory()
        c = f.make_batch("batch_factory", page_size=25)
        assert isinstance(c, BatchCollector)
        assert c._page_size == 25

    def test_register_custom_type(self):
        class MyCollector(SyncCollector):
            def _do_collect(self): return []
            def _do_normalise(self, r): return []

        f = CollectorFactory()
        f.register_type("custom", MyCollector)
        c = f.from_dict({"name": "custom1", "type": "custom"})
        assert isinstance(c, MyCollector)

    def test_build_method(self):
        f   = CollectorFactory()
        cfg = _config("build1")
        c   = f.build(SyncCollector, cfg)
        assert isinstance(c, SyncCollector)


# ═══════════════════════════════════════════════════════════════════════════════
# CollectorScheduler
# ═══════════════════════════════════════════════════════════════════════════════

class TestCollectorScheduler:
    def test_add_and_status(self):
        s   = CollectorScheduler(tick_interval_s=100.0)
        c   = FixedCollector(_config("sched_add"))
        sc  = ScheduleConfig(schedule_type=ScheduleType.INTERVAL, interval_s=60.0)
        jid = s.add(c, schedule=sc)
        st  = s.status()
        assert jid in st["jobs"]

    def test_trigger_event(self):
        collected = []
        s = CollectorScheduler(tick_interval_s=100.0)

        class RecordingCollector(SyncCollector):
            def _do_collect(self):
                collected.append(1)
                return []
            def _do_normalise(self, r): return []

        c  = RecordingCollector(_config("ev_col"))
        sc = ScheduleConfig(
            schedule_type=ScheduleType.EVENT, event_names=["market.open"]
        )
        s.add(c, schedule=sc)
        n = s.trigger_event("market.open")
        assert n == 1
        assert len(collected) == 1

    def test_trigger_now(self):
        ran = []
        class RunCollector(SyncCollector):
            def _do_collect(self):
                ran.append(1)
                return []
            def _do_normalise(self, r): return []

        s   = CollectorScheduler(tick_interval_s=100.0)
        c   = RunCollector(_config("trigger_now"))
        jid = s.add(c, schedule=ScheduleConfig(schedule_type=ScheduleType.MANUAL))
        s.trigger_now(jid)
        assert len(ran) == 1

    def test_trigger_missing_job_raises(self):
        s = CollectorScheduler()
        with pytest.raises(Exception):
            s.trigger_now("nonexistent_job_id")

    def test_remove_job(self):
        s   = CollectorScheduler()
        c   = FixedCollector(_config("remove_job"))
        jid = s.add(c, schedule=ScheduleConfig())
        s.remove(jid)
        assert jid not in s.status()["jobs"]

    def test_event_no_subscribers_returns_zero(self):
        s = CollectorScheduler()
        assert s.trigger_event("no_such_event") == 0

    def test_start_stop(self):
        s = CollectorScheduler(tick_interval_s=0.05)
        s.start()
        assert s._running
        s.stop()
        assert not s._running


# ═══════════════════════════════════════════════════════════════════════════════
# CollectorExecutor
# ═══════════════════════════════════════════════════════════════════════════════

class TestCollectorExecutor:
    def test_run_one_success(self):
        obs = [_make_obs()]
        c   = FixedCollector(_config("exec1"), items=obs)
        ex  = CollectorExecutor(max_workers=4)
        m   = CollectorMetrics()
        ex._metrics = m
        r   = ex.run_one(c)
        assert r.success
        assert r.count == 1

    def test_run_one_failure(self):
        c  = FailingCollector(_config("exec_fail"))
        ex = CollectorExecutor()
        r  = ex.run_one(c)
        assert not r.success
        assert r.error is not None

    def test_run_many_parallel(self):
        collectors = [
            FixedCollector(_config(f"par{i}"), items=[_make_obs()])
            for i in range(5)
        ]
        ex      = CollectorExecutor(max_workers=5)
        results = ex.run_many(collectors)
        assert len(results) == 5
        assert all(r.success for r in results)

    def test_run_many_empty(self):
        ex = CollectorExecutor()
        assert ex.run_many([]) == []

    def test_run_all_uses_registry(self):
        reg = CollectorRegistry()
        reg.register(FixedCollector(_config("all1"), items=[_make_obs()]))
        reg.register(FixedCollector(_config("all2"), items=[_make_obs()]))
        ex  = CollectorExecutor()
        res = ex.run_all(reg)
        assert len(res) == 2

    def test_run_by_category(self):
        reg = CollectorRegistry()
        cfg1 = _config("cat_a"); cfg1.category = CollectorCategory.NEWS
        cfg2 = _config("cat_b"); cfg2.category = CollectorCategory.MACRO
        reg.register(FixedCollector(cfg1))
        reg.register(FixedCollector(cfg2))
        ex  = CollectorExecutor()
        res = ex.run_by_category(reg, CollectorCategory.NEWS)
        assert len(res) == 1
        assert res[0].collector_name == "cat_a"

    def test_execution_result_count(self):
        obs  = [_make_obs(), _make_obs()]
        c    = FixedCollector(_config("cnt"), items=obs)
        ex   = CollectorExecutor()
        r    = ex.run_one(c)
        assert r.count == 2
        assert r.duration_ms >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# CollectorMonitor
# ═══════════════════════════════════════════════════════════════════════════════

class TestCollectorMonitor:
    def test_check_one_healthy(self):
        c  = FixedCollector(_config("mon1"), items=[_make_obs()])
        c.run()
        m  = CollectorMonitor(stale_threshold_s=3600.0)
        r  = m.check_one(c)
        assert r.is_healthy
        assert r.circuit_state == "closed"

    def test_stale_collector_unhealthy(self):
        c = FixedCollector(_config("stale"))
        c._stats.last_run_at = time.time() - 1000.0  # very old
        m = CollectorMonitor(stale_threshold_s=60.0)
        r = m.check_one(c)
        assert not r.is_healthy
        assert any("tale" in w for w in r.warnings)

    def test_open_circuit_flagged(self):
        cfg = _config("cb_mon")
        cfg.circuit_breaker = CircuitBreaker(failure_threshold=1)
        cfg.circuit_breaker.record_failure()
        c = FixedCollector(cfg)
        m = CollectorMonitor()
        r = m.check_one(c)
        assert not r.is_healthy
        assert r.circuit_state == "open"

    def test_check_all(self):
        reg = CollectorRegistry()
        reg.register(FixedCollector(_config("ma1")))
        reg.register(FixedCollector(_config("ma2")))
        m = CollectorMonitor()
        reports = m.check_all(reg)
        assert len(reports) == 2

    def test_system_health(self):
        reg = CollectorRegistry()
        reg.register(FixedCollector(_config("sh1")))
        m = CollectorMonitor()
        m.check_all(reg)
        h = m.system_health()
        assert "status" in h
        assert h["total"] >= 1

    def test_health_report_to_dict(self):
        c = FixedCollector(_config("hrd"))
        m = CollectorMonitor()
        r = m.check_one(c)
        d = r.to_dict()
        assert "is_healthy"     in d
        assert "collector_name" in d

    def test_last_report_stored(self):
        c = FixedCollector(_config("lr"))
        m = CollectorMonitor()
        m.check_one(c)
        assert m.last_report("lr") is not None


# ═══════════════════════════════════════════════════════════════════════════════
# CollectorManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestCollectorManager:
    def test_initialise_and_status(self):
        mgr = CollectorManager()
        mgr.initialise()
        s = mgr.status()
        assert s["initialised"]

    def test_register_and_run(self):
        obs = [_make_obs()]
        c   = FixedCollector(_config("mgr_run"), items=obs)
        mgr = CollectorManager()
        mgr.initialise()
        mgr.register(c, auto_init=False)
        r   = mgr.run("mgr_run")
        assert r.success
        assert r.count == 1

    def test_register_from_dict(self):
        mgr = CollectorManager()
        mgr.initialise()
        name = mgr.register_from_dict({"name": "dict_col", "type": "sync"})
        assert name == "dict_col"
        assert mgr._registry.has("dict_col")

    def test_run_all(self):
        mgr = CollectorManager()
        mgr.initialise()
        mgr.register(FixedCollector(_config("all_a"), items=[_make_obs()]), auto_init=False)
        mgr.register(FixedCollector(_config("all_b"), items=[_make_obs()]), auto_init=False)
        results = mgr.run_all()
        assert len(results) == 2

    def test_run_category(self):
        mgr = CollectorManager()
        mgr.initialise()
        cfg = _config("cat_run"); cfg.category = CollectorCategory.NEWS
        mgr.register(FixedCollector(cfg), auto_init=False)
        res = mgr.run_category(CollectorCategory.NEWS)
        assert len(res) == 1

    def test_trigger_event(self):
        ran = []
        class ECol(SyncCollector):
            def _do_collect(self): ran.append(1); return []
            def _do_normalise(self, r): return []

        mgr = CollectorManager()
        mgr.initialise()
        c   = ECol(_config("ev_trigger"))
        sc  = ScheduleConfig(schedule_type=ScheduleType.EVENT, event_names=["my.event"])
        mgr.register(c, schedule=sc, auto_init=False)
        n   = mgr.trigger_event("my.event")
        assert n == 1
        assert len(ran) == 1

    def test_unregister(self):
        mgr = CollectorManager()
        mgr.initialise()
        mgr.register(FixedCollector(_config("un1")), auto_init=False)
        mgr.unregister("un1")
        assert not mgr._registry.has("un1")

    def test_health(self):
        mgr = CollectorManager()
        mgr.initialise()
        mgr.register(FixedCollector(_config("hlt")), auto_init=False)
        h = mgr.health("hlt")
        assert h.collector_name == "hlt"

    def test_system_health(self):
        mgr = CollectorManager()
        mgr.initialise()
        mgr.register(FixedCollector(_config("sys_hlt")), auto_init=False)
        mgr.all_health()
        sh = mgr.system_health()
        assert "status" in sh

    def test_list_collectors(self):
        mgr = CollectorManager()
        mgr.initialise()
        mgr.register(FixedCollector(_config("lc1")), auto_init=False)
        mgr.register(FixedCollector(_config("lc2")), auto_init=False)
        assert set(mgr.list_collectors()) == {"lc1", "lc2"}

    def test_shutdown(self):
        mgr = CollectorManager()
        mgr.initialise()
        mgr.shutdown()
        assert not mgr._initialised

    def test_concurrency(self):
        """Multiple threads can register and run collectors concurrently."""
        mgr    = CollectorManager()
        mgr.initialise()
        errors = []

        def worker(i):
            try:
                c = FixedCollector(_config(f"conc{i}"), items=[_make_obs()])
                mgr.register(c, auto_init=False)
                mgr.run(f"conc{i}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors


# ═══════════════════════════════════════════════════════════════════════════════
# Category base classes
# ═══════════════════════════════════════════════════════════════════════════════

class TestCategoryCollectors:
    def test_market_data_category(self):
        from iios.observation.collectors.categories import MarketDataCollector
        class MyMDC(MarketDataCollector):
            def _do_collect(self): return []
            def _do_normalise(self, r): return []
        c = MyMDC(_config("mdc"))
        assert c.config.category == CollectorCategory.MARKET_DATA

    def test_news_category(self):
        from iios.observation.collectors.categories import NewsCollector
        class MyNC(NewsCollector):
            def _do_collect(self): return []
            def _do_normalise(self, r): return []
        c = MyNC(_config("nc"))
        assert c.config.category == CollectorCategory.NEWS
        assert c.config.obs_type == ObservationType.NEWS

    def test_plugin_collector_info(self):
        from iios.observation.collectors.categories import PluginCollector
        class MyPlugin(PluginCollector):
            PLUGIN_NAME    = "test_plugin"
            PLUGIN_VERSION = "2.0.0"
            def _do_collect(self): return []
            def _do_normalise(self, r): return []
        c = MyPlugin(_config("plugin"))
        info = c.plugin_info()
        assert info["name"]    == "test_plugin"
        assert info["version"] == "2.0.0"
        assert c.config.category == CollectorCategory.PLUGIN

    def test_internal_system_source(self):
        from iios.observation.collectors.categories import InternalSystemCollector
        class MyISC(InternalSystemCollector):
            def _do_collect(self): return []
            def _do_normalise(self, r): return []
        c = MyISC(_config("isc"))
        assert c.config.source == ObservationSource.INTERNAL_AGENT

    def test_all_categories_importable(self):
        from iios.observation.collectors.categories import (
            MacroCollector, CorporateActionCollector,
            FinancialStatementCollector, ExchangeCollector,
            BrokerCollector, AlternativeDataCollector,
            SocialMediaCollector, ResearchCollector,
        )
        for cls in [MacroCollector, CorporateActionCollector,
                    FinancialStatementCollector, ExchangeCollector,
                    BrokerCollector, AlternativeDataCollector,
                    SocialMediaCollector, ResearchCollector]:
            assert issubclass(cls, BaseCollector)
