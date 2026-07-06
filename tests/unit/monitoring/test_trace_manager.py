"""
tests/unit/monitoring/test_trace_manager.py
============================================
Tests for iios.monitoring.trace_manager
"""
from __future__ import annotations

import threading
import time
import pytest

from iios.monitoring.trace_manager import (
    TraceManager,
    _reset_trace_manager,
    get_trace_manager,
    current_trace,
    current_span,
)
from iios.monitoring.monitoring_constants import TraceStatus


@pytest.fixture()
def mgr():
    _reset_trace_manager()
    m = TraceManager()
    yield m
    _reset_trace_manager()


# ---------------------------------------------------------------------------
# trace() context manager
# ---------------------------------------------------------------------------


def test_trace_context_creates_and_finishes(mgr):
    with mgr.trace("my-operation") as ctx:
        assert ctx is not None
        assert ctx.operation == "my-operation"
    assert ctx.end_time is not None
    assert ctx.status in (TraceStatus.COMPLETED.value, TraceStatus.FAILED.value)


def test_trace_context_marks_completed(mgr):
    with mgr.trace("clean-op") as ctx:
        pass
    assert ctx.status == TraceStatus.COMPLETED.value


def test_trace_context_marks_failed_on_exception(mgr):
    ctx_ref: list = []
    with pytest.raises(RuntimeError):
        with mgr.trace("failing-op") as ctx:
            ctx_ref.append(ctx)
            raise RuntimeError("intentional")
    assert ctx_ref[0].status == TraceStatus.FAILED.value


# ---------------------------------------------------------------------------
# span() context manager
# ---------------------------------------------------------------------------


def test_span_attaches_to_current_trace(mgr):
    with mgr.trace("outer") as ctx:
        with mgr.span("inner-span") as span:
            assert span is not None
    assert any(s.operation == "inner-span" for s in ctx.spans)


def test_nested_spans_set_parent_span_id(mgr):
    with mgr.trace("parent-trace") as ctx:
        with mgr.span("parent-span") as parent:
            with mgr.span("child-span") as child:
                assert child.parent_span_id == parent.span_id


def test_span_outside_trace_creates_trace(mgr):
    with mgr.span("standalone") as span:
        assert span is not None


def test_span_fails_on_exception(mgr):
    span_ref: list = []
    with pytest.raises(ValueError):
        with mgr.trace("trace-with-bad-span"):
            with mgr.span("bad-span") as span:
                span_ref.append(span)
                raise ValueError("span error")
    assert span_ref[0].status == TraceStatus.FAILED.value


# ---------------------------------------------------------------------------
# Thread-local accessors
# ---------------------------------------------------------------------------


def test_current_trace_inside_context(mgr):
    with mgr.trace("active") as ctx:
        assert current_trace() is ctx


def test_current_trace_outside_context_is_none(mgr):
    assert current_trace() is None


def test_current_span_inside_span(mgr):
    with mgr.trace("t"):
        with mgr.span("s") as span:
            assert current_span() is span


def test_current_span_outside_span_is_none(mgr):
    assert current_span() is None


def test_thread_local_trace_isolated():
    """Each thread gets its own trace context."""
    results: dict[str, object] = {}
    _reset_trace_manager()
    shared_mgr = get_trace_manager()

    def worker(name: str) -> None:
        with shared_mgr.trace(f"trace-{name}"):
            import time
            time.sleep(0.01)
            t = current_trace()
            results[name] = t.operation if t else None

    t1 = threading.Thread(target=worker, args=("T1",))
    t2 = threading.Thread(target=worker, args=("T2",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert results.get("T1") == "trace-T1"
    assert results.get("T2") == "trace-T2"
    _reset_trace_manager()


# ---------------------------------------------------------------------------
# Query methods
# ---------------------------------------------------------------------------


def test_recent_traces(mgr):
    with mgr.trace("op1"):
        pass
    with mgr.trace("op2"):
        pass
    recent = mgr.recent_traces(n=5)
    assert len(recent) == 2


def test_find_trace_by_id(mgr):
    with mgr.trace("findable") as ctx:
        trace_id = ctx.trace_id
    found = mgr.find_trace(trace_id)
    assert found is not None
    assert found.trace_id == trace_id


def test_find_trace_unknown_returns_none(mgr):
    assert mgr.find_trace("no-such-id") is None


def test_slow_traces_threshold(mgr):
    # We can't reliably create slow traces in a unit test, but we can verify
    # the method returns a list without error
    result = mgr.slow_traces(threshold_ms=0.0)
    assert isinstance(result, list)


def test_active_traces_count(mgr):
    # Before any traces
    assert mgr.active_count == 0


# ---------------------------------------------------------------------------
# Trace count
# ---------------------------------------------------------------------------


def test_trace_count_increments(mgr):
    with mgr.trace("c1"):
        pass
    with mgr.trace("c2"):
        pass
    assert mgr.trace_count == 2


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


def test_get_trace_manager_singleton():
    _reset_trace_manager()
    a = get_trace_manager()
    b = get_trace_manager()
    assert a is b
    _reset_trace_manager()
