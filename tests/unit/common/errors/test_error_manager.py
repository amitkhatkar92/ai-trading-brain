"""tests/unit/common/errors/test_error_manager.py
Unit tests for ErrorManager — handler registration, dispatch, statistics, thread safety.
"""
from __future__ import annotations

import threading
from typing import List, Optional, Tuple

import pytest

from iios.common.errors.error_context import ErrorContext, clear_error_context
from iios.common.errors.error_manager import (
    ErrorManager,
    get_error_manager,
    reset_error_manager,
)
from iios.common.errors.exceptions import (
    EngineError,
    IIOSError,
    IntegrationError,
    ValidationError,
)
from iios.common.errors.failure_metrics import FailureTracker
from iios.common.errors.recovery_engine import RecoveryEngine
from iios.common.errors.retry_policy import FixedRetry, NoRetry


@pytest.fixture(autouse=True)
def clean_state():
    reset_error_manager()
    clear_error_context()
    yield
    reset_error_manager()
    clear_error_context()


@pytest.fixture
def mgr() -> ErrorManager:
    tracker = FailureTracker()
    return ErrorManager(failure_tracker=tracker, default_policy=NoRetry())


# ── Handler registration ──────────────────────────────────────────────────────

class TestHandlerRegistration:

    def test_register_handler_no_error(self, mgr):
        mgr.register_handler(ValueError, lambda e, c: None)

    def test_register_multiple_handlers_same_type(self, mgr):
        calls: List[str] = []
        mgr.register_handler(ValueError, lambda e, c: calls.append("h1"))
        mgr.register_handler(ValueError, lambda e, c: calls.append("h2"))
        mgr.dispatch(ValueError("test"), ErrorContext(engine_id="E"))
        assert "h1" in calls
        assert "h2" in calls

    def test_handlers_called_in_registration_order(self, mgr):
        order: List[int] = []
        mgr.register_handler(ValueError, lambda e, c: order.append(1))
        mgr.register_handler(ValueError, lambda e, c: order.append(2))
        mgr.dispatch(ValueError("x"), ErrorContext(engine_id="E"))
        assert order == [1, 2]

    def test_unregister_handlers(self, mgr):
        called: List[bool] = []
        mgr.register_handler(ValueError, lambda e, c: called.append(True))
        mgr.unregister_handlers(ValueError)
        mgr.dispatch(ValueError("x"), ErrorContext(engine_id="E"))
        assert not called

    def test_unregister_nonexistent_does_not_raise(self, mgr):
        mgr.unregister_handlers(RuntimeError)   # never registered — should not raise


# ── Dispatch ──────────────────────────────────────────────────────────────────

class TestDispatch:

    def test_dispatch_calls_matching_handler(self, mgr):
        received: List[BaseException] = []
        mgr.register_handler(ValueError, lambda e, c: received.append(e))
        exc = ValueError("test")
        mgr.dispatch(exc, ErrorContext(engine_id="E"))
        assert received == [exc]

    def test_dispatch_no_handler_does_not_raise(self, mgr):
        # Should not raise even with no handler registered
        mgr.dispatch(RuntimeError("no handler"), ErrorContext(engine_id="E"))

    def test_dispatch_passes_context_to_handler(self, mgr):
        received_ctx: List[Optional[ErrorContext]] = []
        mgr.register_handler(ValueError, lambda e, c: received_ctx.append(c))
        ctx = ErrorContext(engine_id="E", stage="S")
        mgr.dispatch(ValueError("x"), ctx)
        assert received_ctx[0] is ctx

    def test_dispatch_with_none_context_uses_current(self, mgr):
        received_ctx: List[Optional[ErrorContext]] = []
        mgr.register_handler(ValueError, lambda e, c: received_ctx.append(c))
        mgr.dispatch(ValueError("x"), None)   # should not raise
        assert len(received_ctx) == 1

    def test_dispatch_mro_lookup(self, mgr):
        """Handler for IIOSError should catch EngineError (subclass)."""
        received: List[str] = []
        mgr.register_handler(IIOSError, lambda e, c: received.append(type(e).__name__))
        mgr.dispatch(EngineError("sub"), ErrorContext(engine_id="E"))
        assert received == ["EngineError"]

    def test_most_specific_handler_wins(self, mgr):
        received: List[str] = []
        mgr.register_handler(IIOSError,    lambda e, c: received.append("base"))
        mgr.register_handler(EngineError,  lambda e, c: received.append("specific"))
        mgr.dispatch(EngineError("x"), ErrorContext(engine_id="E"))
        # Most specific type — EngineError — should be used
        assert received == ["specific"]

    def test_handler_exception_does_not_propagate(self, mgr):
        def bad_handler(e, c):
            raise RuntimeError("handler bug")

        mgr.register_handler(ValueError, bad_handler)
        # Should not raise
        mgr.dispatch(ValueError("x"), ErrorContext(engine_id="E"))

    def test_dispatch_records_failure_in_metrics(self, mgr):
        mgr.dispatch(ValueError("x"), ErrorContext(engine_id="iios:test"))
        snap = mgr.statistics()
        assert snap.total_failures >= 1


# ── Recovery engine factory ───────────────────────────────────────────────────

class TestRecoveryEngineFactory:

    def test_returns_recovery_engine(self, mgr):
        re = mgr.get_recovery_engine("iios:test")
        assert isinstance(re, RecoveryEngine)

    def test_same_engine_id_returns_same_instance(self, mgr):
        a = mgr.get_recovery_engine("iios:test")
        b = mgr.get_recovery_engine("iios:test")
        assert a is b

    def test_different_engine_ids_different_instances(self, mgr):
        a = mgr.get_recovery_engine("iios:eng-a")
        b = mgr.get_recovery_engine("iios:eng-b")
        assert a is not b

    def test_per_call_policy_returns_uncached_engine(self, mgr):
        a = mgr.get_recovery_engine("iios:test")
        b = mgr.get_recovery_engine("iios:test", policy=FixedRetry(max_retries=5))
        assert a is not b

    def test_recovery_engine_has_correct_engine_id(self, mgr):
        re = mgr.get_recovery_engine("iios:market:integration")
        assert re.engine_id == "iios:market:integration"


# ── report_failure / report_retry ─────────────────────────────────────────────

class TestReporting:

    def test_report_failure_increments_metrics(self, mgr):
        mgr.report_failure("iios:test", ValueError("x"))
        snap = mgr.statistics()
        assert snap.total_failures >= 1

    def test_report_retry_increments_retries(self, mgr):
        mgr.report_retry("iios:test")
        snap = mgr.engine_statistics("iios:test")
        assert snap.retries == 1

    def test_report_failure_with_recovery_time(self, mgr):
        mgr.report_failure(
            "iios:test",
            ValueError("x"),
            recovery_time_sec  = 1.5,
            recovery_succeeded = True,
        )
        snap = mgr.engine_statistics("iios:test")
        assert snap.recoveries          == 1
        assert snap.recovery_successes  == 1
        assert snap.mean_time_to_recovery == pytest.approx(1.5)


# ── statistics ────────────────────────────────────────────────────────────────

class TestStatistics:

    def test_statistics_returns_snapshot(self, mgr):
        snap = mgr.statistics()
        assert snap is not None

    def test_engine_statistics_returns_none_for_unknown(self, mgr):
        assert mgr.engine_statistics("nonexistent") is None

    def test_engine_statistics_returns_snapshot(self, mgr):
        mgr.report_failure("iios:known", ValueError("x"))
        snap = mgr.engine_statistics("iios:known")
        assert snap is not None
        assert snap.engine_id == "iios:known"


# ── reset ─────────────────────────────────────────────────────────────────────

class TestReset:

    def test_reset_clears_handlers(self, mgr):
        called: List[bool] = []
        mgr.register_handler(ValueError, lambda e, c: called.append(True))
        mgr.reset()
        mgr.dispatch(ValueError("x"), ErrorContext(engine_id="E"))
        assert not called

    def test_reset_clears_recovery_cache(self, mgr):
        re1 = mgr.get_recovery_engine("iios:test")
        mgr.reset()
        re2 = mgr.get_recovery_engine("iios:test")
        assert re1 is not re2

    def test_reset_clears_metrics(self, mgr):
        mgr.report_failure("iios:test", ValueError("x"))
        mgr.reset()
        snap = mgr.statistics()
        assert snap.total_failures == 0


# ── Singleton ─────────────────────────────────────────────────────────────────

class TestSingleton:

    def test_get_error_manager_returns_same_instance(self):
        a = get_error_manager()
        b = get_error_manager()
        assert a is b

    def test_reset_error_manager_replaces_instance(self):
        a = get_error_manager()
        reset_error_manager()
        b = get_error_manager()
        assert a is not b


# ── Thread safety ─────────────────────────────────────────────────────────────

class TestThreadSafety:

    def test_concurrent_dispatch_no_crash(self, mgr):
        received: List[int] = []
        lock = threading.Lock()

        def handler(e, c):
            with lock:
                received.append(1)

        mgr.register_handler(ValueError, handler)

        def worker():
            for _ in range(100):
                mgr.dispatch(ValueError("concurrent"), ErrorContext(engine_id="E"))

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert len(received) == 500

    def test_concurrent_register_and_dispatch(self, mgr):
        """Registering handlers while dispatching must not deadlock or crash."""
        stop = threading.Event()
        errors: List[Exception] = []

        def dispatcher():
            for _ in range(200):
                try:
                    mgr.dispatch(ValueError("x"), ErrorContext(engine_id="E"))
                except Exception as e:
                    errors.append(e)

        def registrar():
            for i in range(200):
                try:
                    mgr.register_handler(ValueError, lambda e, c: None)
                except Exception as e:
                    errors.append(e)

        t1 = threading.Thread(target=dispatcher)
        t2 = threading.Thread(target=registrar)
        t1.start(); t2.start()
        t1.join();  t2.join()

        assert errors == []
