"""tests/unit/common/errors/test_error_context.py
Unit tests for ErrorContext — context propagation, thread safety, async safety.
"""
from __future__ import annotations

import asyncio
import threading
from typing import List, Optional

import pytest

from iios.common.errors.error_context import (
    ErrorContext,
    bind_error_context,
    clear_error_context,
    current_context_dict,
    get_error_context,
    set_error_context,
)


@pytest.fixture(autouse=True)
def reset_ctx():
    clear_error_context()
    yield
    clear_error_context()


# ── ErrorContext dataclass ────────────────────────────────────────────────────

class TestErrorContextDataclass:

    def test_default_values(self):
        ctx = ErrorContext()
        assert ctx.engine_id      == ""
        assert ctx.stage          == ""
        assert ctx.workflow_id    == ""
        assert ctx.correlation_id == ""
        assert ctx.request_id     == ""
        assert ctx.operation      == ""
        assert ctx.component      == ""
        assert ctx.exception_chain == []
        assert ctx.extra          == {}

    def test_custom_values(self):
        ctx = ErrorContext(engine_id="iios:test", stage="fetch", workflow_id="WF-1")
        assert ctx.engine_id   == "iios:test"
        assert ctx.stage       == "fetch"
        assert ctx.workflow_id == "WF-1"

    def test_timestamp_is_utc(self):
        from datetime import timezone
        ctx = ErrorContext()
        assert ctx.timestamp.tzinfo == timezone.utc

    def test_to_dict_omits_empty_strings(self):
        ctx = ErrorContext(engine_id="E", stage="S")
        d = ctx.to_dict()
        assert d["engine_id"] == "E"
        assert d["stage"]     == "S"
        # empty fields are omitted
        assert "workflow_id"    not in d
        assert "correlation_id" not in d

    def test_to_dict_includes_exception_chain(self):
        ctx = ErrorContext(engine_id="E")
        ctx.add_to_chain(ValueError("boom"))
        d = ctx.to_dict()
        assert len(d["exception_chain"]) == 1
        assert d["exception_chain"][0]["type"]    == "ValueError"
        assert d["exception_chain"][0]["message"] == "boom"

    def test_to_dict_includes_extra(self):
        ctx = ErrorContext()
        ctx.extra["symbol"] = "NIFTY"
        d = ctx.to_dict()
        assert d["extra"]["symbol"] == "NIFTY"

    def test_copy_is_independent(self):
        ctx = ErrorContext(engine_id="E", stage="S")
        ctx.exception_chain.append({"type": "E1", "message": "m1"})
        copy = ctx.copy()
        copy.engine_id = "NEW"
        copy.exception_chain.append({"type": "E2", "message": "m2"})
        assert ctx.engine_id == "E"
        assert len(ctx.exception_chain) == 1


class TestAddToChain:

    def test_add_single_exception(self):
        ctx = ErrorContext()
        ctx.add_to_chain(ValueError("test"))
        assert len(ctx.exception_chain) == 1
        assert ctx.exception_chain[0]["type"] == "ValueError"

    def test_add_multiple_exceptions(self):
        ctx = ErrorContext()
        ctx.add_to_chain(ValueError("v"))
        ctx.add_to_chain(RuntimeError("r"))
        assert len(ctx.exception_chain) == 2

    def test_duplicate_not_added_twice(self):
        ctx = ErrorContext()
        exc = ValueError("same")
        ctx.add_to_chain(exc)
        ctx.add_to_chain(exc)   # same type + message
        assert len(ctx.exception_chain) == 1

    def test_different_messages_both_added(self):
        ctx = ErrorContext()
        ctx.add_to_chain(ValueError("msg1"))
        ctx.add_to_chain(ValueError("msg2"))   # same type, different message
        assert len(ctx.exception_chain) == 2


class TestEnrich:

    def test_known_fields_updated(self):
        ctx = ErrorContext()
        ctx.enrich(engine_id="E", stage="S")
        assert ctx.engine_id == "E"
        assert ctx.stage     == "S"

    def test_unknown_fields_go_to_extra(self):
        ctx = ErrorContext()
        ctx.enrich(symbol="NIFTY", score=9.2)
        assert ctx.extra["symbol"] == "NIFTY"
        assert ctx.extra["score"]  == 9.2

    def test_enrich_returns_self(self):
        ctx = ErrorContext()
        result = ctx.enrich(engine_id="E")
        assert result is ctx


# ── Context-var API ───────────────────────────────────────────────────────────

class TestContextVarAPI:

    def test_get_default_is_none(self):
        assert get_error_context() is None

    def test_set_then_get(self):
        ctx = ErrorContext(engine_id="E")
        token = set_error_context(ctx)
        assert get_error_context() is ctx
        from iios.common.errors.error_context import _CONTEXT_VAR
        _CONTEXT_VAR.reset(token)

    def test_clear_sets_none(self):
        set_error_context(ErrorContext(engine_id="E"))
        clear_error_context()
        assert get_error_context() is None

    def test_current_context_dict_empty_when_none(self):
        assert current_context_dict() == {}

    def test_current_context_dict_when_set(self):
        ctx = ErrorContext(engine_id="E", stage="S")
        token = set_error_context(ctx)
        d = current_context_dict()
        assert d["engine_id"] == "E"
        assert d["stage"]     == "S"
        from iios.common.errors.error_context import _CONTEXT_VAR
        _CONTEXT_VAR.reset(token)


# ── bind_error_context ────────────────────────────────────────────────────────

class TestBindErrorContext:

    def test_sets_context_inside_block(self):
        ctx = ErrorContext(engine_id="E")
        with bind_error_context(ctx):
            assert get_error_context() is ctx

    def test_restores_none_after_block(self):
        ctx = ErrorContext(engine_id="E")
        with bind_error_context(ctx):
            pass
        assert get_error_context() is None

    def test_restores_previous_context_after_block(self):
        outer = ErrorContext(engine_id="OUTER")
        inner = ErrorContext(engine_id="INNER")
        token = set_error_context(outer)
        with bind_error_context(inner):
            assert get_error_context() is inner
        assert get_error_context() is outer
        from iios.common.errors.error_context import _CONTEXT_VAR
        _CONTEXT_VAR.reset(token)

    def test_exception_added_to_chain_on_error(self):
        ctx = ErrorContext(engine_id="E")
        try:
            with bind_error_context(ctx):
                raise ValueError("inner error")
        except ValueError:
            pass
        assert len(ctx.exception_chain) == 1
        assert ctx.exception_chain[0]["type"] == "ValueError"

    def test_context_restored_on_exception(self):
        ctx = ErrorContext(engine_id="E")
        try:
            with bind_error_context(ctx):
                raise RuntimeError("crash")
        except RuntimeError:
            pass
        assert get_error_context() is None

    def test_yields_context(self):
        ctx = ErrorContext(engine_id="E")
        with bind_error_context(ctx) as bound:
            assert bound is ctx

    def test_nested_bind(self):
        outer = ErrorContext(engine_id="OUTER")
        inner = ErrorContext(engine_id="INNER")
        with bind_error_context(outer):
            assert get_error_context().engine_id == "OUTER"
            with bind_error_context(inner):
                assert get_error_context().engine_id == "INNER"
            assert get_error_context().engine_id == "OUTER"
        assert get_error_context() is None


# ── Thread safety ─────────────────────────────────────────────────────────────

class TestThreadSafety:

    def test_context_isolated_per_thread(self):
        results: List[Optional[str]] = [None, None]
        barrier = threading.Barrier(2)

        def thread_fn(idx: int, engine_id: str) -> None:
            ctx = ErrorContext(engine_id=engine_id)
            set_error_context(ctx)
            barrier.wait()
            results[idx] = get_error_context().engine_id

        t1 = threading.Thread(target=thread_fn, args=(0, "ENG-T1"))
        t2 = threading.Thread(target=thread_fn, args=(1, "ENG-T2"))
        t1.start(); t2.start()
        t1.join();  t2.join()

        assert results[0] == "ENG-T1"
        assert results[1] == "ENG-T2"

    def test_bind_isolated_per_thread(self):
        ready = threading.Event()
        done  = threading.Event()

        def bg_thread() -> None:
            ctx = ErrorContext(engine_id="BG-ENG")
            with bind_error_context(ctx):
                ready.set()
                done.wait()

        t = threading.Thread(target=bg_thread)
        t.start()
        ready.wait()
        # Main thread context should not be affected
        assert get_error_context() is None
        done.set()
        t.join()


# ── Async safety ──────────────────────────────────────────────────────────────

class TestAsyncSafety:

    def test_bind_propagates_to_coroutine(self):
        async def _inner() -> Optional[str]:
            ctx = get_error_context()
            return ctx.engine_id if ctx else None

        async def _main() -> Optional[str]:
            ctx = ErrorContext(engine_id="ASYNC-ENG")
            with bind_error_context(ctx):
                return await _inner()

        result = asyncio.run(_main())
        assert result == "ASYNC-ENG"

    def test_different_tasks_isolated(self):
        async def _task(engine_id: str) -> Optional[str]:
            ctx = ErrorContext(engine_id=engine_id)
            with bind_error_context(ctx):
                await asyncio.sleep(0)
                c = get_error_context()
                return c.engine_id if c else None

        async def _main():
            return await asyncio.gather(
                _task("ENG-A"),
                _task("ENG-B"),
            )

        results = asyncio.run(_main())
        assert set(results) == {"ENG-A", "ENG-B"}
