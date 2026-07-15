"""tests/unit/common/logging/test_logging_context.py
Unit tests for LoggingContext — context propagation, thread safety, async safety.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import threading
import time
import uuid
from typing import List, Optional

import pytest

from iios.common.logging.logging_context import (
    LoggingContext,
    _CTX_WORKFLOW_ID,
    _CTX_CORRELATION_ID,
    _CTX_REQUEST_ID,
    _CTX_TRACE_ID,
    _CTX_SESSION_ID,
    _CTX_PORTFOLIO_ID,
    _CTX_DECISION_ID,
    _CTX_MARKET_ID,
    _CTX_COMPANY_ID,
    _CTX_STRATEGY_ID,
    _CTX_ENGINE_ID,
)


@pytest.fixture(autouse=True)
def clear_context():
    """Reset context before each test."""
    LoggingContext.clear()
    yield
    LoggingContext.clear()


# ── Basic get/set ─────────────────────────────────────────────────────────────

class TestBasicGetSet:

    def test_default_values_are_empty_strings(self):
        assert LoggingContext.get_workflow_id()    == ""
        assert LoggingContext.get_trace_id()       == ""
        assert LoggingContext.get_correlation_id() == ""
        assert LoggingContext.get_request_id()     == ""
        assert LoggingContext.get_session_id()     == ""
        assert LoggingContext.get_portfolio_id()   == ""
        assert LoggingContext.get_decision_id()    == ""
        assert LoggingContext.get_market_id()      == ""
        assert LoggingContext.get_company_id()     == ""
        assert LoggingContext.get_strategy_id()    == ""
        assert LoggingContext.get_engine_id()      == ""

    def test_set_workflow_id(self):
        LoggingContext.set_workflow_id("WF-001")
        assert LoggingContext.get_workflow_id() == "WF-001"

    def test_set_trace_id(self):
        tid = str(uuid.uuid4())
        LoggingContext.set_trace_id(tid)
        assert LoggingContext.get_trace_id() == tid

    def test_set_correlation_id(self):
        LoggingContext.set_correlation_id("CORR-abc")
        assert LoggingContext.get_correlation_id() == "CORR-abc"

    def test_set_request_id(self):
        LoggingContext.set_request_id("REQ-xyz")
        assert LoggingContext.get_request_id() == "REQ-xyz"

    def test_set_session_id(self):
        LoggingContext.set_session_id("SESS-1")
        assert LoggingContext.get_session_id() == "SESS-1"

    def test_set_portfolio_id(self):
        LoggingContext.set_portfolio_id("PORT-A")
        assert LoggingContext.get_portfolio_id() == "PORT-A"

    def test_set_decision_id(self):
        LoggingContext.set_decision_id("DEC-10")
        assert LoggingContext.get_decision_id() == "DEC-10"

    def test_set_market_id(self):
        LoggingContext.set_market_id("NSE")
        assert LoggingContext.get_market_id() == "NSE"

    def test_set_company_id(self):
        LoggingContext.set_company_id("TCS")
        assert LoggingContext.get_company_id() == "TCS"

    def test_set_strategy_id(self):
        LoggingContext.set_strategy_id("STR-momentum")
        assert LoggingContext.get_strategy_id() == "STR-momentum"

    def test_set_engine_id(self):
        LoggingContext.set_engine_id("iios:market:integration")
        assert LoggingContext.get_engine_id() == "iios:market:integration"


# ── to_dict ───────────────────────────────────────────────────────────────────

class TestToDict:

    def test_empty_context_returns_empty_dict(self):
        assert LoggingContext.to_dict() == {}

    def test_set_fields_appear_in_dict(self):
        LoggingContext.set_workflow_id("WF-002")
        LoggingContext.set_request_id("REQ-1")
        d = LoggingContext.to_dict()
        assert d["workflow_id"] == "WF-002"
        assert d["request_id"]  == "REQ-1"
        assert "trace_id" not in d   # not set → omitted

    def test_all_set_fields_appear(self):
        LoggingContext.set_workflow_id("W")
        LoggingContext.set_trace_id("T")
        LoggingContext.set_correlation_id("C")
        LoggingContext.set_request_id("R")
        LoggingContext.set_session_id("S")
        LoggingContext.set_portfolio_id("P")
        LoggingContext.set_decision_id("D")
        LoggingContext.set_market_id("M")
        LoggingContext.set_company_id("CO")
        LoggingContext.set_strategy_id("ST")
        LoggingContext.set_engine_id("E")
        d = LoggingContext.to_dict()
        assert len(d) == 11


# ── clear ─────────────────────────────────────────────────────────────────────

class TestClear:

    def test_clear_resets_all_fields(self):
        LoggingContext.set_workflow_id("WF-X")
        LoggingContext.set_trace_id("TR-X")
        LoggingContext.clear()
        assert LoggingContext.get_workflow_id() == ""
        assert LoggingContext.get_trace_id()    == ""

    def test_clear_empty_context_is_idempotent(self):
        LoggingContext.clear()
        LoggingContext.clear()
        assert LoggingContext.to_dict() == {}


# ── bind (context manager) ────────────────────────────────────────────────────

class TestBind:

    def test_bind_sets_values_inside_block(self):
        ctx = LoggingContext(workflow_id="WF-BIND", request_id="REQ-BIND")
        with ctx.bind():
            assert LoggingContext.get_workflow_id() == "WF-BIND"
            assert LoggingContext.get_request_id()  == "REQ-BIND"

    def test_bind_restores_previous_values_after_block(self):
        LoggingContext.set_workflow_id("WF-OUTER")
        ctx = LoggingContext(workflow_id="WF-INNER")
        with ctx.bind():
            assert LoggingContext.get_workflow_id() == "WF-INNER"
        assert LoggingContext.get_workflow_id() == "WF-OUTER"

    def test_bind_restores_empty_after_block(self):
        ctx = LoggingContext(workflow_id="WF-A")
        with ctx.bind():
            assert LoggingContext.get_workflow_id() == "WF-A"
        assert LoggingContext.get_workflow_id() == ""

    def test_bind_restores_on_exception(self):
        LoggingContext.set_workflow_id("WF-SAFE")
        ctx = LoggingContext(workflow_id="WF-CRASH")
        try:
            with ctx.bind():
                raise RuntimeError("deliberate")
        except RuntimeError:
            pass
        assert LoggingContext.get_workflow_id() == "WF-SAFE"

    def test_nested_bind(self):
        outer = LoggingContext(workflow_id="WF-OUTER", trace_id="T-OUTER")
        inner = LoggingContext(workflow_id="WF-INNER")
        with outer.bind():
            assert LoggingContext.get_workflow_id() == "WF-OUTER"
            assert LoggingContext.get_trace_id()    == "T-OUTER"
            with inner.bind():
                assert LoggingContext.get_workflow_id() == "WF-INNER"
                assert LoggingContext.get_trace_id()    == "T-OUTER"   # not overridden
            assert LoggingContext.get_workflow_id() == "WF-OUTER"
        assert LoggingContext.get_workflow_id() == ""

    def test_bind_only_sets_non_empty_fields(self):
        LoggingContext.set_portfolio_id("PORT-KEEP")
        ctx = LoggingContext(workflow_id="WF-SET")   # portfolio_id is ""
        with ctx.bind():
            # portfolio_id should remain unchanged because bind doesn't set it
            assert LoggingContext.get_portfolio_id() == "PORT-KEEP"
        assert LoggingContext.get_portfolio_id() == "PORT-KEEP"


# ── current() ─────────────────────────────────────────────────────────────────

class TestCurrent:

    def test_current_returns_snapshot(self):
        LoggingContext.set_workflow_id("WF-SNAP")
        LoggingContext.set_trace_id("TR-SNAP")
        snap = LoggingContext.current()
        assert snap.workflow_id == "WF-SNAP"
        assert snap.trace_id    == "TR-SNAP"

    def test_modifying_snapshot_does_not_affect_context(self):
        LoggingContext.set_workflow_id("WF-ORIG")
        snap = LoggingContext.current()
        # snap is a dataclass, not frozen — but mutating it should not affect context vars
        snap.workflow_id = "WF-MUTATED"
        assert LoggingContext.get_workflow_id() == "WF-ORIG"


# ── new_trace() ───────────────────────────────────────────────────────────────

class TestNewTrace:

    def test_new_trace_generates_unique_trace_id(self):
        ctx1 = LoggingContext.new_trace()
        ctx2 = LoggingContext.new_trace()
        assert ctx1.trace_id != ""
        assert ctx2.trace_id != ""
        assert ctx1.trace_id != ctx2.trace_id

    def test_new_trace_generates_correlation_id_when_not_provided(self):
        ctx = LoggingContext.new_trace()
        assert ctx.correlation_id != ""

    def test_new_trace_respects_workflow_id(self):
        ctx = LoggingContext.new_trace(workflow_id="WF-TRACE")
        assert ctx.workflow_id == "WF-TRACE"

    def test_new_trace_respects_explicit_correlation_id(self):
        ctx = LoggingContext.new_trace(correlation_id="CORR-EXPLICIT")
        assert ctx.correlation_id == "CORR-EXPLICIT"


# ── Thread safety ─────────────────────────────────────────────────────────────

class TestThreadSafety:

    def test_context_isolated_per_thread(self):
        """Each thread must have its own context variable values."""
        results: List[Optional[str]] = [None, None]
        barrier = threading.Barrier(2)

        def thread_fn(idx: int, value: str) -> None:
            LoggingContext.set_workflow_id(value)
            barrier.wait()   # synchronize so both threads set their value first
            results[idx] = LoggingContext.get_workflow_id()

        t1 = threading.Thread(target=thread_fn, args=(0, "T1-WF"))
        t2 = threading.Thread(target=thread_fn, args=(1, "T2-WF"))
        t1.start(); t2.start()
        t1.join();  t2.join()

        assert results[0] == "T1-WF"
        assert results[1] == "T2-WF"

    def test_bind_isolated_per_thread(self):
        """bind() in one thread must not affect another thread's context."""
        ready = threading.Event()
        done  = threading.Event()
        inner_value: List[str] = [""]

        def bg_thread() -> None:
            ctx = LoggingContext(workflow_id="BG-THREAD-WF")
            with ctx.bind():
                ready.set()    # signal main thread
                done.wait()    # wait until main thread checked

        t = threading.Thread(target=bg_thread)
        t.start()
        ready.wait()
        # main thread context should be unaffected
        assert LoggingContext.get_workflow_id() == ""
        done.set()
        t.join()

    def test_concurrent_set_does_not_corrupt_state(self):
        """High-concurrency set/get must not leak values across threads."""
        errors: List[str] = []

        def worker(wf_id: str) -> None:
            for _ in range(200):
                LoggingContext.set_workflow_id(wf_id)
                val = LoggingContext.get_workflow_id()
                if val != wf_id:
                    errors.append(f"Thread {wf_id} read {val!r}")

        threads = [threading.Thread(target=worker, args=(f"WF-{i}",)) for i in range(8)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert errors == []


# ── Async safety ──────────────────────────────────────────────────────────────

class TestAsyncSafety:

    def test_bind_propagates_into_coroutine(self):
        async def _inner() -> str:
            return LoggingContext.get_workflow_id()

        async def _main() -> str:
            ctx = LoggingContext(workflow_id="WF-ASYNC")
            with ctx.bind():
                return await _inner()

        result = asyncio.run(_main())
        assert result == "WF-ASYNC"

    def test_different_tasks_have_isolated_contexts(self):
        async def _task(wf_id: str) -> str:
            ctx = LoggingContext(workflow_id=wf_id)
            with ctx.bind():
                await asyncio.sleep(0)  # yield control
                return LoggingContext.get_workflow_id()

        async def _main():
            results = await asyncio.gather(
                _task("WF-TASK-A"),
                _task("WF-TASK-B"),
            )
            return results

        results = asyncio.run(_main())
        assert set(results) == {"WF-TASK-A", "WF-TASK-B"}
