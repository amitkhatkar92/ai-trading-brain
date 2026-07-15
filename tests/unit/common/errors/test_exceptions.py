"""tests/unit/common/errors/test_exceptions.py
Unit tests for the IIOS exception hierarchy.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from iios.common.errors.exceptions import (
    IIOSError,
    ConfigurationError,
    ValidationError,
    WorkflowError,
    EngineError,
    DependencyError,
    IntegrationError,
    TimeoutError,
    RecoveryError,
    SecurityError,
)


# ── Hierarchy ─────────────────────────────────────────────────────────────────

class TestHierarchy:

    def test_all_are_iios_errors(self):
        for cls in (
            ConfigurationError, ValidationError, WorkflowError, EngineError,
            DependencyError, IntegrationError, TimeoutError, RecoveryError,
            SecurityError,
        ):
            assert issubclass(cls, IIOSError)

    def test_all_are_exceptions(self):
        assert issubclass(IIOSError, Exception)
        for cls in (
            ConfigurationError, ValidationError, WorkflowError, EngineError,
            DependencyError, IntegrationError, TimeoutError, RecoveryError,
            SecurityError,
        ):
            assert issubclass(cls, Exception)

    def test_catch_as_iios_error(self):
        with pytest.raises(IIOSError):
            raise EngineError("test")

    def test_catch_as_exception(self):
        with pytest.raises(Exception):
            raise ValidationError("test")


# ── IIOSError base ────────────────────────────────────────────────────────────

class TestIIOSErrorBase:

    def test_message_stored(self):
        e = IIOSError("test message")
        assert e.message == "test message"
        assert str(e) == "[IIOS-000] test message"

    def test_default_code(self):
        e = IIOSError("msg")
        assert e.code == "IIOS-000"

    def test_custom_code(self):
        e = IIOSError("msg", code="IIOS-TEST-001")
        assert e.code == "IIOS-TEST-001"

    def test_correlation_id(self):
        e = IIOSError("msg", correlation_id="CORR-abc")
        assert e.correlation_id == "CORR-abc"

    def test_empty_correlation_id_default(self):
        e = IIOSError("msg")
        assert e.correlation_id == ""

    def test_context_stored(self):
        ctx = {"key": "value", "count": 42}
        e = IIOSError("msg", context=ctx)
        assert e.context["key"] == "value"
        assert e.context["count"] == 42

    def test_context_defaults_to_empty_dict(self):
        e = IIOSError("msg")
        assert e.context == {}

    def test_timestamp_is_utc(self):
        e = IIOSError("msg")
        assert e.timestamp.tzinfo == timezone.utc

    def test_repr(self):
        e = IIOSError("msg", code="C-001", correlation_id="X")
        r = repr(e)
        assert "IIOSError" in r
        assert "C-001" in r
        assert "X" in r

    def test_to_dict(self):
        e = IIOSError("msg", code="C", correlation_id="CORR", context={"a": 1})
        d = e.to_dict()
        assert d["type"]           == "IIOSError"
        assert d["code"]           == "C"
        assert d["message"]        == "msg"
        assert d["correlation_id"] == "CORR"
        assert "timestamp" in d
        assert d["context"]["a"]   == 1

    def test_to_dict_timestamp_is_iso(self):
        e = IIOSError("msg")
        d = e.to_dict()
        # Should parse without error
        ts = datetime.fromisoformat(d["timestamp"])
        assert ts.tzinfo is not None

    def test_exception_chaining(self):
        try:
            try:
                raise ValueError("root cause")
            except ValueError as inner:
                raise IIOSError("wrapped") from inner
        except IIOSError as e:
            assert e.__cause__ is not None
            assert "root cause" in str(e.__cause__)


# ── ConfigurationError ────────────────────────────────────────────────────────

class TestConfigurationError:

    def test_default_code(self):
        assert ConfigurationError("msg").code == "IIOS-CFG-001"

    def test_custom_code_override(self):
        e = ConfigurationError("msg", code="MY-CODE")
        assert e.code == "MY-CODE"

    def test_str_contains_code(self):
        e = ConfigurationError("bad config")
        assert "IIOS-CFG-001" in str(e)
        assert "bad config" in str(e)


# ── ValidationError ───────────────────────────────────────────────────────────

class TestValidationError:

    def test_default_code(self):
        assert ValidationError("msg").code == "IIOS-VAL-001"

    def test_field_stored_in_context(self):
        e = ValidationError("invalid", field="weight")
        assert e.context["field"] == "weight"
        assert e.field == "weight"

    def test_value_stored_in_context(self):
        e = ValidationError("out of range", field="score", value=999)
        assert e.context["value"] == 999
        assert e.value == 999

    def test_no_field_no_value(self):
        e = ValidationError("msg")
        assert "field" not in e.context
        assert "value" not in e.context


# ── WorkflowError ─────────────────────────────────────────────────────────────

class TestWorkflowError:

    def test_default_code(self):
        assert WorkflowError("msg").code == "IIOS-WF-001"

    def test_workflow_id_in_context(self):
        e = WorkflowError("stage failed", workflow_id="WF-001", stage="data_fetch")
        assert e.context["workflow_id"] == "WF-001"
        assert e.context["stage"]       == "data_fetch"
        assert e.workflow_id == "WF-001"
        assert e.stage       == "data_fetch"


# ── EngineError ───────────────────────────────────────────────────────────────

class TestEngineError:

    def test_default_code(self):
        assert EngineError("msg").code == "IIOS-ENG-001"

    def test_engine_id_in_context(self):
        e = EngineError("start failed", engine_id="iios:market:integration")
        assert e.context["engine_id"] == "iios:market:integration"
        assert e.engine_id == "iios:market:integration"


# ── DependencyError ───────────────────────────────────────────────────────────

class TestDependencyError:

    def test_default_code(self):
        assert DependencyError("msg").code == "IIOS-DEP-001"

    def test_dependency_in_context(self):
        e = DependencyError("feed down", dependency="yahoo_feed")
        assert e.context["dependency"] == "yahoo_feed"
        assert e.dependency == "yahoo_feed"


# ── IntegrationError ──────────────────────────────────────────────────────────

class TestIntegrationError:

    def test_default_code(self):
        assert IntegrationError("msg").code == "IIOS-INT-001"

    def test_integration_and_status(self):
        e = IntegrationError("API error", integration="dhan_broker", status_code=451)
        assert e.context["integration"] == "dhan_broker"
        assert e.context["status_code"] == 451
        assert e.status_code == 451


# ── TimeoutError ──────────────────────────────────────────────────────────────

class TestTimeoutError:

    def test_default_code(self):
        assert TimeoutError("msg").code == "IIOS-TMO-001"

    def test_operation_and_timeout(self):
        e = TimeoutError("timed out", operation="get_quotes", timeout_sec=5.0)
        assert e.context["operation"]   == "get_quotes"
        assert e.context["timeout_sec"] == 5.0
        assert e.timeout_sec == 5.0

    def test_is_iios_error(self):
        e = TimeoutError("timed out")
        assert isinstance(e, IIOSError)


# ── RecoveryError ─────────────────────────────────────────────────────────────

class TestRecoveryError:

    def test_default_code(self):
        assert RecoveryError("msg").code == "IIOS-REC-001"

    def test_strategy_and_attempts(self):
        e = RecoveryError("recovery failed", strategy="fallback", attempts=3)
        assert e.context["strategy"] == "fallback"
        assert e.context["attempts"] == 3
        assert e.attempts == 3


# ── SecurityError ─────────────────────────────────────────────────────────────

class TestSecurityError:

    def test_default_code(self):
        assert SecurityError("msg").code == "IIOS-SEC-001"

    def test_actor_and_resource(self):
        e = SecurityError("access denied", actor="unknown_client", resource="/api/orders")
        assert e.context["actor"]    == "unknown_client"
        assert e.context["resource"] == "/api/orders"
        assert e.actor    == "unknown_client"
        assert e.resource == "/api/orders"
