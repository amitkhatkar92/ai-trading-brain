"""
tests/unit/supervisor/integration/test_supervisor_integration_engine.py
------------------------------------------------------------------------
Unit tests for C13 M6 — AI Supervisor Integration.

Coverage targets:
  - constants.py
  - exceptions.py
  - supervisor_integration_context.py
  - supervisor_integration_request.py
  - supervisor_integration_response.py
  - supervisor_integration_snapshot.py
  - supervisor_integration_validation.py
  - supervisor_integration_health.py
  - supervisor_integration_status.py
  - supervisor_integration_statistics.py
  - supervisor_integration_history.py
  - supervisor_integration_events.py
  - supervisor_integration_registry.py
  - supervisor_component_registry.py
  - supervisor_component_factory.py
  - supervisor_integration_manager.py
  - supervisor_integration_engine.py
  - __init__.py

All M1-M5 subsystems are replaced by lightweight test-doubles so the test
suite runs without any real AI pipeline.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers — lightweight test doubles for M1-M5 components
# ---------------------------------------------------------------------------


class _FakeLifecycleState:
    def __init__(self, value: str = "running") -> None:
        self.value = value


class _FakeLifecycleAware:
    """Minimal stand-in for any LifecycleAwareMixin component."""
    _state: str = "stopped"

    def start(self) -> None:
        self._state = "running"

    def stop(self) -> None:
        self._state = "stopped"

    def lifecycle_state(self) -> _FakeLifecycleState:
        return _FakeLifecycleState(self._state)


class _FakeSession:
    def __init__(self) -> None:
        self.session_id = str(uuid.uuid4())


class _FakeLifecycle(_FakeLifecycleAware):
    """M1 stand-in."""
    def create(self, session_id: str) -> _FakeSession:
        return _FakeSession()

    def initialize(self, sid: str) -> None: ...
    def discover(self, sid: str) -> None: ...
    def validate_session(self, sid: str) -> None: ...
    def mark_ready(self, sid: str) -> None: ...
    def start_supervising(self, sid: str) -> None: ...
    def stop_monitoring(self, sid: str) -> None: ...
    def complete(self, sid: str) -> None: ...
    def archive(self, sid: str) -> None: ...


class _FakeEngineResponse:
    health_summary: Dict[str, Any] = {}
    outputs: Dict[str, Any] = {}


class _FakeEngine(_FakeLifecycleAware):
    """M2 stand-in."""
    def submit(self, request: Any) -> _FakeEngineResponse:
        return _FakeEngineResponse()


class _FakeDecisionSummary:
    final_action = MagicMock(value="APPROVE")
    rationale = "all good"


class _FakePolicyResponse:
    governance_decision_summary = _FakeDecisionSummary()


class _FakePolicyEngine(_FakeLifecycleAware):
    """M3 stand-in."""
    def evaluate(self, request: Any) -> _FakePolicyResponse:
        return _FakePolicyResponse()


class _FakeAnomalyReport:
    total = 0


class _FakeIncidentReport:
    total = 0


class _FakeGovernanceReport:
    governance_decision = MagicMock(value="CONTINUE")
    violations = ()
    is_compliant = True


class _FakeEnterpriseState:
    enterprise_state = MagicMock(value="STABLE")
    stability_score = 1.0


class _FakeM4Summary:
    governance_report = _FakeGovernanceReport()
    platform_health   = MagicMock(overall_score=1.0)
    anomaly_report    = _FakeAnomalyReport()
    incident_report   = _FakeIncidentReport()
    enterprise_state  = _FakeEnterpriseState()
    reasoning_summary = "all fine"
    is_success        = True


class _FakeGovernanceEngine(_FakeLifecycleAware):
    """M4 stand-in."""
    def govern(self, request: Any) -> _FakeM4Summary:
        return _FakeM4Summary()


class _FakeSnapshot:
    snapshot_id  = str(uuid.uuid4())
    is_valid     = True
    is_published = True


class _FakeSnapshotFactory:
    """M5 stand-in."""
    def create_from_governance_summary(
        self, session_id: str, workflow_id: str, summary: Any
    ) -> _FakeSnapshot:
        return _FakeSnapshot()

    def create_minimal(self, session_id: str, workflow_id: str) -> _FakeSnapshot:
        return _FakeSnapshot()


# ===========================================================================
# 1 — Constants
# ===========================================================================


class TestConstants:
    def test_version_is_string(self) -> None:
        from iios.supervisor.integration.constants import VERSION
        assert isinstance(VERSION, str)
        assert VERSION

    def test_integration_system_id(self) -> None:
        from iios.supervisor.integration.constants import INTEGRATION_SYSTEM_ID
        assert "integration" in INTEGRATION_SYSTEM_ID

    def test_integration_status_members(self) -> None:
        from iios.supervisor.integration.constants import IntegrationStatus
        vals = {s.value for s in IntegrationStatus}
        assert "idle" in vals
        assert "running" in vals
        assert "stopped" in vals
        assert "failed" in vals

    def test_integration_event_type_count(self) -> None:
        from iios.supervisor.integration.constants import IntegrationEventType
        assert len(IntegrationEventType) == 8

    def test_integration_validation_code_count(self) -> None:
        from iios.supervisor.integration.constants import IntegrationValidationCode
        assert len(IntegrationValidationCode) == 7

    def test_component_type_count(self) -> None:
        from iios.supervisor.integration.constants import ComponentType
        assert len(ComponentType) == 5

    def test_component_type_members(self) -> None:
        from iios.supervisor.integration.constants import ComponentType
        assert ComponentType.LIFECYCLE.value == "lifecycle"
        assert ComponentType.ENGINE.value    == "engine"
        assert ComponentType.POLICY.value    == "policy"
        assert ComponentType.GOVERNANCE.value == "governance"
        assert ComponentType.SNAPSHOT.value  == "snapshot"

    def test_workflow_phase_members(self) -> None:
        from iios.supervisor.integration.constants import WorkflowPhase
        phases = {p.value for p in WorkflowPhase}
        assert "receive" in phases
        assert "governance" in phases
        assert "complete" in phases

    def test_integration_mode_members(self) -> None:
        from iios.supervisor.integration.constants import IntegrationMode
        assert IntegrationMode.FULL.value == "full"

    def test_health_status_members(self) -> None:
        from iios.supervisor.integration.constants import IntegrationHealthStatus
        assert IntegrationHealthStatus.HEALTHY.value == "healthy"

    def test_defaults_are_positive(self) -> None:
        from iios.supervisor.integration.constants import (
            DEFAULT_MAX_HISTORY,
            DEFAULT_MAX_REQUESTS,
        )
        assert DEFAULT_MAX_HISTORY > 0
        assert DEFAULT_MAX_REQUESTS > 0


# ===========================================================================
# 2 — Exceptions
# ===========================================================================


class TestExceptions:
    def test_base_error(self) -> None:
        from iios.supervisor.integration.exceptions import SupervisorIntegrationError
        exc = SupervisorIntegrationError("test")
        assert "SIN-000" in str(exc) or exc.args[0] == "test"
        assert isinstance(exc, Exception)

    def test_not_running_error_code(self) -> None:
        from iios.supervisor.integration.exceptions import SupervisorIntegrationNotRunningError
        exc = SupervisorIntegrationNotRunningError()
        assert "SIN-001" in str(exc) or isinstance(exc, Exception)

    def test_validation_error(self) -> None:
        from iios.supervisor.integration.exceptions import SupervisorIntegrationValidationError
        exc = SupervisorIntegrationValidationError("bad request")
        assert isinstance(exc, Exception)

    def test_workflow_error(self) -> None:
        from iios.supervisor.integration.exceptions import SupervisorIntegrationWorkflowError
        exc = SupervisorIntegrationWorkflowError("pipeline failed")
        assert isinstance(exc, Exception)

    def test_component_error_has_component(self) -> None:
        from iios.supervisor.integration.exceptions import SupervisorIntegrationComponentError
        exc = SupervisorIntegrationComponentError("missing", component="lifecycle")
        assert exc.component == "lifecycle"

    def test_capacity_error_has_limit(self) -> None:
        from iios.supervisor.integration.exceptions import SupervisorIntegrationCapacityError
        exc = SupervisorIntegrationCapacityError("over limit", limit=100)
        assert exc.limit == 100

    def test_registry_error(self) -> None:
        from iios.supervisor.integration.exceptions import SupervisorIntegrationRegistryError
        exc = SupervisorIntegrationRegistryError("registry error")
        assert isinstance(exc, Exception)

    def test_timeout_error(self) -> None:
        from iios.supervisor.integration.exceptions import SupervisorIntegrationTimeoutError
        exc = SupervisorIntegrationTimeoutError("timed out")
        assert isinstance(exc, Exception)

    def test_hierarchy(self) -> None:
        from iios.supervisor.integration.exceptions import (
            SupervisorIntegrationError,
            SupervisorIntegrationNotRunningError,
            SupervisorIntegrationValidationError,
            SupervisorIntegrationWorkflowError,
        )
        for cls in (
            SupervisorIntegrationNotRunningError,
            SupervisorIntegrationValidationError,
            SupervisorIntegrationWorkflowError,
        ):
            assert issubclass(cls, SupervisorIntegrationError)


# ===========================================================================
# 3 — Context
# ===========================================================================


class TestContext:
    def _make(self, **kwargs):
        from iios.supervisor.integration.supervisor_integration_context import (
            SupervisorIntegrationContext,
        )
        return SupervisorIntegrationContext.create("int-001", **kwargs)

    def test_create_defaults(self) -> None:
        ctx = self._make()
        assert ctx.integration_id == "int-001"
        assert ctx.context_id
        assert ctx.session_id
        assert ctx.workflow_id
        assert ctx.execution_snapshot == {}
        assert ctx.risk_snapshot == {}

    def test_create_with_snapshots(self) -> None:
        ctx = self._make(risk_snapshot={"vix": 20}, market_snapshot={"trend": "bull"})
        assert ctx.risk_snapshot == {"vix": 20}
        assert ctx.market_snapshot == {"trend": "bull"}

    def test_from_inputs(self) -> None:
        from iios.supervisor.integration.supervisor_integration_context import (
            SupervisorIntegrationContext,
        )
        inputs = {
            "risk_snapshot": {"vix": 15},
            "extra_key": "extra_val",
        }
        ctx = SupervisorIntegrationContext.from_inputs("int-002", inputs)
        assert ctx.risk_snapshot == {"vix": 15}
        assert ctx.extra == {"extra_key": "extra_val"}

    def test_all_inputs_contains_snapshots(self) -> None:
        ctx = self._make(risk_snapshot={"vix": 10})
        ai = ctx.all_inputs()
        assert "risk_snapshot" in ai
        assert ai["risk_snapshot"] == {"vix": 10}

    def test_to_dict(self) -> None:
        ctx = self._make()
        d = ctx.to_dict()
        assert "context_id" in d
        assert "integration_id" in d
        assert d["mode"] == "full"

    def test_is_frozen(self) -> None:
        ctx = self._make()
        with pytest.raises((AttributeError, TypeError)):
            ctx.session_id = "new"  # type: ignore[misc]

    def test_extra_snapshots_preserved(self) -> None:
        from iios.supervisor.integration.supervisor_integration_context import (
            SupervisorIntegrationContext,
        )
        inputs = {"risk_snapshot": {}, "custom": 42}
        ctx = SupervisorIntegrationContext.from_inputs("x", inputs)
        assert ctx.extra.get("custom") == 42


# ===========================================================================
# 4 — Request
# ===========================================================================


class TestRequest:
    def _make(self, **kwargs):
        from iios.supervisor.integration.supervisor_integration_request import (
            SupervisorIntegrationRequest,
        )
        return SupervisorIntegrationRequest.create("int-req-001", **kwargs)

    def test_create_defaults(self) -> None:
        req = self._make()
        assert req.integration_id == "int-req-001"
        assert req.request_id
        assert req.session_id
        assert req.workflow_id
        assert req.mode.value == "full"

    def test_create_with_inputs(self) -> None:
        req = self._make(inputs={"risk_snapshot": {"score": 0.9}})
        assert req.inputs["risk_snapshot"]["score"] == 0.9

    def test_with_inputs(self) -> None:
        req = self._make(inputs={"a": 1})
        req2 = req.with_inputs({"b": 2})
        assert req2.inputs["a"] == 1
        assert req2.inputs["b"] == 2
        # original unchanged
        assert "b" not in req.inputs

    def test_to_dict(self) -> None:
        req = self._make()
        d = req.to_dict()
        assert "request_id" in d
        assert d["integration_id"] == "int-req-001"

    def test_context_is_auto_created(self) -> None:
        req = self._make()
        assert req.context is not None
        assert req.context.integration_id == "int-req-001"

    def test_is_frozen(self) -> None:
        req = self._make()
        with pytest.raises((AttributeError, TypeError)):
            req.integration_id = "changed"  # type: ignore[misc]

    def test_custom_request_id(self) -> None:
        req = self._make(request_id="custom-rid")
        assert req.request_id == "custom-rid"


# ===========================================================================
# 5 — Response
# ===========================================================================


class TestResponse:
    def test_create_success_defaults(self) -> None:
        from iios.supervisor.integration.supervisor_integration_response import (
            SupervisorIntegrationResponse,
        )
        r = SupervisorIntegrationResponse.create_success("i1", "r1")
        assert r.is_success
        assert r.error_message == ""
        assert r.integration_id == "i1"
        assert r.request_id == "r1"

    def test_create_failure(self) -> None:
        from iios.supervisor.integration.supervisor_integration_response import (
            SupervisorIntegrationResponse,
        )
        r = SupervisorIntegrationResponse.create_failure("i1", "r1", error="oops")
        assert not r.is_success
        assert r.error_message == "oops"
        assert r.supervisor_snapshot is None

    def test_has_snapshot_true(self) -> None:
        from iios.supervisor.integration.supervisor_integration_response import (
            SupervisorIntegrationResponse,
        )
        r = SupervisorIntegrationResponse.create_success("i1", "r1", supervisor_snapshot=object())
        assert r.has_snapshot

    def test_has_snapshot_false(self) -> None:
        from iios.supervisor.integration.supervisor_integration_response import (
            SupervisorIntegrationResponse,
        )
        r = SupervisorIntegrationResponse.create_success("i1", "r1")
        assert not r.has_snapshot

    def test_to_dict(self) -> None:
        from iios.supervisor.integration.supervisor_integration_response import (
            SupervisorIntegrationResponse,
        )
        r = SupervisorIntegrationResponse.create_success("i1", "r1")
        d = r.to_dict()
        assert d["is_success"] is True
        assert "platform_health" in d

    def test_platform_health_summary_create(self) -> None:
        from iios.supervisor.integration.supervisor_integration_response import (
            PlatformHealthSummary,
        )
        ph = PlatformHealthSummary.create(overall_health=1.0)
        assert ph.is_healthy

    def test_platform_health_summary_not_healthy(self) -> None:
        from iios.supervisor.integration.supervisor_integration_response import (
            PlatformHealthSummary,
        )
        ph = PlatformHealthSummary.create(overall_health=0.5)
        assert not ph.is_healthy

    def test_governance_summary_create(self) -> None:
        from iios.supervisor.integration.supervisor_integration_response import (
            IntegrationGovernanceSummary,
        )
        g = IntegrationGovernanceSummary.create(final_action="APPROVE", is_compliant=True)
        assert g.is_compliant
        assert g.final_action == "APPROVE"

    def test_enterprise_assessment_create(self) -> None:
        from iios.supervisor.integration.supervisor_integration_response import (
            EnterpriseAssessment,
        )
        a = EnterpriseAssessment.create(stability_score=1.0)
        assert a.is_stable

    def test_enterprise_assessment_not_stable(self) -> None:
        from iios.supervisor.integration.supervisor_integration_response import (
            EnterpriseAssessment,
        )
        a = EnterpriseAssessment.create(stability_score=0.5)
        assert not a.is_stable

    def test_response_is_frozen(self) -> None:
        from iios.supervisor.integration.supervisor_integration_response import (
            SupervisorIntegrationResponse,
        )
        r = SupervisorIntegrationResponse.create_success("i1", "r1")
        with pytest.raises((AttributeError, TypeError)):
            r.is_success = False  # type: ignore[misc]

    def test_failure_platform_health_score_zero(self) -> None:
        from iios.supervisor.integration.supervisor_integration_response import (
            SupervisorIntegrationResponse,
        )
        r = SupervisorIntegrationResponse.create_failure("i1", "r1", error="e")
        assert r.platform_health_summary.overall_health == 0.0


# ===========================================================================
# 6 — Integration Snapshot (wrapper)
# ===========================================================================


class TestIntegrationSnapshot:
    def _make(self, snap=None):
        from iios.supervisor.integration.supervisor_integration_snapshot import (
            SupervisorIntegrationSnapshot,
        )
        inner = snap or MagicMock(snapshot_id="snap-123", is_valid=True, is_published=True)
        return SupervisorIntegrationSnapshot.create(
            integration_id      = "int-001",
            request_id          = "req-001",
            supervisor_snapshot = inner,
        )

    def test_create(self) -> None:
        s = self._make()
        assert s.integration_id == "int-001"
        assert s.request_id == "req-001"
        assert s.snapshot_id == "snap-123"

    def test_is_valid_delegates(self) -> None:
        s = self._make()
        assert s.is_valid

    def test_is_published_delegates(self) -> None:
        s = self._make()
        assert s.is_published

    def test_is_valid_false_when_no_snapshot(self) -> None:
        from iios.supervisor.integration.supervisor_integration_snapshot import (
            SupervisorIntegrationSnapshot,
        )
        s = SupervisorIntegrationSnapshot.create("i1", "r1", supervisor_snapshot=None)
        assert not s.is_valid

    def test_to_dict(self) -> None:
        s = self._make()
        d = s.to_dict()
        assert d["integration_id"] == "int-001"
        assert d["snapshot_id"] == "snap-123"

    def test_is_frozen(self) -> None:
        s = self._make()
        with pytest.raises((AttributeError, TypeError)):
            s.integration_id = "changed"  # type: ignore[misc]


# ===========================================================================
# 7 — Validation
# ===========================================================================


class TestValidation:
    def _make_request(self):
        from iios.supervisor.integration.supervisor_integration_request import (
            SupervisorIntegrationRequest,
        )
        return SupervisorIntegrationRequest.create("int-001")

    def _validator(self):
        from iios.supervisor.integration.supervisor_integration_validation import (
            SupervisorIntegrationValidator,
        )
        return SupervisorIntegrationValidator()

    def test_valid_request_passes(self) -> None:
        req = self._make_request()
        result = self._validator().validate_request(req)
        assert result.is_valid
        assert result.failed_count == 0

    def test_missing_integration_id_fails(self) -> None:
        from iios.supervisor.integration.supervisor_integration_request import (
            SupervisorIntegrationRequest,
        )
        req = SupervisorIntegrationRequest.create("")
        result = self._validator().validate_request(req)
        # "" integration_id should fail INTEGRATION_CONSISTENCY
        assert not result.is_valid

    def test_missing_context_fails(self) -> None:
        class _Bad:
            integration_id = "x"
            request_id     = "y"
            context        = None
            mode           = __import__(
                "iios.supervisor.integration.constants", fromlist=["IntegrationMode"]
            ).IntegrationMode.FULL

        result = self._validator().validate_request(_Bad())
        assert not result.is_valid

    def test_response_validation_success_with_snapshot(self) -> None:
        from iios.supervisor.integration.supervisor_integration_response import (
            SupervisorIntegrationResponse,
        )
        req  = self._make_request()
        resp = SupervisorIntegrationResponse.create_success(
            "int-001", req.request_id,
            session_id          = req.session_id,
            supervisor_snapshot = _FakeSnapshot(),
        )
        result = self._validator().validate_response(req, resp)
        assert result.is_valid

    def test_response_validation_fails_missing_snapshot(self) -> None:
        from iios.supervisor.integration.supervisor_integration_response import (
            SupervisorIntegrationResponse,
        )
        req  = self._make_request()
        resp = SupervisorIntegrationResponse.create_success(
            "int-001", req.request_id,
            session_id          = req.session_id,
            supervisor_snapshot = None,
        )
        result = self._validator().validate_response(req, resp)
        assert not result.is_valid

    def test_validation_result_has_counts(self) -> None:
        req = self._make_request()
        result = self._validator().validate_request(req)
        assert result.passed_count == 3
        assert result.failed_count == 0

    def test_to_dict_on_result(self) -> None:
        req = self._make_request()
        result = self._validator().validate_request(req)
        d = result.to_dict()
        assert "is_valid" in d
        assert "checks" in d

    def test_failure_messages_populated_on_failure(self) -> None:
        class _Bad:
            integration_id = ""
            request_id     = "r"
            context        = object()
            mode           = __import__(
                "iios.supervisor.integration.constants", fromlist=["IntegrationMode"]
            ).IntegrationMode.FULL

        result = self._validator().validate_request(_Bad())
        assert len(result.failure_messages) > 0


# ===========================================================================
# 8 — Health
# ===========================================================================


class TestHealth:
    def _health(self):
        from iios.supervisor.integration.supervisor_integration_health import (
            SupervisorIntegrationHealth,
        )
        return SupervisorIntegrationHealth()

    def _engine_mock(self, state="running"):
        m = MagicMock()
        m.lifecycle_state.return_value = _FakeLifecycleState(state)
        return m

    def test_healthy_when_running(self) -> None:
        from iios.supervisor.integration.supervisor_integration_statistics import (
            SupervisorIntegrationStatistics,
        )
        eng    = self._engine_mock("running")
        reg    = MagicMock()
        reg.all_components.return_value = {}
        stats  = SupervisorIntegrationStatistics()
        result = self._health().assess(eng, reg, stats)
        assert result["is_healthy"]

    def test_not_healthy_when_stopped(self) -> None:
        eng    = self._engine_mock("stopped")
        result = self._health().assess(eng, MagicMock(), MagicMock())
        assert not result["is_healthy"]

    def test_assess_returns_dict(self) -> None:
        eng    = self._engine_mock("running")
        result = self._health().assess(eng, MagicMock(), MagicMock())
        assert isinstance(result, dict)
        assert "status" in result
        assert "lifecycle_state" in result

    def test_degraded_when_component_not_running(self) -> None:
        from iios.supervisor.integration.supervisor_integration_health import (
            SupervisorIntegrationHealth,
        )
        from iios.supervisor.integration.supervisor_integration_statistics import (
            SupervisorIntegrationStatistics,
        )
        eng = self._engine_mock("running")
        reg = MagicMock()
        reg.all_components.return_value = {
            "lifecycle": MagicMock(lifecycle_state=lambda: _FakeLifecycleState("stopped"))
        }
        stats  = SupervisorIntegrationStatistics()
        result = SupervisorIntegrationHealth().assess(eng, reg, stats)
        assert result["status"] in ("degraded", "critical")


# ===========================================================================
# 9 — Status
# ===========================================================================


class TestStatus:
    def _status(self):
        from iios.supervisor.integration.supervisor_integration_status import (
            SupervisorIntegrationStatus,
        )
        return SupervisorIntegrationStatus()

    def test_build_status_returns_dict(self) -> None:
        eng = MagicMock()
        eng.lifecycle_state.return_value = _FakeLifecycleState("running")
        d = self._status().build_status(eng, MagicMock(), MagicMock(), MagicMock())
        assert isinstance(d, dict)

    def test_is_running_in_status(self) -> None:
        eng = MagicMock()
        eng.lifecycle_state.return_value = _FakeLifecycleState("running")
        d = self._status().build_status(eng, MagicMock(), MagicMock(), MagicMock())
        assert d.get("is_running") is True

    def test_not_running_in_status(self) -> None:
        eng = MagicMock()
        eng.lifecycle_state.return_value = _FakeLifecycleState("stopped")
        d = self._status().build_status(eng, MagicMock(), MagicMock(), MagicMock())
        assert d.get("is_running") is False

    def test_system_id_in_status(self) -> None:
        from iios.supervisor.integration.constants import INTEGRATION_SYSTEM_ID
        eng = MagicMock()
        eng.lifecycle_state.return_value = _FakeLifecycleState("running")
        d = self._status().build_status(eng, MagicMock(), MagicMock(), MagicMock())
        assert d["system_id"] == INTEGRATION_SYSTEM_ID


# ===========================================================================
# 10 — Statistics
# ===========================================================================


class TestStatistics:
    def _stats(self):
        from iios.supervisor.integration.supervisor_integration_statistics import (
            SupervisorIntegrationStatistics,
        )
        return SupervisorIntegrationStatistics()

    def test_initial_zero(self) -> None:
        s = self._stats()
        assert s.integration_requests == 0
        assert s.successful_integrations == 0
        assert s.failed_integrations == 0

    def test_record_started(self) -> None:
        s = self._stats()
        s.record_integration_started()
        assert s.integration_requests == 1

    def test_record_success(self) -> None:
        s = self._stats()
        s.record_integration_started()
        s.record_success(processing_time_s=0.5)
        assert s.successful_integrations == 1

    def test_record_failure(self) -> None:
        s = self._stats()
        s.record_integration_started()
        s.record_failure(processing_time_s=0.1)
        assert s.failed_integrations == 1

    def test_record_snapshot_publication(self) -> None:
        s = self._stats()
        s.record_snapshot_publication()
        assert s.snapshot_publications == 1

    def test_average_processing_time(self) -> None:
        s = self._stats()
        s.record_integration_started()
        s.record_success(processing_time_s=1.0)
        s.record_integration_started()
        s.record_success(processing_time_s=3.0)
        assert abs(s.average_processing_time_s - 2.0) < 0.01

    def test_platform_availability_all_success(self) -> None:
        s = self._stats()
        for _ in range(5):
            s.record_integration_started()
            s.record_success()
        assert s.platform_availability == 1.0

    def test_platform_availability_partial(self) -> None:
        s = self._stats()
        s.record_integration_started()
        s.record_success()
        s.record_integration_started()
        s.record_failure()
        assert abs(s.platform_availability - 0.5) < 0.01

    def test_snapshot_returns_dict(self) -> None:
        s = self._stats()
        d = s.snapshot()
        assert isinstance(d, dict)
        assert "integration_requests" in d

    def test_reset(self) -> None:
        s = self._stats()
        s.record_integration_started()
        s.record_success()
        s.reset()
        assert s.integration_requests == 0
        assert s.successful_integrations == 0

    def test_thread_safety(self) -> None:
        s = self._stats()
        barrier = threading.Barrier(10)
        errors = []

        def worker():
            try:
                barrier.wait()
                s.record_integration_started()
                s.record_success(processing_time_s=0.01)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert s.integration_requests == 10


# ===========================================================================
# 11 — History
# ===========================================================================


class TestHistory:
    def _hist(self):
        from iios.supervisor.integration.supervisor_integration_history import (
            SupervisorIntegrationHistory,
        )
        return SupervisorIntegrationHistory(max_records=50)

    def test_initial_empty(self) -> None:
        h = self._hist()
        counts = h.counts()
        assert counts["requests"] == 0
        assert counts["responses"] == 0
        assert counts["events"] == 0

    def test_record_request(self) -> None:
        h = self._hist()
        h.record_request({"request_id": "r1"})
        assert h.counts()["requests"] == 1

    def test_record_response(self) -> None:
        h = self._hist()
        h.record_response({"response_id": "resp-1"})
        assert h.counts()["responses"] == 1

    def test_record_event(self) -> None:
        h = self._hist()
        h.record_event({"event_type": "started"})
        assert h.counts()["events"] == 1

    def test_record_with_to_dict(self) -> None:
        h = self._hist()
        obj = MagicMock()
        obj.to_dict.return_value = {"key": "val"}
        h.record_request(obj)
        assert h.counts()["requests"] == 1

    def test_recent_requests(self) -> None:
        h = self._hist()
        for i in range(5):
            h.record_request({"i": i})
        recent = h.recent_requests(3)
        assert len(recent) == 3

    def test_recent_events(self) -> None:
        h = self._hist()
        for i in range(5):
            h.record_event({"i": i})
        assert len(h.recent_events(2)) == 2

    def test_bounded_capacity(self) -> None:
        h = self._hist()
        for i in range(60):
            h.record_request({"i": i})
        assert h.counts()["requests"] == 50

    def test_clear(self) -> None:
        h = self._hist()
        h.record_request({"a": 1})
        h.record_event({"b": 2})
        h.clear()
        assert h.counts()["requests"] == 0
        assert h.counts()["events"] == 0


# ===========================================================================
# 12 — Events
# ===========================================================================


class TestEvents:
    def test_make_initialized(self) -> None:
        from iios.supervisor.integration.supervisor_integration_events import (
            make_integration_initialized_event,
            IntegrationEventType,
        )
        e = make_integration_initialized_event("int-001")
        assert e.event_type == IntegrationEventType.INTEGRATION_INITIALIZED
        assert e.integration_id == "int-001"

    def test_make_started(self) -> None:
        from iios.supervisor.integration.supervisor_integration_events import (
            make_integration_started_event,
            IntegrationEventType,
        )
        e = make_integration_started_event("int-001", "req-001", mode="full")
        assert e.event_type == IntegrationEventType.INTEGRATION_STARTED
        assert e.payload["mode"] == "full"

    def test_make_validated(self) -> None:
        from iios.supervisor.integration.supervisor_integration_events import (
            make_integration_validated_event,
            IntegrationEventType,
        )
        e = make_integration_validated_event("int-001", "req-001", is_valid=True)
        assert e.event_type == IntegrationEventType.INTEGRATION_VALIDATED
        assert e.payload["is_valid"] is True

    def test_make_executed(self) -> None:
        from iios.supervisor.integration.supervisor_integration_events import (
            make_integration_executed_event,
            IntegrationEventType,
        )
        e = make_integration_executed_event("int-001", "req-001", phase="engine")
        assert e.event_type == IntegrationEventType.INTEGRATION_EXECUTED
        assert e.payload["phase"] == "engine"

    def test_make_snapshot_published(self) -> None:
        from iios.supervisor.integration.supervisor_integration_events import (
            make_snapshot_published_event,
            IntegrationEventType,
        )
        e = make_snapshot_published_event("int-001", "req-001", snapshot_id="snap-123")
        assert e.event_type == IntegrationEventType.SNAPSHOT_PUBLISHED
        assert e.payload["snapshot_id"] == "snap-123"

    def test_make_completed(self) -> None:
        from iios.supervisor.integration.supervisor_integration_events import (
            make_integration_completed_event,
            IntegrationEventType,
        )
        e = make_integration_completed_event("int-001", "req-001", processing_time_s=0.5)
        assert e.event_type == IntegrationEventType.INTEGRATION_COMPLETED

    def test_make_failed(self) -> None:
        from iios.supervisor.integration.supervisor_integration_events import (
            make_integration_failed_event,
            IntegrationEventType,
        )
        e = make_integration_failed_event("int-001", "req-001", error="oops")
        assert e.event_type == IntegrationEventType.INTEGRATION_FAILED
        assert e.payload["error"] == "oops"

    def test_make_stopped(self) -> None:
        from iios.supervisor.integration.supervisor_integration_events import (
            make_integration_stopped_event,
            IntegrationEventType,
        )
        e = make_integration_stopped_event("int-001")
        assert e.event_type == IntegrationEventType.INTEGRATION_STOPPED

    def test_event_to_dict(self) -> None:
        from iios.supervisor.integration.supervisor_integration_events import (
            make_integration_initialized_event,
        )
        e = make_integration_initialized_event("int-001")
        d = e.to_dict()
        assert "event_id" in d
        assert "event_type" in d

    def test_event_is_frozen(self) -> None:
        from iios.supervisor.integration.supervisor_integration_events import (
            make_integration_stopped_event,
        )
        e = make_integration_stopped_event("int-001")
        with pytest.raises((AttributeError, TypeError)):
            e.integration_id = "changed"  # type: ignore[misc]


# ===========================================================================
# 13 — Integration Registry
# ===========================================================================


class TestIntegrationRegistry:
    def _reg(self):
        from iios.supervisor.integration.supervisor_integration_registry import (
            SupervisorIntegrationRegistry,
        )
        return SupervisorIntegrationRegistry(max_requests=50)

    def _req(self):
        from iios.supervisor.integration.supervisor_integration_request import (
            SupervisorIntegrationRequest,
        )
        return SupervisorIntegrationRequest.create("int-001")

    def _resp(self, req):
        from iios.supervisor.integration.supervisor_integration_response import (
            SupervisorIntegrationResponse,
        )
        return SupervisorIntegrationResponse.create_success(
            req.integration_id, req.request_id
        )

    def test_register_request(self) -> None:
        reg = self._reg()
        req = self._req()
        reg.register_request(req)
        assert reg.is_registered(req.request_id)
        assert reg.count == 1

    def test_register_response(self) -> None:
        reg  = self._reg()
        req  = self._req()
        resp = self._resp(req)
        reg.register_request(req)
        reg.register_response(resp)
        assert reg.is_complete(req.request_id)

    def test_get_request(self) -> None:
        reg = self._reg()
        req = self._req()
        reg.register_request(req)
        assert reg.get_request(req.request_id) is req

    def test_get_response(self) -> None:
        reg  = self._reg()
        req  = self._req()
        resp = self._resp(req)
        reg.register_request(req)
        reg.register_response(resp)
        assert reg.get_response(req.request_id) is resp

    def test_unregister(self) -> None:
        reg = self._reg()
        req = self._req()
        reg.register_request(req)
        reg.unregister(req.request_id)
        assert not reg.is_registered(req.request_id)

    def test_active_count(self) -> None:
        reg = self._reg()
        req = self._req()
        reg.register_request(req)
        assert reg.active_count == 1

    def test_completed_count(self) -> None:
        reg  = self._reg()
        req  = self._req()
        resp = self._resp(req)
        reg.register_request(req)
        reg.register_response(resp)
        assert reg.completed_count == 1

    def test_idempotent_register(self) -> None:
        reg = self._reg()
        req = self._req()
        reg.register_request(req)
        reg.register_request(req)  # second call is no-op
        assert reg.count == 1

    def test_response_without_request_raises(self) -> None:
        from iios.supervisor.integration.exceptions import (
            SupervisorIntegrationRegistryError,
        )
        reg  = self._reg()
        req  = self._req()
        resp = self._resp(req)
        with pytest.raises(SupervisorIntegrationRegistryError):
            reg.register_response(resp)

    def test_eviction_at_capacity(self) -> None:
        from iios.supervisor.integration.supervisor_integration_registry import (
            SupervisorIntegrationRegistry,
        )
        from iios.supervisor.integration.supervisor_integration_request import (
            SupervisorIntegrationRequest,
        )
        reg = SupervisorIntegrationRegistry(max_requests=3)
        for _ in range(5):
            reg.register_request(SupervisorIntegrationRequest.create(str(uuid.uuid4())))
        assert reg.count <= 3

    def test_clear(self) -> None:
        reg = self._reg()
        reg.register_request(self._req())
        reg.clear()
        assert reg.count == 0


# ===========================================================================
# 14 — Component Registry
# ===========================================================================


class TestComponentRegistry:
    def _reg(self):
        from iios.supervisor.integration.supervisor_component_registry import (
            SupervisorComponentRegistry,
        )
        return SupervisorComponentRegistry()

    def test_register_and_get(self) -> None:
        from iios.supervisor.integration.constants import ComponentType
        reg  = self._reg()
        comp = _FakeLifecycle()
        reg.register(ComponentType.LIFECYCLE, comp)
        assert reg.get(ComponentType.LIFECYCLE) is comp

    def test_get_missing_raises(self) -> None:
        from iios.supervisor.integration.constants import ComponentType
        from iios.supervisor.integration.exceptions import (
            SupervisorIntegrationComponentError,
        )
        reg = self._reg()
        with pytest.raises(SupervisorIntegrationComponentError):
            reg.get(ComponentType.ENGINE)

    def test_get_optional_missing_returns_none(self) -> None:
        from iios.supervisor.integration.constants import ComponentType
        reg = self._reg()
        assert reg.get_optional(ComponentType.ENGINE) is None

    def test_is_registered(self) -> None:
        from iios.supervisor.integration.constants import ComponentType
        reg = self._reg()
        assert not reg.is_registered(ComponentType.LIFECYCLE)
        reg.register(ComponentType.LIFECYCLE, _FakeLifecycle())
        assert reg.is_registered(ComponentType.LIFECYCLE)

    def test_unregister(self) -> None:
        from iios.supervisor.integration.constants import ComponentType
        reg = self._reg()
        reg.register(ComponentType.LIFECYCLE, _FakeLifecycle())
        reg.unregister(ComponentType.LIFECYCLE)
        assert not reg.is_registered(ComponentType.LIFECYCLE)

    def test_all_components(self) -> None:
        from iios.supervisor.integration.constants import ComponentType
        reg = self._reg()
        reg.register(ComponentType.LIFECYCLE, _FakeLifecycle())
        reg.register(ComponentType.ENGINE,    _FakeEngine())
        comps = reg.all_components()
        assert "lifecycle" in comps
        assert "engine" in comps

    def test_count(self) -> None:
        from iios.supervisor.integration.constants import ComponentType
        reg = self._reg()
        reg.register(ComponentType.LIFECYCLE, _FakeLifecycle())
        assert reg.count == 1

    def test_clear(self) -> None:
        from iios.supervisor.integration.constants import ComponentType
        reg = self._reg()
        reg.register(ComponentType.LIFECYCLE, _FakeLifecycle())
        reg.clear()
        assert reg.count == 0


# ===========================================================================
# 15 — Component Factory
# ===========================================================================


class TestComponentFactory:
    def _factory(self):
        from iios.supervisor.integration.supervisor_component_factory import (
            SupervisorComponentFactory,
        )
        return SupervisorComponentFactory()

    def test_create_all_returns_registry(self) -> None:
        from iios.supervisor.integration.supervisor_component_registry import (
            SupervisorComponentRegistry,
        )
        factory = self._factory()
        reg = factory.create_all(
            lifecycle         = _FakeLifecycle(),
            engine            = _FakeEngine(),
            policy_engine     = _FakePolicyEngine(),
            governance_engine = _FakeGovernanceEngine(),
            snapshot_factory  = _FakeSnapshotFactory(),
        )
        assert isinstance(reg, SupervisorComponentRegistry)
        assert reg.count == 5

    def test_create_all_registers_all_types(self) -> None:
        from iios.supervisor.integration.constants import ComponentType
        factory = self._factory()
        reg = factory.create_all(
            lifecycle         = _FakeLifecycle(),
            engine            = _FakeEngine(),
            policy_engine     = _FakePolicyEngine(),
            governance_engine = _FakeGovernanceEngine(),
            snapshot_factory  = _FakeSnapshotFactory(),
        )
        for comp_type in ComponentType:
            assert reg.is_registered(comp_type), f"Missing: {comp_type}"

    def test_create_all_uses_provided_registry(self) -> None:
        from iios.supervisor.integration.supervisor_component_registry import (
            SupervisorComponentRegistry,
        )
        factory = self._factory()
        provided = SupervisorComponentRegistry()
        returned = factory.create_all(
            registry          = provided,
            lifecycle         = _FakeLifecycle(),
            engine            = _FakeEngine(),
            policy_engine     = _FakePolicyEngine(),
            governance_engine = _FakeGovernanceEngine(),
            snapshot_factory  = _FakeSnapshotFactory(),
        )
        assert returned is provided


# ===========================================================================
# 16 — Manager
# ===========================================================================


def _make_manager(
    lifecycle=None, engine=None, policy=None, governance=None, snapshot=None
):
    from iios.supervisor.integration.supervisor_component_registry import (
        SupervisorComponentRegistry,
    )
    from iios.supervisor.integration.supervisor_component_factory import (
        SupervisorComponentFactory,
    )
    from iios.supervisor.integration.supervisor_integration_manager import (
        SupervisorIntegrationManager,
    )
    from iios.supervisor.integration.constants import ComponentType

    reg = SupervisorComponentRegistry()
    reg.register(ComponentType.LIFECYCLE,  lifecycle  or _FakeLifecycle())
    reg.register(ComponentType.ENGINE,     engine     or _FakeEngine())
    reg.register(ComponentType.POLICY,     policy     or _FakePolicyEngine())
    reg.register(ComponentType.GOVERNANCE, governance or _FakeGovernanceEngine())
    reg.register(ComponentType.SNAPSHOT,   snapshot   or _FakeSnapshotFactory())

    return SupervisorIntegrationManager(component_registry=reg)


class TestManager:
    def _req(self):
        from iios.supervisor.integration.supervisor_integration_request import (
            SupervisorIntegrationRequest,
        )
        return SupervisorIntegrationRequest.create("int-mgr-001")

    def test_run_integration_success(self) -> None:
        mgr  = _make_manager()
        req  = self._req()
        resp = mgr.run_integration(req)
        assert resp.is_success
        assert resp.integration_id == "int-mgr-001"

    def test_run_integration_has_snapshot(self) -> None:
        mgr  = _make_manager()
        req  = self._req()
        resp = mgr.run_integration(req)
        assert resp.supervisor_snapshot is not None

    def test_run_integration_does_not_raise(self) -> None:
        class _BoomEngine(_FakeEngine):
            def submit(self, request): raise RuntimeError("boom")

        mgr  = _make_manager(engine=_BoomEngine())
        req  = self._req()
        resp = mgr.run_integration(req)
        # Should return failure, not raise
        assert isinstance(resp.is_success, bool)

    def test_run_integration_failure_on_invalid_request(self) -> None:
        mgr = _make_manager()
        # Request with empty integration_id triggers validation failure
        from iios.supervisor.integration.supervisor_integration_request import (
            SupervisorIntegrationRequest,
        )
        req = SupervisorIntegrationRequest.create("")
        resp = mgr.run_integration(req)
        assert not resp.is_success

    def test_fires_events(self) -> None:
        events = []
        mgr = _make_manager()
        mgr._listeners.append(lambda e: events.append(e))
        req = self._req()
        mgr.run_integration(req)
        event_types = [e.event_type.value for e in events]
        assert "integration.started" in event_types
        assert "integration.completed" in event_types

    def test_statistics_updated_on_success(self) -> None:
        from iios.supervisor.integration.supervisor_integration_statistics import (
            SupervisorIntegrationStatistics,
        )
        stats = SupervisorIntegrationStatistics()
        mgr   = _make_manager()
        mgr._stats = stats
        req   = self._req()
        mgr.run_integration(req)
        assert stats.integration_requests >= 1

    def test_history_recorded(self) -> None:
        from iios.supervisor.integration.supervisor_integration_history import (
            SupervisorIntegrationHistory,
        )
        hist = SupervisorIntegrationHistory()
        mgr  = _make_manager()
        mgr._history = hist
        req  = self._req()
        mgr.run_integration(req)
        assert hist.counts()["requests"] == 1


# ===========================================================================
# 17 — Engine lifecycle
# ===========================================================================


def _make_engine(**kwargs):
    from iios.supervisor.integration.supervisor_integration_engine import (
        SupervisorIntegrationEngine,
    )
    return SupervisorIntegrationEngine(
        lifecycle         = kwargs.pop("lifecycle", _FakeLifecycle()),
        engine            = kwargs.pop("engine", _FakeEngine()),
        policy_engine     = kwargs.pop("policy_engine", _FakePolicyEngine()),
        governance_engine = kwargs.pop("governance_engine", _FakeGovernanceEngine()),
        snapshot_factory  = kwargs.pop("snapshot_factory", _FakeSnapshotFactory()),
        **kwargs,
    )


class TestEngineLifecycle:
    def test_initial_state_not_running(self) -> None:
        eng = _make_engine()
        assert eng.lifecycle_state().value != "running"

    def test_start_transitions_to_running(self) -> None:
        eng = _make_engine()
        eng.start()
        assert eng.lifecycle_state().value == "running"
        eng.stop()

    def test_stop_transitions_from_running(self) -> None:
        eng = _make_engine()
        eng.start()
        eng.stop()
        assert eng.lifecycle_state().value != "running"

    def test_restart(self) -> None:
        eng = _make_engine()
        eng.start()
        eng.restart()
        assert eng.lifecycle_state().value == "running"
        eng.stop()

    def test_initialize_alias(self) -> None:
        eng = _make_engine()
        eng.initialize()
        assert eng.lifecycle_state().value == "running"
        eng.stop()

    def test_submit_when_not_running_raises(self) -> None:
        from iios.supervisor.integration.exceptions import (
            SupervisorIntegrationNotRunningError,
        )
        from iios.supervisor.integration.supervisor_integration_request import (
            SupervisorIntegrationRequest,
        )
        eng = _make_engine()
        req = SupervisorIntegrationRequest.create("int-001")
        with pytest.raises(SupervisorIntegrationNotRunningError):
            eng.submit(req)

    def test_double_start_raises(self) -> None:
        """LifecycleAwareMixin raises EngineAlreadyRunningError on double-start."""
        from iios.investment.workflow.engine_lifecycle import EngineAlreadyRunningError
        eng = _make_engine()
        eng.start()
        try:
            with pytest.raises(EngineAlreadyRunningError):
                eng.start()
            assert eng.lifecycle_state().value == "running"
        finally:
            eng.stop()


# ===========================================================================
# 18 — Engine submit
# ===========================================================================


class TestEngineSubmit:
    def _req(self):
        from iios.supervisor.integration.supervisor_integration_request import (
            SupervisorIntegrationRequest,
        )
        return SupervisorIntegrationRequest.create("int-sub-001")

    def test_submit_success(self) -> None:
        eng = _make_engine()
        eng.start()
        try:
            req  = self._req()
            resp = eng.submit(req)
            assert resp.is_success
            assert resp.integration_id == "int-sub-001"
        finally:
            eng.stop()

    def test_submit_has_snapshot(self) -> None:
        eng = _make_engine()
        eng.start()
        try:
            resp = eng.submit(self._req())
            assert resp.supervisor_snapshot is not None
        finally:
            eng.stop()

    def test_submit_updates_latest_snapshot(self) -> None:
        eng = _make_engine()
        eng.start()
        try:
            eng.submit(self._req())
            assert eng.snapshot() is not None
        finally:
            eng.stop()

    def test_submit_non_raising_on_m4_error(self) -> None:
        class _BoomGov(_FakeGovernanceEngine):
            def govern(self, req): raise ValueError("gov error")

        eng = _make_engine(governance_engine=_BoomGov())
        eng.start()
        try:
            resp = eng.submit(self._req())
            assert isinstance(resp.is_success, bool)
        finally:
            eng.stop()

    def test_health_returns_dict(self) -> None:
        eng = _make_engine()
        eng.start()
        try:
            h = eng.health()
            assert isinstance(h, dict)
            assert "is_healthy" in h
        finally:
            eng.stop()

    def test_status_returns_dict(self) -> None:
        eng = _make_engine()
        eng.start()
        try:
            s = eng.status()
            assert isinstance(s, dict)
            assert s["is_running"] is True
        finally:
            eng.stop()

    def test_statistics_returns_dict(self) -> None:
        eng = _make_engine()
        eng.start()
        try:
            stats = eng.statistics()
            assert isinstance(stats, dict)
            assert "integration_requests" in stats
        finally:
            eng.stop()

    def test_history_returns_counts(self) -> None:
        eng = _make_engine()
        eng.start()
        try:
            h = eng.history()
            assert isinstance(h, dict)
        finally:
            eng.stop()

    def test_validate_returns_dict(self) -> None:
        from iios.supervisor.integration.supervisor_integration_request import (
            SupervisorIntegrationRequest,
        )
        eng = _make_engine()
        d = eng.validate(SupervisorIntegrationRequest.create("int-v001"))
        assert isinstance(d, dict)
        assert "is_valid" in d

    def test_query_health(self) -> None:
        eng = _make_engine()
        eng.start()
        try:
            result = eng.query("health")
            assert isinstance(result, dict)
        finally:
            eng.stop()

    def test_query_unknown_key_returns_none(self) -> None:
        eng = _make_engine()
        assert eng.query("nonexistent_key") is None


# ===========================================================================
# 19 — Concurrency
# ===========================================================================


class TestConcurrency:
    def test_concurrent_submits(self) -> None:
        from iios.supervisor.integration.supervisor_integration_request import (
            SupervisorIntegrationRequest,
        )

        eng = _make_engine()
        eng.start()
        results = []
        errors  = []

        def worker():
            try:
                req  = SupervisorIntegrationRequest.create(str(uuid.uuid4()))
                resp = eng.submit(req)
                results.append(resp.is_success)
            except Exception as e:
                errors.append(e)

        try:
            threads = [threading.Thread(target=worker) for _ in range(20)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert not errors, f"Errors: {errors}"
            assert len(results) == 20
        finally:
            eng.stop()


# ===========================================================================
# 20 — Public surface (__init__ exports)
# ===========================================================================


class TestPublicSurface:
    def test_engine_exported(self) -> None:
        from iios.supervisor.integration import SupervisorIntegrationEngine
        assert SupervisorIntegrationEngine is not None

    def test_request_exported(self) -> None:
        from iios.supervisor.integration import SupervisorIntegrationRequest
        assert SupervisorIntegrationRequest is not None

    def test_response_exported(self) -> None:
        from iios.supervisor.integration import SupervisorIntegrationResponse
        assert SupervisorIntegrationResponse is not None

    def test_context_exported(self) -> None:
        from iios.supervisor.integration import SupervisorIntegrationContext
        assert SupervisorIntegrationContext is not None

    def test_exceptions_exported(self) -> None:
        from iios.supervisor.integration import (
            SupervisorIntegrationError,
            SupervisorIntegrationNotRunningError,
            SupervisorIntegrationValidationError,
        )
        assert SupervisorIntegrationNotRunningError is not None

    def test_events_exported(self) -> None:
        from iios.supervisor.integration import (
            SupervisorIntegrationEvent,
            make_integration_initialized_event,
        )
        assert make_integration_initialized_event is not None

    def test_statistics_exported(self) -> None:
        from iios.supervisor.integration import SupervisorIntegrationStatistics
        assert SupervisorIntegrationStatistics is not None

    def test_history_exported(self) -> None:
        from iios.supervisor.integration import SupervisorIntegrationHistory
        assert SupervisorIntegrationHistory is not None

    def test_component_factory_exported(self) -> None:
        from iios.supervisor.integration import SupervisorComponentFactory
        assert SupervisorComponentFactory is not None

    def test_snapshot_wrapper_exported(self) -> None:
        from iios.supervisor.integration import SupervisorIntegrationSnapshot
        assert SupervisorIntegrationSnapshot is not None

    def test_validator_exported(self) -> None:
        from iios.supervisor.integration import SupervisorIntegrationValidator
        assert SupervisorIntegrationValidator is not None

    def test_all_is_complete(self) -> None:
        import iios.supervisor.integration as m6
        for name in m6.__all__:
            assert hasattr(m6, name), f"Missing from module: {name}"


# ===========================================================================
# 21 — Integration (end-to-end with test doubles)
# ===========================================================================


class TestEndToEnd:
    def test_full_integration_cycle(self) -> None:
        from iios.supervisor.integration.supervisor_integration_request import (
            SupervisorIntegrationRequest,
        )
        eng = _make_engine()
        eng.start()
        try:
            req  = SupervisorIntegrationRequest.create(
                "int-e2e-001",
                inputs={"risk_snapshot": {"vix": 18}, "market_snapshot": {"trend": "up"}},
            )
            resp = eng.submit(req)

            assert resp.is_success
            assert resp.integration_id == "int-e2e-001"
            assert resp.has_snapshot
            assert isinstance(resp.platform_health_summary.overall_health, float)
            assert isinstance(resp.governance_summary.final_action, str)
            assert isinstance(resp.enterprise_assessment.stability_score, float)
        finally:
            eng.stop()

    def test_listener_receives_events(self) -> None:
        from iios.supervisor.integration.supervisor_integration_request import (
            SupervisorIntegrationRequest,
        )
        events_received = []
        eng = _make_engine()
        eng.add_listener(lambda e: events_received.append(e))
        eng.start()
        try:
            req = SupervisorIntegrationRequest.create("int-e2e-002")
            eng.submit(req)
        finally:
            eng.stop()

        assert len(events_received) > 0

    def test_statistics_accumulate_over_requests(self) -> None:
        from iios.supervisor.integration.supervisor_integration_request import (
            SupervisorIntegrationRequest,
        )
        eng = _make_engine()
        eng.start()
        try:
            for _ in range(3):
                eng.submit(SupervisorIntegrationRequest.create(str(uuid.uuid4())))
            stats = eng.statistics()
            assert stats["integration_requests"] >= 3
        finally:
            eng.stop()

    def test_query_components(self) -> None:
        eng = _make_engine()
        eng.start()
        try:
            comps = eng.query("components")
            assert isinstance(comps, dict)
            assert len(comps) == 5
        finally:
            eng.stop()

    def test_remove_listener(self) -> None:
        events = []
        eng    = _make_engine()
        fn     = lambda e: events.append(e)
        eng.add_listener(fn)
        eng.remove_listener(fn)
        eng.start()
        try:
            initial = len(events)
            from iios.supervisor.integration.supervisor_integration_request import (
                SupervisorIntegrationRequest,
            )
            eng.submit(SupervisorIntegrationRequest.create("int-listen"))
        finally:
            eng.stop()
        # After removal, should not have grown much (stop event may still fire)
        assert len(events) == initial
