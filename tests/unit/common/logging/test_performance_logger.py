"""tests/unit/common/logging/test_performance_logger.py
Unit tests for PerformanceLogger — timing accuracy, context manager, pipeline logging.
"""
from __future__ import annotations

import io
import json
import logging
import time
from typing import Any, Dict, List

import pytest

from iios.common.logging.performance_logger import (
    PerformanceLogger,
    PerformanceRecord,
    _Timer,
    get_performance_logger,
)
from iios.common.logging.structured_logger import JsonFormatter


def _attach_capture(perf: PerformanceLogger) -> io.StringIO:
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(JsonFormatter())
    underlying = perf._log.logger
    underlying.handlers.clear()
    underlying.setLevel(logging.DEBUG)
    underlying.addHandler(handler)
    underlying.propagate = False
    return buf


def _records(buf: io.StringIO) -> List[Dict[str, Any]]:
    return [json.loads(l) for l in buf.getvalue().splitlines() if l.strip()]


# ── Timer ─────────────────────────────────────────────────────────────────────

class TestTimer:

    def test_elapsed_sec_non_negative(self):
        t = _Timer()
        t.start()
        time.sleep(0.01)
        t.stop()
        assert t.elapsed_sec >= 0.0

    def test_elapsed_ms_property(self):
        t = _Timer()
        t.start()
        time.sleep(0.01)
        t.stop()
        assert t.elapsed_ms == pytest.approx(t.elapsed_sec * 1000, rel=0.1)

    def test_cpu_time_non_negative(self):
        t = _Timer()
        t.start()
        _ = sum(range(100000))  # some CPU work
        t.stop()
        assert t.cpu_time_sec >= 0.0

    def test_memory_none_when_not_tracking(self):
        t = _Timer(track_memory=False)
        t.start()
        t.stop()
        assert t.memory_delta_kb is None

    def test_memory_measured_when_tracking(self):
        t = _Timer(track_memory=True)
        t.start()
        large_list = list(range(10000))   # allocate some memory
        t.stop()
        # Value could be 0 on heavily-optimised runtimes, but should not be None
        assert t.memory_delta_kb is not None


# ── Construction / registry ───────────────────────────────────────────────────

class TestConstruction:

    def test_get_performance_logger_returns_instance(self):
        pl = get_performance_logger("test.perf.ctor")
        assert isinstance(pl, PerformanceLogger)

    def test_same_name_returns_same_instance(self):
        a = get_performance_logger("test.perf.same", engine_id="E1")
        b = get_performance_logger("test.perf.same", engine_id="E1")
        assert a is b

    def test_different_engine_id_different_instance(self):
        a = get_performance_logger("test.perf.diff", engine_id="EA")
        b = get_performance_logger("test.perf.diff", engine_id="EB")
        assert a is not b


# ── Context-manager measure ───────────────────────────────────────────────────

class TestMeasure:

    def test_measure_returns_timer(self):
        pl = PerformanceLogger("test.perf.measure")
        _attach_capture(pl)
        with pl.measure("op") as t:
            pass
        assert isinstance(t, _Timer)

    def test_measure_elapsed_positive(self):
        pl = PerformanceLogger("test.perf.elapsed")
        _attach_capture(pl)
        with pl.measure("sleep_op") as t:
            time.sleep(0.01)
        assert t.elapsed_sec > 0.005

    def test_measure_logs_record(self):
        pl = PerformanceLogger("test.perf.log")
        buf = _attach_capture(pl)
        with pl.measure("my_op"):
            pass
        records = _records(buf)
        assert records, "No log output"
        ctx = records[0].get("context", {})
        assert ctx.get("perf_name") == "my_op"
        assert "elapsed_ms" in ctx

    def test_measure_logs_stage(self):
        pl = PerformanceLogger("test.perf.stage_cm")
        buf = _attach_capture(pl)
        with pl.measure("fetch", stage="data_fetch", pipeline="intelligence"):
            pass
        records = _records(buf)
        ctx = records[0].get("context", {})
        assert ctx.get("stage")    == "data_fetch"
        assert ctx.get("pipeline") == "intelligence"

    def test_measure_still_logs_on_exception(self):
        pl = PerformanceLogger("test.perf.exc")
        buf = _attach_capture(pl)
        try:
            with pl.measure("failing_op"):
                raise RuntimeError("deliberate")
        except RuntimeError:
            pass
        records = _records(buf)
        assert records, "Should log even when exception occurs"

    def test_measure_stores_in_summary(self):
        pl = PerformanceLogger("test.perf.summary_cm")
        _attach_capture(pl)
        pl.clear()
        with pl.measure("op_summary"):
            pass
        summary = pl.summary()
        assert len(summary) == 1
        assert summary[0].name == "op_summary"

    def test_measure_with_metadata(self):
        pl = PerformanceLogger("test.perf.meta")
        buf = _attach_capture(pl)
        with pl.measure("tagged_op", metadata={"symbol": "NIFTY"}):
            pass
        records = _records(buf)
        ctx = records[0].get("context", {})
        assert ctx.get("symbol") == "NIFTY"


# ── log_execution ─────────────────────────────────────────────────────────────

class TestLogExecution:

    def test_log_execution_emits_record(self):
        pl = PerformanceLogger("test.perf.exec")
        buf = _attach_capture(pl)
        pl.log_execution("my_exec", elapsed_sec=0.042)
        records = _records(buf)
        ctx = records[0].get("context", {})
        assert ctx.get("perf_name") == "my_exec"
        assert ctx.get("elapsed_ms") == pytest.approx(42.0, rel=0.01)

    def test_log_execution_stores_record(self):
        pl = PerformanceLogger("test.perf.exec.store")
        _attach_capture(pl)
        pl.clear()
        pl.log_execution("store_exec", elapsed_sec=0.1)
        assert len(pl.summary()) == 1


# ── log_stage ─────────────────────────────────────────────────────────────────

class TestLogStage:

    def test_log_stage_emits_record(self):
        pl = PerformanceLogger("test.perf.stage")
        buf = _attach_capture(pl)
        pl.log_stage("normalise", 12.4)
        records = _records(buf)
        ctx = records[0].get("context", {})
        assert ctx.get("stage") == "normalise"
        assert ctx.get("elapsed_ms") == pytest.approx(12.4, rel=0.01)

    def test_log_stage_with_pipeline(self):
        pl = PerformanceLogger("test.perf.stage.pipe")
        buf = _attach_capture(pl)
        pl.log_stage("fetch", 80.0, pipeline="cycle")
        records = _records(buf)
        ctx = records[0].get("context", {})
        assert ctx.get("pipeline") == "cycle"


# ── log_pipeline ──────────────────────────────────────────────────────────────

class TestLogPipeline:

    def test_log_pipeline_emits_summary(self):
        pl = PerformanceLogger("test.perf.pipeline")
        buf = _attach_capture(pl)
        pl.log_pipeline(
            "intelligence_cycle",
            total_ms=140.0,
            stage_durations={"fetch": 80.0, "normalise": 12.4, "score": 47.6},
        )
        records = _records(buf)
        assert records
        ctx = records[0].get("context", {})
        assert ctx.get("pipeline") == "intelligence_cycle"
        assert "stage_durations_ms" in ctx

    def test_pipeline_total_ms_accurate(self):
        pl = PerformanceLogger("test.perf.pipeline.total")
        buf = _attach_capture(pl)
        pl.log_pipeline("pipe", total_ms=200.0, stage_durations={"a": 100.0, "b": 100.0})
        records = _records(buf)
        ctx = records[0].get("context", {})
        assert ctx.get("elapsed_ms") == pytest.approx(200.0, rel=0.01)


# ── summary / clear ───────────────────────────────────────────────────────────

class TestSummaryAndClear:

    def test_summary_returns_list_of_records(self):
        pl = PerformanceLogger("test.perf.sum")
        _attach_capture(pl)
        pl.clear()
        pl.log_execution("op1", elapsed_sec=0.01)
        pl.log_execution("op2", elapsed_sec=0.02)
        summary = pl.summary()
        assert len(summary) == 2
        assert all(isinstance(r, PerformanceRecord) for r in summary)

    def test_summary_returns_copy(self):
        pl = PerformanceLogger("test.perf.sum.copy")
        _attach_capture(pl)
        pl.clear()
        pl.log_execution("op", elapsed_sec=0.01)
        s1 = pl.summary()
        s1.clear()
        assert len(pl.summary()) == 1

    def test_clear_empties_buffer(self):
        pl = PerformanceLogger("test.perf.clear")
        _attach_capture(pl)
        pl.log_execution("op", elapsed_sec=0.01)
        pl.clear()
        assert pl.summary() == []

    def test_buffer_capped_at_200(self):
        pl = PerformanceLogger("test.perf.cap")
        _attach_capture(pl)
        pl.clear()
        for i in range(250):
            pl.log_execution(f"op_{i}", elapsed_sec=0.001)
        assert len(pl.summary()) <= 200


# ── PerformanceRecord ─────────────────────────────────────────────────────────

class TestPerformanceRecord:

    def test_record_is_frozen(self):
        pl = PerformanceLogger("test.perf.rec.frozen")
        _attach_capture(pl)
        pl.clear()
        pl.log_execution("op", elapsed_sec=0.01)
        rec = pl.summary()[0]
        with pytest.raises((AttributeError, TypeError)):
            rec.elapsed_sec = 999.0   # type: ignore[misc]

    def test_record_has_utc_timestamp(self):
        from datetime import timezone
        pl = PerformanceLogger("test.perf.rec.ts")
        _attach_capture(pl)
        pl.clear()
        pl.log_execution("op", elapsed_sec=0.01)
        rec = pl.summary()[0]
        assert rec.timestamp.tzinfo == timezone.utc
