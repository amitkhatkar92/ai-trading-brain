"""Tests for iios.common.async_exec.timeout_policy"""
import asyncio
import pytest
from iios.common.async_exec.timeout_policy import (
    TimeoutPolicy,
    apply_timeout,
    with_stage_timeout,
    with_workflow_timeout,
    with_engine_timeout,
    with_pipeline_timeout,
    timeout_scope,
)
from iios.common.errors.exceptions import TimeoutError as IIOSTimeoutError


# ── TimeoutPolicy ────────────────────────────────────────────────────────────

class TestTimeoutPolicy:

    def test_defaults(self):
        p = TimeoutPolicy()
        assert p.stage_timeout_sec    == 30.0
        assert p.workflow_timeout_sec == 300.0
        assert p.engine_timeout_sec   == 60.0
        assert p.pipeline_timeout_sec == 120.0

    def test_strict_preset(self):
        p = TimeoutPolicy.strict()
        assert p.stage_timeout_sec    < TimeoutPolicy().stage_timeout_sec
        assert p.engine_timeout_sec   < TimeoutPolicy().engine_timeout_sec

    def test_relaxed_preset(self):
        p = TimeoutPolicy.relaxed()
        assert p.stage_timeout_sec    > TimeoutPolicy().stage_timeout_sec

    def test_unlimited_preset(self):
        p = TimeoutPolicy.unlimited()
        assert p.stage_timeout_sec    is None
        assert p.workflow_timeout_sec is None
        assert p.engine_timeout_sec   is None
        assert p.pipeline_timeout_sec is None

    def test_frozen(self):
        p = TimeoutPolicy()
        try:
            p.stage_timeout_sec = 99.0  # type: ignore[misc]
            assert False
        except (AttributeError, TypeError):
            pass

    def test_custom_values(self):
        p = TimeoutPolicy(stage_timeout_sec=5.0, engine_timeout_sec=20.0)
        assert p.stage_timeout_sec == 5.0
        assert p.engine_timeout_sec == 20.0

    def test_none_disables_timeout(self):
        p = TimeoutPolicy(stage_timeout_sec=None)
        assert p.stage_timeout_sec is None


# ── apply_timeout ─────────────────────────────────────────────────────────────

class TestApplyTimeout:

    def test_completes_within_timeout(self):
        async def fast():
            return "ok"
        result = asyncio.run(apply_timeout(fast(), timeout_sec=5.0))
        assert result == "ok"

    def test_none_timeout_disables_limit(self):
        async def fast():
            return "ok"
        result = asyncio.run(apply_timeout(fast(), timeout_sec=None))
        assert result == "ok"

    def test_timeout_raises_iios_error(self):
        async def slow():
            await asyncio.sleep(10.0)
        try:
            asyncio.run(apply_timeout(slow(), timeout_sec=0.01))
            assert False, "Expected IIOSTimeoutError"
        except IIOSTimeoutError as exc:
            assert "0.0" in str(exc) or "timed out" in str(exc).lower()

    def test_operation_in_error_message(self):
        async def slow():
            await asyncio.sleep(10.0)
        try:
            asyncio.run(apply_timeout(slow(), timeout_sec=0.01, operation="fetch_quotes"))
            assert False
        except IIOSTimeoutError as exc:
            assert "fetch_quotes" in str(exc)

    def test_engine_id_in_error_context(self):
        async def slow():
            await asyncio.sleep(10.0)
        try:
            asyncio.run(apply_timeout(
                slow(), timeout_sec=0.01,
                operation="test_op", engine_id="engine:test"
            ))
            assert False
        except IIOSTimeoutError as exc:
            assert exc.context.get("engine_id") == "engine:test" or "engine:test" in str(exc)

    def test_exception_passthrough(self):
        async def raises():
            raise ValueError("test error")
        try:
            asyncio.run(apply_timeout(raises(), timeout_sec=5.0))
            assert False
        except ValueError as exc:
            assert "test error" in str(exc)

    def test_return_value_preserved(self):
        async def returns_dict():
            return {"key": "value", "num": 42}
        result = asyncio.run(apply_timeout(returns_dict(), timeout_sec=5.0))
        assert result == {"key": "value", "num": 42}


# ── Scope helpers ─────────────────────────────────────────────────────────────

class TestScopeHelpers:

    def _policy(self, **kwargs) -> TimeoutPolicy:
        return TimeoutPolicy(**kwargs)

    def test_stage_timeout_passes(self):
        async def fast(): return 1
        p = self._policy(stage_timeout_sec=5.0)
        result = asyncio.run(with_stage_timeout(fast(), p, stage="test"))
        assert result == 1

    def test_stage_timeout_fires(self):
        async def slow(): await asyncio.sleep(10)
        p = self._policy(stage_timeout_sec=0.01)
        try:
            asyncio.run(with_stage_timeout(slow(), p, stage="my_stage"))
            assert False
        except IIOSTimeoutError as exc:
            assert "stage" in str(exc).lower() or "timed out" in str(exc).lower()

    def test_workflow_timeout_fires(self):
        async def slow(): await asyncio.sleep(10)
        p = self._policy(workflow_timeout_sec=0.01)
        try:
            asyncio.run(with_workflow_timeout(slow(), p, workflow_id="wf1"))
            assert False
        except IIOSTimeoutError:
            pass

    def test_engine_timeout_fires(self):
        async def slow(): await asyncio.sleep(10)
        p = self._policy(engine_timeout_sec=0.01)
        try:
            asyncio.run(with_engine_timeout(slow(), p, engine_id="eng1"))
            assert False
        except IIOSTimeoutError:
            pass

    def test_pipeline_timeout_fires(self):
        async def slow(): await asyncio.sleep(10)
        p = self._policy(pipeline_timeout_sec=0.01)
        try:
            asyncio.run(with_pipeline_timeout(slow(), p, pipeline="pipe1"))
            assert False
        except IIOSTimeoutError:
            pass

    def test_none_timeout_in_helpers(self):
        async def fast(): return "ok"
        p = TimeoutPolicy.unlimited()
        result = asyncio.run(with_stage_timeout(fast(), p))
        assert result == "ok"


# ── timeout_scope context manager ────────────────────────────────────────────

class TestTimeoutScope:

    def test_scope_passes_within_limit(self):
        async def run():
            async with timeout_scope(5.0, operation="test"):
                return 42
        assert asyncio.run(run()) == 42

    def test_scope_none_passes(self):
        async def run():
            async with timeout_scope(None, operation="no-limit"):
                return 99
        assert asyncio.run(run()) == 99

    def test_scope_fires_on_slow_code(self):
        async def run():
            async with timeout_scope(0.01, operation="slow_block"):
                await asyncio.sleep(10)
        try:
            asyncio.run(run())
            assert False
        except IIOSTimeoutError:
            pass

    def test_scope_propagates_non_timeout_exceptions(self):
        async def run():
            async with timeout_scope(5.0):
                raise RuntimeError("inner error")
        try:
            asyncio.run(run())
            assert False
        except RuntimeError as exc:
            assert "inner error" in str(exc)
