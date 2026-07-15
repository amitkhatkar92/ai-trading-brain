"""tests/unit/common/logging/test_audit_logger.py
Unit tests for AuditLogger — all 7 event types, structured output, registry.
"""
from __future__ import annotations

import io
import json
import logging
from typing import Any, Dict, List

import pytest

from iios.common.logging.audit_logger import (
    AuditEventType,
    AuditLogger,
    AuditRecord,
    get_audit_logger,
)
from iios.common.logging.logging_context import LoggingContext
from iios.common.logging.structured_logger import JsonFormatter


@pytest.fixture(autouse=True)
def clear_context():
    LoggingContext.clear()
    yield
    LoggingContext.clear()


def _attach_capture(audit: AuditLogger) -> io.StringIO:
    """Attach a capturing JSON handler and return the buffer."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(JsonFormatter())
    underlying = audit._log.logger
    underlying.handlers.clear()
    underlying.setLevel(logging.DEBUG)
    underlying.addHandler(handler)
    underlying.propagate = False
    return buf


def _records(buf: io.StringIO) -> List[Dict[str, Any]]:
    return [json.loads(l) for l in buf.getvalue().splitlines() if l.strip()]


# ── Construction / registry ───────────────────────────────────────────────────

class TestConstruction:

    def test_get_audit_logger_returns_audit_logger(self):
        al = get_audit_logger("test.audit.ctor")
        assert isinstance(al, AuditLogger)

    def test_same_name_returns_same_instance(self):
        a = get_audit_logger("test.audit.same", engine_id="E1")
        b = get_audit_logger("test.audit.same", engine_id="E1")
        assert a is b

    def test_different_engine_id_returns_different_instance(self):
        a = get_audit_logger("test.audit.diff", engine_id="EA")
        b = get_audit_logger("test.audit.diff", engine_id="EB")
        assert a is not b


# ── AuditRecord structure ─────────────────────────────────────────────────────

class TestAuditRecord:

    def test_record_fields(self):
        al = AuditLogger("test.record.fields", engine_id="E", component="C")
        _attach_capture(al)
        rec = al.log_lifecycle_event("E", "INITIALIZED", "RUNNING", "1.0.0")
        assert isinstance(rec, AuditRecord)
        assert rec.event_type       == AuditEventType.LIFECYCLE_EVENT
        assert rec.engine_id        == "E"
        assert rec.component        == "C"
        assert rec.details["engine_id"]  == "E"
        assert rec.details["from_state"] == "INITIALIZED"
        assert rec.details["to_state"]   == "RUNNING"
        assert rec.details["version"]    == "1.0.0"

    def test_record_is_frozen(self):
        al = AuditLogger("test.record.frozen")
        _attach_capture(al)
        rec = al.log_lifecycle_event("E", "A", "B", "1.0.0")
        with pytest.raises((AttributeError, TypeError)):
            rec.engine_id = "modified"   # type: ignore[misc]

    def test_record_timestamp_is_utc(self):
        from datetime import timezone
        al = AuditLogger("test.record.ts")
        _attach_capture(al)
        rec = al.log_lifecycle_event("E", "A", "B", "1.0.0")
        assert rec.timestamp.tzinfo == timezone.utc


# ── Event types ───────────────────────────────────────────────────────────────

class TestLifecycleEvent:

    def test_emits_lifecycle_event_type(self):
        al = AuditLogger("test.lifecycle", engine_id="iios:test", component="test")
        buf = _attach_capture(al)
        al.log_lifecycle_event("iios:test", "INITIALIZED", "RUNNING", "1.0.0")
        records = _records(buf)
        assert records, "No log output"
        ctx = records[0].get("context", {})
        assert ctx.get("event_type") == AuditEventType.LIFECYCLE_EVENT.value
        assert ctx.get("from_state") == "INITIALIZED"
        assert ctx.get("to_state")   == "RUNNING"

    def test_lifecycle_message_contains_engine(self):
        al = AuditLogger("test.lifecycle.msg")
        buf = _attach_capture(al)
        al.log_lifecycle_event("my-engine", "STARTING", "RUNNING", "2.0.0")
        records = _records(buf)
        assert "my-engine" in records[0]["msg"]


class TestWorkflowEvent:

    def test_emits_workflow_event_type(self):
        al = AuditLogger("test.workflow")
        buf = _attach_capture(al)
        al.log_workflow_event("WF-001", "data_fetch", "completed")
        records = _records(buf)
        ctx = records[0].get("context", {})
        assert ctx.get("event_type")   == AuditEventType.WORKFLOW_EVENT.value
        assert ctx.get("workflow_id")  == "WF-001"
        assert ctx.get("stage")        == "data_fetch"
        assert ctx.get("event")        == "completed"


class TestConfigChange:

    def test_emits_config_changed_type(self):
        al = AuditLogger("test.config")
        buf = _attach_capture(al)
        al.log_config_change("market_engine", "polling_interval", 30, 15)
        records = _records(buf)
        ctx = records[0].get("context", {})
        assert ctx.get("event_type") == AuditEventType.CONFIG_CHANGED.value
        assert ctx.get("key")        == "polling_interval"
        assert ctx.get("old_value")  == 30
        assert ctx.get("new_value")  == 15

    def test_config_message_contains_key(self):
        al = AuditLogger("test.config.msg")
        buf = _attach_capture(al)
        al.log_config_change("comp", "timeout", 5, 10)
        records = _records(buf)
        assert "timeout" in records[0]["msg"]


class TestValidationEvent:

    def test_pass_result(self):
        al = AuditLogger("test.validation.pass")
        buf = _attach_capture(al)
        al.log_validation_event("market_engine", "schema_check", True)
        records = _records(buf)
        ctx = records[0].get("context", {})
        assert ctx.get("result") == "PASS"

    def test_fail_result(self):
        al = AuditLogger("test.validation.fail")
        buf = _attach_capture(al)
        al.log_validation_event("market_engine", "schema_check", False)
        records = _records(buf)
        ctx = records[0].get("context", {})
        assert ctx.get("result") == "FAIL"

    def test_validation_event_type(self):
        al = AuditLogger("test.validation.type")
        buf = _attach_capture(al)
        al.log_validation_event("comp", "check", True)
        records = _records(buf)
        ctx = records[0].get("context", {})
        assert ctx.get("event_type") == AuditEventType.VALIDATION_EVENT.value


class TestPublicationEvent:

    def test_emits_publication_event_type(self):
        al = AuditLogger("test.pub")
        buf = _attach_capture(al)
        al.log_publication_event("company_engine", "SNAP-123")
        records = _records(buf)
        ctx = records[0].get("context", {})
        assert ctx.get("event_type")  == AuditEventType.PUBLICATION_EVENT.value
        assert ctx.get("snapshot_id") == "SNAP-123"


class TestFailureEvent:

    def test_emits_failure_event_type(self):
        al = AuditLogger("test.failure")
        buf = _attach_capture(al)
        al.log_failure("strategy_engine", "TimeoutError", "API timed out")
        records = _records(buf)
        ctx = records[0].get("context", {})
        assert ctx.get("event_type")    == AuditEventType.FAILURE.value
        assert ctx.get("error_type")    == "TimeoutError"
        assert ctx.get("error_message") == "API timed out"

    def test_failure_captures_exception(self):
        al = AuditLogger("test.failure.exc")
        buf = _attach_capture(al)
        try:
            raise ValueError("deliberate failure")
        except ValueError as e:
            al.log_failure("comp", "ValueError", str(e), exc=e)
        records = _records(buf)
        assert "exc" in records[0]
        assert "deliberate failure" in records[0]["exc"]


class TestSecurityEvent:

    def test_emits_security_event_type(self):
        al = AuditLogger("test.security")
        buf = _attach_capture(al)
        al.log_security_event("auth_module", "UNAUTHORIZED_ACCESS")
        records = _records(buf)
        ctx = records[0].get("context", {})
        assert ctx.get("event_type")    == AuditEventType.SECURITY_EVENT.value
        assert ctx.get("security_event") == "UNAUTHORIZED_ACCESS"


# ── Context snapshot ──────────────────────────────────────────────────────────

class TestContextSnapshot:

    def test_context_snapshot_captures_current_context(self):
        al = AuditLogger("test.ctx.snap")
        _attach_capture(al)
        LoggingContext.set_workflow_id("WF-SNAP")
        rec = al.log_lifecycle_event("E", "A", "B", "1.0")
        assert rec.context_snapshot.get("workflow_id") == "WF-SNAP"

    def test_context_snapshot_empty_when_no_context(self):
        al = AuditLogger("test.ctx.empty")
        _attach_capture(al)
        rec = al.log_lifecycle_event("E", "A", "B", "1.0")
        assert rec.context_snapshot == {}


# ── AuditEventType enum ───────────────────────────────────────────────────────

class TestAuditEventType:

    def test_all_event_types_exist(self):
        for name in (
            "CONFIG_CHANGED", "LIFECYCLE_EVENT", "WORKFLOW_EVENT",
            "VALIDATION_EVENT", "PUBLICATION_EVENT", "FAILURE", "SECURITY_EVENT",
        ):
            assert hasattr(AuditEventType, name)

    def test_is_string_enum(self):
        assert isinstance(AuditEventType.LIFECYCLE_EVENT, str)
        assert AuditEventType.LIFECYCLE_EVENT == "LIFECYCLE_EVENT"
