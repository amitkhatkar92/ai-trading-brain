"""tests/unit/common/logging/test_structured_logger.py
Unit tests for StructuredLogger and JsonFormatter.
"""
from __future__ import annotations

import json
import logging
import io
from typing import Any, Dict, List

import pytest

from iios.common.logging.logging_context import LoggingContext
from iios.common.logging.structured_logger import JsonFormatter, StructuredLogger, TextFormatter


@pytest.fixture(autouse=True)
def clear_context():
    LoggingContext.clear()
    yield
    LoggingContext.clear()


def _capture_json(
    logger: StructuredLogger,
    level: int = logging.DEBUG,
) -> tuple[io.StringIO, logging.StreamHandler]:
    """Attach a capturing JSON handler to the underlying logger."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter())
    logger.logger.setLevel(logging.DEBUG)
    logger.logger.handlers.clear()
    logger.logger.addHandler(handler)
    logger.logger.propagate = False
    return buf, handler


def _parse_first_record(buf: io.StringIO) -> Dict[str, Any]:
    lines = [l for l in buf.getvalue().splitlines() if l.strip()]
    assert lines, "No log output captured"
    return json.loads(lines[0])


# ── Construction ──────────────────────────────────────────────────────────────

class TestConstruction:

    def test_name_attribute(self):
        sl = StructuredLogger("test.module")
        assert sl.name == "test.module"

    def test_engine_id_attribute(self):
        sl = StructuredLogger("test.module", engine_id="iios:test:engine")
        assert sl.engine_id == "iios:test:engine"

    def test_get_factory(self):
        sl = StructuredLogger.get("test.factory", engine_id="E", component="C")
        assert sl.name == "test.factory"
        assert sl.engine_id == "E"

    def test_repr_contains_name_and_engine(self):
        sl = StructuredLogger("my.logger", engine_id="my:engine")
        r = repr(sl)
        assert "my.logger" in r
        assert "my:engine" in r


# ── Level checks ──────────────────────────────────────────────────────────────

class TestLevelChecks:

    def test_is_enabled_for_respects_underlying_logger(self):
        sl = StructuredLogger("test.level_check")
        sl.logger.setLevel(logging.WARNING)
        assert not sl.isEnabledFor(logging.DEBUG)
        assert not sl.isEnabledFor(logging.INFO)
        assert sl.isEnabledFor(logging.WARNING)
        assert sl.isEnabledFor(logging.ERROR)

    def test_set_level(self):
        sl = StructuredLogger("test.set_level")
        sl.set_level(logging.ERROR)
        assert sl.level == logging.ERROR


# ── Log methods ───────────────────────────────────────────────────────────────

class TestLogMethods:

    def test_debug_produces_output(self):
        sl = StructuredLogger("test.debug")
        buf, _ = _capture_json(sl)
        sl.debug("debug message")
        record = _parse_first_record(buf)
        assert record["level"] == "DEBUG"
        assert record["msg"]   == "debug message"

    def test_info_produces_output(self):
        sl = StructuredLogger("test.info")
        buf, _ = _capture_json(sl)
        sl.info("info message")
        record = _parse_first_record(buf)
        assert record["level"] == "INFO"

    def test_warning_produces_output(self):
        sl = StructuredLogger("test.warning")
        buf, _ = _capture_json(sl)
        sl.warning("warn message")
        record = _parse_first_record(buf)
        assert record["level"] == "WARNING"

    def test_warn_alias(self):
        sl = StructuredLogger("test.warn_alias")
        buf, _ = _capture_json(sl)
        sl.warn("warn via alias")
        record = _parse_first_record(buf)
        assert record["level"] == "WARNING"

    def test_error_produces_output(self):
        sl = StructuredLogger("test.error")
        buf, _ = _capture_json(sl)
        sl.error("error message")
        record = _parse_first_record(buf)
        assert record["level"] == "ERROR"

    def test_critical_produces_output(self):
        sl = StructuredLogger("test.critical")
        buf, _ = _capture_json(sl)
        sl.critical("critical message")
        record = _parse_first_record(buf)
        assert record["level"] == "CRITICAL"

    def test_exception_captures_exc_text(self):
        sl = StructuredLogger("test.exception")
        buf, _ = _capture_json(sl)
        try:
            raise ValueError("boom")
        except ValueError as e:
            sl.exception("caught error", exc=e)
        record = _parse_first_record(buf)
        assert "exc" in record
        assert "boom" in record["exc"]

    def test_structured_uses_explicit_level(self):
        sl = StructuredLogger("test.structured")
        buf, _ = _capture_json(sl)
        sl.structured(logging.WARNING, "explicit level")
        record = _parse_first_record(buf)
        assert record["level"] == "WARNING"


# ── JSON output fields ────────────────────────────────────────────────────────

class TestJsonFields:

    def test_timestamp_field_present(self):
        sl = StructuredLogger("test.ts")
        buf, _ = _capture_json(sl)
        sl.info("ts test")
        record = _parse_first_record(buf)
        assert "ts" in record
        assert record["ts"].endswith("+00:00")

    def test_logger_name_in_output(self):
        sl = StructuredLogger("test.name_check")
        buf, _ = _capture_json(sl)
        sl.info("name check")
        record = _parse_first_record(buf)
        assert record["logger"] == "test.name_check"

    def test_thread_id_in_output(self):
        sl = StructuredLogger("test.thread")
        buf, _ = _capture_json(sl)
        sl.info("thread check")
        record = _parse_first_record(buf)
        assert "thread_id" in record

    def test_elapsed_ms_injected(self):
        sl = StructuredLogger("test.elapsed")
        buf, _ = _capture_json(sl)
        sl.info("timed operation", elapsed_ms=42.5)
        record = _parse_first_record(buf)
        assert record["elapsed_ms"] == 42.5

    def test_engine_id_injected(self):
        sl = StructuredLogger("test.engine", engine_id="iios:test")
        buf, _ = _capture_json(sl)
        sl.info("engine id test")
        record = _parse_first_record(buf)
        assert record.get("engine_id") == "iios:test"

    def test_context_dict_injected(self):
        sl = StructuredLogger("test.ctx")
        buf, _ = _capture_json(sl)
        sl.info("ctx test", context={"portfolio": "P-001", "score": 9.2})
        record = _parse_first_record(buf)
        assert "context" in record
        assert record["context"]["portfolio"] == "P-001"
        assert record["context"]["score"] == 9.2

    def test_exception_exc_parameter(self):
        sl = StructuredLogger("test.exc_param")
        buf, _ = _capture_json(sl)
        try:
            raise RuntimeError("test exc")
        except RuntimeError as e:
            sl.error("error with exc", exc=e)
        record = _parse_first_record(buf)
        assert "exc" in record
        assert "RuntimeError" in record["exc"]


# ── Context injection ─────────────────────────────────────────────────────────

class TestContextInjection:

    def test_workflow_id_injected_from_context(self):
        sl = StructuredLogger("test.ctx_inject")
        buf, _ = _capture_json(sl)
        LoggingContext.set_workflow_id("WF-INJECT")
        sl.info("with context")
        record = _parse_first_record(buf)
        assert record.get("workflow_id") == "WF-INJECT"

    def test_all_context_ids_injected(self):
        sl = StructuredLogger("test.all_ctx")
        buf, _ = _capture_json(sl)
        LoggingContext.set_workflow_id("W")
        LoggingContext.set_trace_id("T")
        LoggingContext.set_correlation_id("C")
        LoggingContext.set_request_id("R")
        sl.info("all ctx")
        record = _parse_first_record(buf)
        assert record.get("workflow_id")    == "W"
        assert record.get("trace_id")       == "T"
        assert record.get("correlation_id") == "C"
        assert record.get("request_id")     == "R"

    def test_no_context_fields_when_context_empty(self):
        sl = StructuredLogger("test.no_ctx")
        buf, _ = _capture_json(sl)
        sl.info("no ctx")
        record = _parse_first_record(buf)
        assert "workflow_id"    not in record
        assert "trace_id"       not in record
        assert "correlation_id" not in record

    def test_bind_context_visible_in_log(self):
        sl = StructuredLogger("test.bind_ctx")
        buf, _ = _capture_json(sl)
        ctx = LoggingContext(workflow_id="WF-BIND-LOG", correlation_id="CORR-X")
        with ctx.bind():
            sl.info("bound context")
        record = _parse_first_record(buf)
        assert record.get("workflow_id")    == "WF-BIND-LOG"
        assert record.get("correlation_id") == "CORR-X"


# ── Level filtering ───────────────────────────────────────────────────────────

class TestLevelFiltering:

    def test_debug_suppressed_when_level_info(self):
        sl = StructuredLogger("test.filter_debug")
        sl.logger.setLevel(logging.INFO)
        buf, _ = _capture_json(sl, level=logging.INFO)
        sl.debug("suppressed")
        assert buf.getvalue().strip() == ""

    def test_info_visible_when_level_debug(self):
        sl = StructuredLogger("test.filter_info")
        buf, _ = _capture_json(sl, level=logging.DEBUG)
        sl.info("visible")
        record = _parse_first_record(buf)
        assert record["msg"] == "visible"


# ── TextFormatter ─────────────────────────────────────────────────────────────

class TestTextFormatter:

    def test_text_formatter_produces_readable_output(self):
        sl = StructuredLogger("test.text_fmt")
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setFormatter(TextFormatter())
        sl.logger.setLevel(logging.DEBUG)
        sl.logger.handlers.clear()
        sl.logger.addHandler(handler)
        sl.logger.propagate = False
        sl.info("readable output")
        output = buf.getvalue()
        assert "readable output" in output
        assert "INFO" in output
