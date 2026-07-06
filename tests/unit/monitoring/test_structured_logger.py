"""
tests/unit/monitoring/test_structured_logger.py
=================================================
Tests for iios.monitoring.structured_logger
"""
from __future__ import annotations

import logging
import threading
import pytest

from iios.monitoring.structured_logger import (
    StructuredLogger,
    get_structured_logger,
    correlation_context,
    set_context,
    get_context,
    clear_context,
    _reset_structured_loggers,
)
from iios.monitoring.monitoring_models import MonitoringContext


@pytest.fixture(autouse=True)
def reset():
    """Reset singleton cache and thread-local between tests."""
    clear_context()
    _reset_structured_loggers()
    yield
    clear_context()
    _reset_structured_loggers()


# ---------------------------------------------------------------------------
# Basic logging
# ---------------------------------------------------------------------------


def test_info_produces_log_record(caplog):
    with caplog.at_level(logging.INFO, logger="iios.test"):
        logger = StructuredLogger("iios.test", component="TestComp", layer="TestLayer")
        logger.info("hello world")
    assert any("hello world" in r.message for r in caplog.records)


def test_warning_produces_log_record(caplog):
    with caplog.at_level(logging.WARNING, logger="iios.test2"):
        logger = StructuredLogger("iios.test2")
        logger.warning("something wrong")
    assert any("something wrong" in r.message for r in caplog.records)


def test_error_produces_log_record(caplog):
    with caplog.at_level(logging.ERROR, logger="iios.test3"):
        logger = StructuredLogger("iios.test3")
        logger.error("an error occurred")
    assert any("an error occurred" in r.message for r in caplog.records)


def test_critical_produces_log_record(caplog):
    with caplog.at_level(logging.CRITICAL, logger="iios.test4"):
        logger = StructuredLogger("iios.test4")
        logger.critical("critical failure")
    assert any("critical failure" in r.message for r in caplog.records)


def test_exception_attaches_exc_info(caplog):
    with caplog.at_level(logging.ERROR, logger="iios.test5"):
        logger = StructuredLogger("iios.test5")
        try:
            raise ValueError("oops")
        except ValueError:
            logger.exception("caught error")
    assert any("caught error" in r.message for r in caplog.records)
    assert any(r.exc_info is not None for r in caplog.records)


# ---------------------------------------------------------------------------
# build_record
# ---------------------------------------------------------------------------


def test_build_record_populates_fields():
    logger = StructuredLogger("iios.rec", component="RecComp", layer="RecLayer")
    rec = logger.build_record("INFO", "test message", {"extra_key": "extra_val"})
    assert rec.level == "INFO"
    assert rec.message == "test message"
    assert rec.component == "RecComp"
    assert rec.layer == "RecLayer"
    assert rec.extra.get("extra_key") == "extra_val"


def test_build_record_has_thread_info():
    logger = StructuredLogger("iios.rec2")
    rec = logger.build_record("DEBUG", "msg", {})
    assert rec.thread_id > 0
    assert rec.process_id > 0


# ---------------------------------------------------------------------------
# Context propagation
# ---------------------------------------------------------------------------


def test_set_get_clear_context():
    ctx = MonitoringContext(correlation_id="cid-1", request_id="req-1")
    set_context(ctx)
    retrieved = get_context()
    assert retrieved is not None
    assert retrieved.correlation_id == "cid-1"
    clear_context()
    assert get_context() is None


def test_correlation_context_manager():
    with correlation_context("corr-42", "MyComp", "MyLayer"):
        ctx = get_context()
        assert ctx is not None
        assert ctx.correlation_id == "corr-42"
        assert ctx.component == "MyComp"
    # Context cleared after exit
    assert get_context() is None


def test_correlation_context_injects_into_record():
    logger = StructuredLogger("iios.ctx")
    with correlation_context("ctx-test"):
        rec = logger.build_record("INFO", "in-context", {})
    assert rec.correlation_id == "ctx-test"


def test_context_isolated_per_thread():
    results = {}

    def worker(cid: str) -> None:
        with correlation_context(cid):
            import time
            time.sleep(0.01)
            ctx = get_context()
            results[cid] = ctx.correlation_id if ctx else None

    t1 = threading.Thread(target=worker, args=("thread-A",))
    t2 = threading.Thread(target=worker, args=("thread-B",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert results.get("thread-A") == "thread-A"
    assert results.get("thread-B") == "thread-B"


# ---------------------------------------------------------------------------
# bind()
# ---------------------------------------------------------------------------


def test_bind_returns_new_logger_with_extra_context(caplog):
    logger = StructuredLogger("iios.bind", component="Base")
    bound = logger.bind(layer="BoundLayer")
    assert bound is not logger
    rec = bound.build_record("INFO", "bound message", {})
    assert rec.layer == "BoundLayer"


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------


def test_get_structured_logger_returns_same_instance():
    a = get_structured_logger("iios.singleton", component="C", layer="L")
    b = get_structured_logger("iios.singleton", component="C", layer="L")
    assert a is b


def test_get_structured_logger_different_keys_different_instances():
    a = get_structured_logger("iios.x", component="X")
    b = get_structured_logger("iios.y", component="Y")
    assert a is not b
