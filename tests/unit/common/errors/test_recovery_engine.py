"""tests/unit/common/errors/test_recovery_engine.py
Unit tests for RecoveryEngine, RecoveryStrategy, CircuitBreakerHook, DeadLetterHook.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from iios.common.errors.error_context import ErrorContext, clear_error_context
from iios.common.errors.recovery_engine import (
    CircuitBreakerHook,
    DeadLetterHook,
    RecoveryEngine,
    RecoveryResult,
    RecoveryStrategy,
    _NoOpCircuitBreaker,
    _NoOpDeadLetter,
)
from iios.common.errors.retry_policy import FixedRetry, NoRetry, ExponentialBackoff


@pytest.fixture(autouse=True)
def reset_ctx():
    clear_error_context()
    yield
    clear_error_context()


def _no_sleep(secs: float) -> None:
    """Replace time.sleep so tests don't actually sleep."""
    pass


# ── RecoveryStrategy ──────────────────────────────────────────────────────────

class TestRecoveryStrategy:

    def test_all_values_exist(self):
        for name in ("retry", "fallback", "skip_stage", "resume_workflow",
                     "abort_workflow", "safe_shutdown"):
            assert RecoveryStrategy(name)

    def test_is_str_enum(self):
        assert isinstance(RecoveryStrategy.RETRY, str)
        assert RecoveryStrategy.RETRY == "retry"


# ── RecoveryResult ─────────────────────────────────────────────────────────────

class TestRecoveryResult:

    def test_frozen(self):
        r: RecoveryResult[int] = RecoveryResult(
            succeeded=True, strategy=RecoveryStrategy.RETRY,
            value=42, error=None, attempts=1, elapsed_sec=0.01,
        )
        with pytest.raises((AttributeError, TypeError)):
            r.succeeded = False   # type: ignore[misc]

    def test_fields_accessible(self):
        r: RecoveryResult[str] = RecoveryResult(
            succeeded=True, strategy=RecoveryStrategy.FALLBACK,
            value="ok", error=None, attempts=2, elapsed_sec=0.5,
        )
        assert r.succeeded
        assert r.value   == "ok"
        assert r.attempts == 2


# ── No-op hooks ───────────────────────────────────────────────────────────────

class TestNoOpHooks:

    def test_circuit_breaker_always_allows(self):
        cb = _NoOpCircuitBreaker()
        assert cb.allow_request("e", "op") is True

    def test_circuit_breaker_records_noop(self):
        cb = _NoOpCircuitBreaker()
        cb.record_success("e", "op")   # Should not raise
        cb.record_failure("e", "op")   # Should not raise

    def test_dead_letter_send_noop(self):
        dl = _NoOpDeadLetter()
        dl.send("op", "e", ValueError("x"), {})   # Should not raise


# ── Successful execution ──────────────────────────────────────────────────────

class TestSuccessfulExecution:

    def test_returns_value_on_success(self):
        eng = RecoveryEngine(engine_id="iios:test", retry_policy=NoRetry())
        result = eng.execute(lambda: 42, operation="get_42")
        assert result.succeeded
        assert result.value == 42

    def test_attempts_is_one_on_first_success(self):
        eng = RecoveryEngine(engine_id="iios:test", retry_policy=NoRetry())
        result = eng.execute(lambda: "ok")
        assert result.attempts == 1

    def test_elapsed_sec_positive(self):
        eng = RecoveryEngine(engine_id="iios:test", retry_policy=NoRetry())
        result = eng.execute(lambda: None)
        assert result.elapsed_sec >= 0.0

    def test_error_is_none_on_success(self):
        eng = RecoveryEngine(engine_id="iios:test", retry_policy=NoRetry())
        result = eng.execute(lambda: "ok")
        assert result.error is None


# ── Retry behaviour ───────────────────────────────────────────────────────────

class TestRetryBehaviour:

    def test_succeeds_after_retries(self):
        calls: List[int] = []

        def fn():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("not yet")
            return "done"

        eng = RecoveryEngine(
            engine_id    = "iios:test",
            retry_policy = FixedRetry(max_retries=5, delay_sec=0.0),
            sleep_fn     = _no_sleep,
        )
        result = eng.execute(fn, operation="fn")
        assert result.succeeded
        assert result.value    == "done"
        assert result.attempts == 3

    def test_fails_after_max_retries_exhausted(self):
        def always_fail():
            raise RuntimeError("permanent")

        eng = RecoveryEngine(
            engine_id    = "iios:test",
            retry_policy = FixedRetry(max_retries=2, delay_sec=0.0),
            sleep_fn     = _no_sleep,
        )
        result = eng.execute(always_fail)
        assert not result.succeeded
        assert result.attempts == 3   # 1 original + 2 retries
        assert isinstance(result.error, RuntimeError)

    def test_per_call_policy_override(self):
        calls: List[int] = []

        def fn():
            calls.append(1)
            if len(calls) < 2:
                raise ValueError("retry me")
            return "done"

        # Engine has NoRetry but we override per-call
        eng = RecoveryEngine(engine_id="iios:test", retry_policy=NoRetry())
        result = eng.execute(
            fn,
            policy   = FixedRetry(max_retries=3, delay_sec=0.0),
            operation = "override",
        )
        assert result.succeeded
        assert result.attempts == 2

    def test_no_retry_does_not_retry(self):
        calls: List[int] = []

        def fn():
            calls.append(1)
            raise ValueError("fail")

        eng = RecoveryEngine(engine_id="iios:test", retry_policy=NoRetry())
        result = eng.execute(fn)
        assert not result.succeeded
        assert len(calls) == 1


# ── Fallback ──────────────────────────────────────────────────────────────────

class TestFallback:

    def test_fallback_called_when_all_retries_exhausted(self):
        def always_fail():
            raise RuntimeError("permanent")

        eng = RecoveryEngine(
            engine_id    = "iios:test",
            retry_policy = FixedRetry(max_retries=1, delay_sec=0.0),
            sleep_fn     = _no_sleep,
        )
        result = eng.execute(always_fail, fallback=lambda: "fallback_value")
        assert result.succeeded
        assert result.value    == "fallback_value"
        assert result.strategy == RecoveryStrategy.FALLBACK

    def test_fallback_not_called_on_success(self):
        fallback_called: List[bool] = []

        def fb():
            fallback_called.append(True)
            return "fb"

        eng = RecoveryEngine(engine_id="iios:test", retry_policy=NoRetry())
        result = eng.execute(lambda: "ok", fallback=fb)
        assert result.succeeded
        assert result.value == "ok"
        assert not fallback_called

    def test_failed_fallback_returns_failure(self):
        def always_fail():
            raise RuntimeError("fail")

        def also_fails():
            raise RuntimeError("fallback also fails")

        eng = RecoveryEngine(
            engine_id    = "iios:test",
            retry_policy = NoRetry(),
        )
        result = eng.execute(always_fail, fallback=also_fails)
        assert not result.succeeded


# ── execute_with_skip ─────────────────────────────────────────────────────────

class TestExecuteWithSkip:

    def test_returns_default_on_failure(self):
        def always_fail():
            raise RuntimeError("fail")

        eng = RecoveryEngine(engine_id="iios:test", retry_policy=NoRetry())
        result = eng.execute_with_skip(always_fail, default={"empty": True}, operation="op")
        assert result.succeeded
        assert result.value      == {"empty": True}
        assert result.strategy   == RecoveryStrategy.SKIP_STAGE

    def test_returns_real_value_on_success(self):
        eng = RecoveryEngine(engine_id="iios:test", retry_policy=NoRetry())
        result = eng.execute_with_skip(lambda: 99, default=0, operation="op")
        assert result.succeeded
        assert result.value == 99


# ── Error context integration ─────────────────────────────────────────────────

class TestErrorContextIntegration:

    def test_context_captured_in_result(self):
        ctx = ErrorContext(engine_id="CTX-ENG", stage="test")
        eng = RecoveryEngine(engine_id="iios:test", retry_policy=NoRetry())

        def fail():
            raise ValueError("boom")

        result = eng.execute(fail, context=ctx)
        assert not result.succeeded
        assert result.context.get("engine_id") == "CTX-ENG"

    def test_exception_chain_populated(self):
        ctx = ErrorContext(engine_id="E")
        eng = RecoveryEngine(engine_id="iios:test", retry_policy=NoRetry())

        def fail():
            raise ValueError("test exception")

        result = eng.execute(fail, context=ctx)
        assert len(ctx.exception_chain) >= 1


# ── Circuit breaker hook ──────────────────────────────────────────────────────

class TestCircuitBreakerHook:

    def test_open_circuit_returns_failure(self):
        class OpenCircuit(CircuitBreakerHook):
            def allow_request(self, engine_id, operation):   return False
            def record_success(self, engine_id, operation):  pass
            def record_failure(self, engine_id, operation):  pass

        eng = RecoveryEngine(
            engine_id       = "iios:test",
            retry_policy    = NoRetry(),
            circuit_breaker = OpenCircuit(),
        )
        result = eng.execute(lambda: "ok", operation="test_op")
        assert not result.succeeded
        assert "Circuit open" in str(result.error)

    def test_success_calls_record_success(self):
        recorded: List[str] = []

        class TrackingCB(CircuitBreakerHook):
            def allow_request(self, e, o):  return True
            def record_success(self, e, o): recorded.append("success")
            def record_failure(self, e, o): recorded.append("failure")

        eng = RecoveryEngine(
            engine_id       = "iios:test",
            retry_policy    = NoRetry(),
            circuit_breaker = TrackingCB(),
        )
        eng.execute(lambda: "ok")
        assert recorded == ["success"]


# ── Dead-letter hook ──────────────────────────────────────────────────────────

class TestDeadLetterHook:

    def test_dead_letter_called_on_terminal_failure(self):
        sent: List[dict] = []

        class TrackingDL(DeadLetterHook):
            def send(self, operation, engine_id, error, context):
                sent.append({"op": operation, "error": error})

        eng = RecoveryEngine(
            engine_id    = "iios:test",
            retry_policy = NoRetry(),
            dead_letter  = TrackingDL(),
        )
        eng.execute(lambda: (_ for _ in ()).throw(RuntimeError("dead")), operation="dead_op")
        assert len(sent) == 1
        assert isinstance(sent[0]["error"], RuntimeError)


# ── with_policy ───────────────────────────────────────────────────────────────

class TestWithPolicy:

    def test_returns_new_engine_with_same_id(self):
        eng = RecoveryEngine(engine_id="iios:test", retry_policy=NoRetry())
        new_eng = eng.with_policy(FixedRetry(max_retries=5))
        assert new_eng.engine_id == "iios:test"
        assert new_eng is not eng
