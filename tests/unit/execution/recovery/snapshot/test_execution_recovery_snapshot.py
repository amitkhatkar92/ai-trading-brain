"""
tests/unit/execution/recovery/snapshot/test_execution_recovery_snapshot.py
===========================================================================
Comprehensive test suite for the Execution Recovery Snapshot (C7 M5).

95%+ coverage target across all 15 source files.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

from iios.execution.recovery.snapshot.constants import (
    LIFECYCLE_TERMINAL_STATES,
    LIFECYCLE_VALID_STATES,
    SCHEMA_VERSION,
    VERSION,
    RecoveryResult,
    SnapshotEventType,
    SnapshotHealth,
    SnapshotStatus,
    VerificationOutcome,
)
from iios.execution.recovery.snapshot.exceptions import (
    RecoverySnapshotError,
    SnapshotBuildError,
    SnapshotCacheError,
    SnapshotDuplicateError,
    SnapshotNotFoundError,
    SnapshotNotRunningError,
    SnapshotRegistryError,
    SnapshotStoreError,
    SnapshotValidationError,
    SnapshotVersionError,
)
from iios.execution.recovery.snapshot.execution_recovery_snapshot import (
    ExecutionRecoverySnapshot,
    make_execution_recovery_snapshot,
)
from iios.execution.recovery.snapshot.recovery_snapshot_builder import RecoverySnapshotBuilder
from iios.execution.recovery.snapshot.recovery_snapshot_bundle import (
    RecoverySnapshotBundle,
    make_snapshot_bundle,
)
from iios.execution.recovery.snapshot.recovery_snapshot_cache import RecoverySnapshotCache
from iios.execution.recovery.snapshot.recovery_snapshot_events import (
    SnapshotEvent,
    make_snapshot_archived,
    make_snapshot_cached,
    make_snapshot_created,
    make_snapshot_published,
    make_snapshot_retrieved,
    make_snapshot_validated,
)
from iios.execution.recovery.snapshot.recovery_snapshot_factory import RecoverySnapshotFactory
from iios.execution.recovery.snapshot.recovery_snapshot_history import RecoverySnapshotHistory
from iios.execution.recovery.snapshot.recovery_snapshot_metadata import (
    AuditMetadata,
    make_audit_metadata,
)
from iios.execution.recovery.snapshot.recovery_snapshot_registry import (
    RecoverySnapshotRegistry,
)
from iios.execution.recovery.snapshot.recovery_snapshot_statistics import (
    RecoverySnapshotStatistics,
)
from iios.execution.recovery.snapshot.recovery_snapshot_store import RecoverySnapshotStore
from iios.execution.recovery.snapshot.recovery_snapshot_validation import (
    RecoverySnapshotValidator,
    SnapshotValidationResult,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _snap(
    *,
    recovery_session_id:  str = "",
    execution_session_id: str = "",
    lifecycle_state:      str = "completed",
    recovery_result:      RecoveryResult = RecoveryResult.SUCCESS,
    verification_result:  VerificationOutcome = VerificationOutcome.PASSED,
    recovery_duration_ms: float = 100.0,
    failure_id:           str = "",
    workflow_id:          str = "",
    gateway_id:           str = "",
    broker_id:            str = "",
    snapshot_version:     int = 1,
    recovery_status:      SnapshotStatus = SnapshotStatus.CREATED,
    recovery_health:      SnapshotHealth = SnapshotHealth.HEALTHY,
    selected_recovery_policy: str = "RetryPolicy",
    executed_failover_strategy: str = "retry",
    recovery_trigger:     str = "automatic",
    recovery_reason:      str = "test",
    **kwargs: Any,
) -> ExecutionRecoverySnapshot:
    return make_execution_recovery_snapshot(
        recovery_session_id        = recovery_session_id or str(uuid.uuid4()),
        execution_session_id       = execution_session_id or str(uuid.uuid4()),
        lifecycle_state            = lifecycle_state,
        recovery_result            = recovery_result,
        verification_result        = verification_result,
        recovery_duration_ms       = recovery_duration_ms,
        failure_id                 = failure_id,
        workflow_id                = workflow_id,
        gateway_id                 = gateway_id,
        broker_id                  = broker_id,
        snapshot_version           = snapshot_version,
        recovery_status            = recovery_status,
        recovery_health            = recovery_health,
        selected_recovery_policy   = selected_recovery_policy,
        executed_failover_strategy = executed_failover_strategy,
        recovery_trigger           = recovery_trigger,
        recovery_reason            = recovery_reason,
        **kwargs,
    )


def _mock_session(
    session_id:           str = "",
    execution_session_id: str = "",
    state:                str = "completed",
    recovery_trigger:     str = "automatic",
    recovery_reason:      str = "test",
    workflow_id:          str = "",
    failure_id:           str = "",
    recovery_plan_id:     str = "",
) -> MagicMock:
    m = MagicMock()
    m.session_id           = session_id or str(uuid.uuid4())
    m.execution_session_id = execution_session_id or str(uuid.uuid4())
    m.state                = MagicMock()
    m.state.value          = state
    m.recovery_trigger     = MagicMock()
    m.recovery_trigger.value = recovery_trigger
    m.recovery_reason      = recovery_reason
    m.workflow_id          = workflow_id
    m.failure_id           = failure_id
    m.recovery_plan_id     = recovery_plan_id
    m.framework_version    = VERSION
    return m


def _mock_engine_response(
    outcome:   str = "success",
    duration:  float = 150.0,
    stages_done: int = 6,
    stages_total: int = 6,
) -> MagicMock:
    m = MagicMock()
    m.outcome              = MagicMock()
    m.outcome.value        = outcome
    m.duration_ms          = duration
    m.pipeline_stages_completed = stages_done
    m.pipeline_stages_total     = stages_total
    m.framework_version    = VERSION
    return m


def _mock_policy_decision(
    policy_name:     str = "RetryPolicy",
    strategy_type:   str = "retry",
    confidence:      float = 0.9,
) -> MagicMock:
    m = MagicMock()
    m.policy_name      = policy_name
    m.strategy_type    = MagicMock()
    m.strategy_type.value = strategy_type
    m.confidence_score = confidence
    m.version          = VERSION
    return m


def _mock_failover_response(
    is_successful:  bool = True,
    is_operational: bool = True,
    action_executed: str = "retry",
    verification_passed: bool = True,
) -> MagicMock:
    m = MagicMock()
    m.is_successful  = is_successful
    m.is_operational = is_operational

    result = MagicMock()
    result.action_executed       = MagicMock()
    result.action_executed.value = action_executed
    m.result = result

    vr = MagicMock()
    vr.overall_status       = MagicMock()
    vr.overall_status.value = "passed" if verification_passed else "failed"
    m.verification_report   = vr
    m.response_time_ms      = 5.0
    return m


# ════════════════════════════════════════════════════════════════════════════
# 1.  Constants
# ════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_snapshot_status_values(self):
        assert SnapshotStatus.CREATED.value  == "created"
        assert SnapshotStatus.PUBLISHED.value == "published"
        assert SnapshotStatus.ARCHIVED.value  == "archived"

    def test_recovery_result_values(self):
        assert RecoveryResult.SUCCESS.value == "success"
        assert RecoveryResult.FAILURE.value == "failure"
        assert RecoveryResult.UNKNOWN.value == "unknown"

    def test_verification_outcome_values(self):
        assert VerificationOutcome.PASSED.value  == "passed"
        assert VerificationOutcome.SKIPPED.value == "skipped"

    def test_snapshot_health_values(self):
        assert SnapshotHealth.HEALTHY.value   == "healthy"
        assert SnapshotHealth.UNHEALTHY.value == "unhealthy"

    def test_lifecycle_terminal_states(self):
        assert "completed" in LIFECYCLE_TERMINAL_STATES
        assert "failed" in LIFECYCLE_TERMINAL_STATES
        assert "aborted" in LIFECYCLE_TERMINAL_STATES

    def test_lifecycle_valid_states(self):
        assert LIFECYCLE_TERMINAL_STATES.issubset(LIFECYCLE_VALID_STATES)
        assert "recovering" in LIFECYCLE_VALID_STATES

    def test_event_type_values(self):
        for et in SnapshotEventType:
            assert isinstance(et.value, str)


# ════════════════════════════════════════════════════════════════════════════
# 2.  Exceptions
# ════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_error_code(self):
        e = RecoverySnapshotError("test")
        assert e.error_code == "RS-000"

    def test_not_running(self):
        e = SnapshotNotRunningError()
        assert e.error_code == "RS-001"

    def test_validation_error(self):
        e = SnapshotValidationError("bad", errors=("e1", "e2"))
        assert e.error_code == "RS-002"
        assert "e1" in e.errors

    def test_build_error(self):
        e = SnapshotBuildError("build failed", reason="missing_session")
        assert e.error_code == "RS-003"
        assert e.reason == "missing_session"

    def test_not_found_error(self):
        e = SnapshotNotFoundError("snap-abc")
        assert e.error_code == "RS-004"
        assert e.snapshot_id == "snap-abc"

    def test_duplicate_error(self):
        e = SnapshotDuplicateError("snap-xyz")
        assert e.error_code == "RS-005"
        assert e.snapshot_id == "snap-xyz"

    def test_store_error(self):
        e = SnapshotStoreError("full")
        assert e.error_code == "RS-006"

    def test_cache_error(self):
        e = SnapshotCacheError("cache broken")
        assert e.error_code == "RS-007"

    def test_registry_error(self):
        e = SnapshotRegistryError("dup")
        assert e.error_code == "RS-008"

    def test_version_error(self):
        e = SnapshotVersionError("2.0")
        assert e.error_code == "RS-009"
        assert e.version == "2.0"

    def test_hierarchy(self):
        for cls in [
            SnapshotNotRunningError, SnapshotValidationError, SnapshotBuildError,
            SnapshotNotFoundError, SnapshotDuplicateError, SnapshotStoreError,
        ]:
            assert issubclass(cls, RecoverySnapshotError)


# ════════════════════════════════════════════════════════════════════════════
# 3.  AuditMetadata
# ════════════════════════════════════════════════════════════════════════════

class TestAuditMetadata:
    def test_factory_defaults(self):
        a = make_audit_metadata()
        assert a.audit_id
        assert a.framework_version == VERSION
        assert a.schema_version == SCHEMA_VERSION
        assert a.build_time_ms == 0.0

    def test_factory_custom(self):
        a = make_audit_metadata(
            build_time_ms=15.5,
            tags=("prod",),
            lifecycle_version="2.0",
        )
        assert a.build_time_ms == 15.5
        assert "prod" in a.tags
        assert a.lifecycle_version == "2.0"

    def test_frozen(self):
        a = make_audit_metadata()
        with pytest.raises((AttributeError, TypeError)):
            a.built_by = "other"  # type: ignore[misc]

    def test_to_dict(self):
        a = make_audit_metadata(build_time_ms=5.0)
        d = a.to_dict()
        assert "audit_id" in d
        assert d["build_time_ms"] == 5.0
        assert "tags" in d


# ════════════════════════════════════════════════════════════════════════════
# 4.  ExecutionRecoverySnapshot
# ════════════════════════════════════════════════════════════════════════════

class TestExecutionRecoverySnapshot:
    def test_factory_creates_snapshot(self):
        s = _snap()
        assert s.snapshot_id
        assert s.recovery_session_id
        assert s.snapshot_version == 1

    def test_is_successful_true(self):
        s = _snap(recovery_result=RecoveryResult.SUCCESS)
        assert s.is_successful

    def test_is_successful_false(self):
        s = _snap(recovery_result=RecoveryResult.FAILURE)
        assert not s.is_successful

    def test_is_verified_true(self):
        s = _snap(verification_result=VerificationOutcome.PASSED)
        assert s.is_verified

    def test_is_verified_false(self):
        s = _snap(verification_result=VerificationOutcome.FAILED)
        assert not s.is_verified

    def test_is_published(self):
        s = _snap(recovery_status=SnapshotStatus.PUBLISHED)
        assert s.is_published

    def test_is_not_published(self):
        s = _snap(recovery_status=SnapshotStatus.CREATED)
        assert not s.is_published

    def test_is_complete_terminal_state(self):
        for state in ("completed", "failed", "aborted", "archived"):
            s = _snap(lifecycle_state=state)
            assert s.is_complete, f"Expected is_complete for state={state}"

    def test_is_not_complete_active_state(self):
        s = _snap(lifecycle_state="recovering")
        assert not s.is_complete

    def test_is_archived(self):
        s = _snap(recovery_status=SnapshotStatus.ARCHIVED)
        assert s.is_archived

    def test_frozen(self):
        s = _snap()
        with pytest.raises((AttributeError, TypeError)):
            s.snapshot_id = "other"  # type: ignore[misc]

    def test_to_dict_contains_all_fields(self):
        s = _snap()
        d = s.to_dict()
        required = [
            "snapshot_id", "snapshot_version", "recovery_session_id",
            "lifecycle_state", "recovery_status", "recovery_result",
            "verification_result", "recovery_duration_ms", "audit_metadata",
            "framework_version", "schema_version", "timestamp",
        ]
        for key in required:
            assert key in d, f"Missing key: {key}"

    def test_to_json_produces_valid_json(self):
        import json
        s = _snap()
        j = s.to_json()
        d = json.loads(j)
        assert d["snapshot_id"] == s.snapshot_id

    def test_to_dict_enum_values_are_strings(self):
        s = _snap()
        d = s.to_dict()
        assert isinstance(d["recovery_result"], str)
        assert isinstance(d["verification_result"], str)
        assert isinstance(d["recovery_status"], str)
        assert isinstance(d["recovery_health"], str)

    def test_optional_ids_empty_by_default(self):
        s = _snap()
        assert s.execution_id    == ""
        assert s.gateway_id      == ""
        assert s.broker_id       == ""
        assert s.portfolio_id    == ""
        assert s.strategy_id     == ""

    def test_custom_metadata_persists(self):
        s = _snap(recovery_metadata={"key": "val"}, recovery_statistics={"count": 5})
        assert s.recovery_metadata["key"] == "val"
        assert s.recovery_statistics["count"] == 5

    def test_snapshot_size_default_zero(self):
        s = _snap()
        assert s.snapshot_size_bytes == 0

    def test_snapshot_size_custom(self):
        s = _snap(snapshot_size_bytes=4096)
        assert s.snapshot_size_bytes == 4096

    def test_unique_ids_each_call(self):
        ids = {_snap().snapshot_id for _ in range(20)}
        assert len(ids) == 20


# ════════════════════════════════════════════════════════════════════════════
# 5.  SnapshotValidationResult
# ════════════════════════════════════════════════════════════════════════════

class TestSnapshotValidationResult:
    def test_initially_valid(self):
        r = SnapshotValidationResult()
        assert r.is_valid
        assert not r.errors
        assert not r.warnings

    def test_add_error_marks_invalid(self):
        r = SnapshotValidationResult()
        r.add_error("bad field")
        assert not r.is_valid
        assert "bad field" in r.errors

    def test_add_warning_keeps_valid(self):
        r = SnapshotValidationResult()
        r.add_warning("suspicious field")
        assert r.is_valid
        assert "suspicious field" in r.warnings

    def test_merge_propagates_errors(self):
        r1 = SnapshotValidationResult()
        r2 = SnapshotValidationResult()
        r2.add_error("error from r2")
        r1.merge(r2)
        assert not r1.is_valid
        assert "error from r2" in r1.errors

    def test_merge_propagates_warnings(self):
        r1 = SnapshotValidationResult()
        r2 = SnapshotValidationResult()
        r2.add_warning("warn from r2")
        r1.merge(r2)
        assert r1.is_valid
        assert "warn from r2" in r1.warnings

    def test_to_dict(self):
        r = SnapshotValidationResult()
        r.add_warning("w")
        d = r.to_dict()
        assert "is_valid" in d
        assert "w" in d["warnings"]


# ════════════════════════════════════════════════════════════════════════════
# 6.  RecoverySnapshotValidator
# ════════════════════════════════════════════════════════════════════════════

class TestRecoverySnapshotValidator:
    def setup_method(self):
        self.v = RecoverySnapshotValidator()

    def test_valid_snapshot(self):
        r = self.v.validate(_snap())
        assert r.is_valid, f"Unexpected errors: {r.errors}"

    def test_none_snapshot_invalid(self):
        r = self.v.validate(None)
        assert not r.is_valid

    def test_empty_snapshot_id_invalid(self):
        # Bypass factory (which auto-generates UUID) to inject an empty snapshot_id
        s = _snap()
        s2 = ExecutionRecoverySnapshot(
            snapshot_id                = "",  # ← empty
            snapshot_version           = 1,
            recovery_session_id        = s.recovery_session_id,
            recovery_plan_id           = "",
            failure_id                 = "",
            execution_session_id       = s.execution_session_id,
            execution_id               = "",
            workflow_id                = "",
            gateway_id                 = "",
            broker_id                  = "",
            portfolio_id               = "",
            strategy_id                = "",
            lifecycle_state            = "completed",
            recovery_status            = SnapshotStatus.CREATED,
            recovery_health            = SnapshotHealth.UNKNOWN,
            selected_recovery_policy   = "",
            executed_failover_strategy = "",
            recovery_trigger           = "",
            recovery_reason            = "",
            recovery_result            = RecoveryResult.SUCCESS,
            verification_result        = VerificationOutcome.PASSED,
            recovery_duration_ms       = 10.0,
            recovery_statistics        = {},
            recovery_metadata          = {},
            audit_metadata             = make_audit_metadata(),
            framework_version          = VERSION,
            schema_version             = SCHEMA_VERSION,
            timestamp                  = time.time(),
        )
        r = self.v.validate_identifiers(s2)
        assert not r.is_valid

    def test_invalid_lifecycle_state(self):
        s2 = make_execution_recovery_snapshot(
            recovery_session_id  = str(uuid.uuid4()),
            execution_session_id = str(uuid.uuid4()),
            lifecycle_state      = "BOGUS_STATE",
            recovery_result      = RecoveryResult.SUCCESS,
            verification_result  = VerificationOutcome.PASSED,
            recovery_duration_ms = 10.0,
        )
        r = self.v.validate_lifecycle(s2)
        assert not r.is_valid

    def test_valid_lifecycle_states(self):
        for state in LIFECYCLE_VALID_STATES:
            s = _snap(lifecycle_state=state)
            r = self.v.validate_lifecycle(s)
            assert r.is_valid, f"Unexpected invalid for state={state}: {r.errors}"

    def test_negative_duration_invalid(self):
        s = make_execution_recovery_snapshot(
            recovery_session_id  = str(uuid.uuid4()),
            execution_session_id = str(uuid.uuid4()),
            lifecycle_state      = "completed",
            recovery_result      = RecoveryResult.SUCCESS,
            verification_result  = VerificationOutcome.PASSED,
            recovery_duration_ms = -1.0,  # ← negative
        )
        r = self.v.validate_recovery(s)
        assert not r.is_valid

    def test_empty_schema_version_invalid(self):
        s = make_execution_recovery_snapshot(
            recovery_session_id  = str(uuid.uuid4()),
            execution_session_id = str(uuid.uuid4()),
            lifecycle_state      = "completed",
            recovery_result      = RecoveryResult.SUCCESS,
            verification_result  = VerificationOutcome.PASSED,
            recovery_duration_ms = 10.0,
            schema_version       = "",  # ← empty
        )
        r = self.v.validate_version(s)
        assert not r.is_valid

    def test_future_timestamp_warning(self):
        s = make_execution_recovery_snapshot(
            recovery_session_id  = str(uuid.uuid4()),
            execution_session_id = str(uuid.uuid4()),
            lifecycle_state      = "completed",
            recovery_result      = RecoveryResult.SUCCESS,
            verification_result  = VerificationOutcome.PASSED,
            recovery_duration_ms = 10.0,
            timestamp            = time.time() + 120.0,  # 2 min future
        )
        r = self.v.validate_timestamp(s)
        assert r.is_valid   # warning only, not error
        assert r.warnings

    def test_negative_timestamp_invalid(self):
        s = make_execution_recovery_snapshot(
            recovery_session_id  = str(uuid.uuid4()),
            execution_session_id = str(uuid.uuid4()),
            lifecycle_state      = "completed",
            recovery_result      = RecoveryResult.SUCCESS,
            verification_result  = VerificationOutcome.PASSED,
            recovery_duration_ms = 10.0,
            timestamp            = -1.0,
        )
        r = self.v.validate_timestamp(s)
        assert not r.is_valid

    def test_validate_policy_warning_when_empty(self):
        s = _snap(selected_recovery_policy="")
        r = self.v.validate_policy(s)
        # warning, not error
        assert r.is_valid
        assert r.warnings

    def test_full_validate_aggregates(self):
        r = self.v.validate(_snap())
        assert r.is_valid


# ════════════════════════════════════════════════════════════════════════════
# 7.  RecoverySnapshotFactory
# ════════════════════════════════════════════════════════════════════════════

class TestRecoverySnapshotFactory:
    def setup_method(self):
        self.factory = RecoverySnapshotFactory()
        self.factory.start()

    def teardown_method(self):
        if self.factory.lifecycle_state() not in ("stopped", "STOPPED"):
            self.factory.stop()

    def test_create_basic(self):
        s = self.factory.create(
            recovery_session_id  = str(uuid.uuid4()),
            execution_session_id = str(uuid.uuid4()),
            lifecycle_state      = "completed",
            recovery_result      = RecoveryResult.SUCCESS,
            verification_result  = VerificationOutcome.PASSED,
            recovery_duration_ms = 200.0,
        )
        assert s.snapshot_id
        assert s.is_successful
        assert s.is_verified

    def test_not_running_raises(self):
        f = RecoverySnapshotFactory()
        with pytest.raises(SnapshotNotRunningError):
            f.create(
                recovery_session_id  = str(uuid.uuid4()),
                execution_session_id = str(uuid.uuid4()),
                lifecycle_state      = "completed",
                recovery_result      = RecoveryResult.SUCCESS,
                verification_result  = VerificationOutcome.PASSED,
                recovery_duration_ms = 10.0,
            )

    def test_all_optional_fields(self):
        s = self.factory.create(
            recovery_session_id        = str(uuid.uuid4()),
            execution_session_id       = str(uuid.uuid4()),
            lifecycle_state            = "failed",
            recovery_result            = RecoveryResult.FAILURE,
            verification_result        = VerificationOutcome.FAILED,
            recovery_duration_ms       = 50.0,
            workflow_id                = "wf-1",
            gateway_id                 = "gw-1",
            broker_id                  = "bk-1",
            portfolio_id               = "pf-1",
            strategy_id                = "st-1",
            selected_recovery_policy   = "FailoverPolicy",
            executed_failover_strategy = "switch_broker",
            recovery_statistics        = {"errors": 2},
        )
        assert s.workflow_id == "wf-1"
        assert s.broker_id == "bk-1"
        assert s.recovery_statistics["errors"] == 2


# ════════════════════════════════════════════════════════════════════════════
# 8.  SnapshotEvents
# ════════════════════════════════════════════════════════════════════════════

class TestSnapshotEvents:
    def test_created_event(self):
        e = make_snapshot_created("snap-1", "sess-1")
        assert e.event_type == SnapshotEventType.SNAPSHOT_CREATED
        assert e.snapshot_id == "snap-1"

    def test_validated_event(self):
        e = make_snapshot_validated("snap-1", "sess-1")
        assert e.event_type == SnapshotEventType.SNAPSHOT_VALIDATED

    def test_published_event(self):
        e = make_snapshot_published("snap-1", "sess-1")
        assert e.event_type == SnapshotEventType.SNAPSHOT_PUBLISHED

    def test_archived_event(self):
        e = make_snapshot_archived("snap-1", "sess-1")
        assert e.event_type == SnapshotEventType.SNAPSHOT_ARCHIVED

    def test_retrieved_event(self):
        e = make_snapshot_retrieved("snap-1", "sess-1")
        assert e.event_type == SnapshotEventType.SNAPSHOT_RETRIEVED

    def test_cached_event(self):
        e = make_snapshot_cached("snap-1", "sess-1")
        assert e.event_type == SnapshotEventType.SNAPSHOT_CACHED

    def test_event_frozen(self):
        e = make_snapshot_created("s", "r")
        with pytest.raises((AttributeError, TypeError)):
            e.event_id = "other"  # type: ignore[misc]

    def test_event_to_dict(self):
        e = make_snapshot_created("snap-1", "sess-1", reason="test")
        d = e.to_dict()
        assert d["event_type"] == "snapshot_created"
        assert d["snapshot_id"] == "snap-1"
        assert d["reason"] == "test"

    def test_event_unique_ids(self):
        ids = {make_snapshot_created("s", "r").event_id for _ in range(20)}
        assert len(ids) == 20


# ════════════════════════════════════════════════════════════════════════════
# 9.  RecoverySnapshotStatistics
# ════════════════════════════════════════════════════════════════════════════

class TestRecoverySnapshotStatistics:
    def setup_method(self):
        self.stats = RecoverySnapshotStatistics()

    def test_initial_state(self):
        assert self.stats.snapshots_created    == 0
        assert self.stats.snapshots_published  == 0
        assert self.stats.average_build_time_ms == 0.0

    def test_record_created(self):
        self.stats.record_created()
        assert self.stats.snapshots_created == 1

    def test_record_published(self):
        self.stats.record_published()
        assert self.stats.snapshots_published == 1

    def test_record_archived(self):
        self.stats.record_archived()
        assert self.stats.snapshots_archived == 1

    def test_validation_success_rate(self):
        self.stats.record_validation_run(passed=True)
        self.stats.record_validation_run(passed=False)
        assert self.stats.validation_success_rate == 0.5

    def test_validation_rate_zero_when_none(self):
        assert self.stats.validation_success_rate == 0.0

    def test_average_build_time(self):
        self.stats.record_build_time(10.0)
        self.stats.record_build_time(20.0)
        assert self.stats.average_build_time_ms == 15.0

    def test_average_snapshot_size(self):
        self.stats.record_snapshot_size(100)
        self.stats.record_snapshot_size(200)
        assert self.stats.average_snapshot_size_bytes == 150.0

    def test_copy_is_independent(self):
        self.stats.record_created()
        copy = self.stats.copy()
        assert copy.snapshots_created == 1
        self.stats.record_created()
        assert copy.snapshots_created == 1  # copy unaffected

    def test_reset(self):
        self.stats.record_created()
        self.stats.record_published()
        self.stats.reset()
        assert self.stats.snapshots_created == 0
        assert self.stats.snapshots_published == 0

    def test_to_dict(self):
        d = self.stats.to_dict()
        assert "snapshots_created" in d
        assert "average_build_time_ms" in d

    def test_thread_safety(self):
        errors = []

        def worker():
            try:
                for _ in range(100):
                    self.stats.record_created()
                    self.stats.record_build_time(5.0)
                    self.stats.record_validation_run(passed=True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert self.stats.snapshots_created == 500


# ════════════════════════════════════════════════════════════════════════════
# 10. RecoverySnapshotHistory
# ════════════════════════════════════════════════════════════════════════════

class TestRecoverySnapshotHistory:
    def setup_method(self):
        self.hist = RecoverySnapshotHistory(max_snapshots=10, max_events=20)

    def test_append_and_read(self):
        s = _snap()
        self.hist.append(s)
        assert self.hist.snapshot_count == 1
        assert self.hist.latest() is s

    def test_append_event(self):
        e = make_snapshot_created("s", "r")
        self.hist.append_event(e)
        assert self.hist.event_count == 1

    def test_bounded_capacity(self):
        for _ in range(15):
            self.hist.append(_snap())
        assert self.hist.snapshot_count == 10

    def test_for_session(self):
        sid = str(uuid.uuid4())
        self.hist.append(_snap(recovery_session_id=sid))
        self.hist.append(_snap())  # different session
        assert len(self.hist.for_session(sid)) == 1

    def test_for_failure(self):
        fid = str(uuid.uuid4())
        self.hist.append(_snap(failure_id=fid))
        self.hist.append(_snap(failure_id="other"))
        assert len(self.hist.for_failure(fid)) == 1

    def test_for_execution(self):
        eid = str(uuid.uuid4())
        s = make_execution_recovery_snapshot(
            recovery_session_id  = str(uuid.uuid4()),
            execution_session_id = eid,
            lifecycle_state      = "completed",
            recovery_result      = RecoveryResult.SUCCESS,
            verification_result  = VerificationOutcome.PASSED,
            recovery_duration_ms = 10.0,
        )
        self.hist.append(s)
        assert len(self.hist.for_execution(eid)) == 1
        assert len(self.hist.for_execution("other")) == 0

    def test_latest_none_when_empty(self):
        assert self.hist.latest() is None

    def test_snapshots_returns_list(self):
        self.hist.append(_snap())
        snaps = self.hist.snapshots()
        assert isinstance(snaps, list)
        assert len(snaps) == 1

    def test_clear(self):
        self.hist.append(_snap())
        self.hist.append_event(make_snapshot_created("s", "r"))
        self.hist.clear()
        assert self.hist.snapshot_count == 0
        assert self.hist.event_count == 0


# ════════════════════════════════════════════════════════════════════════════
# 11. RecoverySnapshotStore
# ════════════════════════════════════════════════════════════════════════════

class TestRecoverySnapshotStore:
    def setup_method(self):
        self.store = RecoverySnapshotStore()
        self.store.start()

    def teardown_method(self):
        if self.store.lifecycle_state() not in ("stopped", "STOPPED"):
            self.store.stop()

    def _save(self, **kw) -> ExecutionRecoverySnapshot:
        s = _snap(**kw)
        self.store.save(s)
        return s

    def test_save_and_get(self):
        s = self._save()
        found = self.store.get(s.snapshot_id)
        assert found is s

    def test_get_missing_returns_none(self):
        assert self.store.get("no-such-id") is None

    def test_get_or_raise(self):
        s = self._save()
        assert self.store.get_or_raise(s.snapshot_id) is s

    def test_get_or_raise_missing(self):
        with pytest.raises(SnapshotNotFoundError):
            self.store.get_or_raise("no-such-id")

    def test_duplicate_raises(self):
        s = _snap()
        self.store.save(s)
        with pytest.raises(SnapshotDuplicateError):
            self.store.save(s)

    def test_capacity_limit(self):
        store = RecoverySnapshotStore(max_snapshots=2)
        store.start()
        store.save(_snap())
        store.save(_snap())
        with pytest.raises(SnapshotStoreError):
            store.save(_snap())
        store.stop()

    def test_all(self):
        s1 = self._save()
        s2 = self._save()
        all_snaps = self.store.all()
        assert s1 in all_snaps
        assert s2 in all_snaps

    def test_latest(self):
        self._save()
        s = self._save()
        assert self.store.latest() is s

    def test_by_session(self):
        sid = str(uuid.uuid4())
        self._save(recovery_session_id=sid)
        self._save()  # different session
        assert len(self.store.by_session(sid)) == 1

    def test_by_failure(self):
        fid = str(uuid.uuid4())
        self._save(failure_id=fid)
        self._save(failure_id="other")
        assert len(self.store.by_failure(fid)) == 1

    def test_by_execution(self):
        eid = str(uuid.uuid4())
        s = make_execution_recovery_snapshot(
            recovery_session_id  = str(uuid.uuid4()),
            execution_session_id = eid,
            lifecycle_state      = "completed",
            recovery_result      = RecoveryResult.SUCCESS,
            verification_result  = VerificationOutcome.PASSED,
            recovery_duration_ms = 10.0,
        )
        self.store.save(s)
        assert len(self.store.by_execution(eid)) == 1

    def test_by_workflow(self):
        wid = str(uuid.uuid4())
        self._save(workflow_id=wid)
        assert len(self.store.by_workflow(wid)) == 1

    def test_by_gateway(self):
        gid = str(uuid.uuid4())
        self._save(gateway_id=gid)
        assert len(self.store.by_gateway(gid)) == 1

    def test_by_broker(self):
        bid = str(uuid.uuid4())
        self._save(broker_id=bid)
        assert len(self.store.by_broker(bid)) == 1

    def test_by_status(self):
        self._save(recovery_status=SnapshotStatus.PUBLISHED)
        self._save(recovery_status=SnapshotStatus.CREATED)
        assert len(self.store.by_status(SnapshotStatus.PUBLISHED)) == 1

    def test_by_result(self):
        self._save(recovery_result=RecoveryResult.SUCCESS)
        self._save(recovery_result=RecoveryResult.FAILURE)
        assert len(self.store.by_result(RecoveryResult.SUCCESS)) == 1

    def test_by_verification(self):
        self._save(verification_result=VerificationOutcome.PASSED)
        self._save(verification_result=VerificationOutcome.FAILED)
        assert len(self.store.by_verification(VerificationOutcome.PASSED)) == 1

    def test_by_timestamp_range(self):
        now = time.time()
        s = _snap(timestamp=now)
        # frozen — use factory with timestamp
        s2 = make_execution_recovery_snapshot(
            recovery_session_id  = str(uuid.uuid4()),
            execution_session_id = str(uuid.uuid4()),
            lifecycle_state      = "completed",
            recovery_result      = RecoveryResult.SUCCESS,
            verification_result  = VerificationOutcome.PASSED,
            recovery_duration_ms = 10.0,
            timestamp            = now + 10,
        )
        self.store.save(s)
        self.store.save(s2)
        results = self.store.by_timestamp_range(since=now - 1, before=now + 5)
        assert len(results) == 1
        assert results[0] is s

    def test_latest_for_session_returns_highest_version(self):
        sid = str(uuid.uuid4())
        s1 = _snap(recovery_session_id=sid, snapshot_version=1)
        s2 = _snap(recovery_session_id=sid, snapshot_version=2)
        self.store.save(s1)
        self.store.save(s2)
        latest = self.store.latest_for_session(sid)
        assert latest.snapshot_version == 2

    def test_latest_for_session_none_when_missing(self):
        assert self.store.latest_for_session("no-session") is None

    def test_contains(self):
        s = self._save()
        assert self.store.contains(s.snapshot_id)
        assert not self.store.contains("missing")

    def test_snapshot_count(self):
        self._save()
        self._save()
        assert self.store.snapshot_count == 2

    def test_update_overwrites(self):
        s = _snap(recovery_status=SnapshotStatus.CREATED)
        self.store.save(s)
        # Build updated snapshot (same ID, different status)
        s2 = make_execution_recovery_snapshot(
            snapshot_id          = s.snapshot_id,
            recovery_session_id  = s.recovery_session_id,
            execution_session_id = s.execution_session_id,
            lifecycle_state      = s.lifecycle_state,
            recovery_result      = s.recovery_result,
            verification_result  = s.verification_result,
            recovery_duration_ms = s.recovery_duration_ms,
            recovery_status      = SnapshotStatus.PUBLISHED,
        )
        self.store.update(s2)
        assert self.store.get(s.snapshot_id).recovery_status == SnapshotStatus.PUBLISHED

    def test_update_not_found_raises(self):
        with pytest.raises(SnapshotNotFoundError):
            self.store.update(_snap())

    def test_clear(self):
        self._save()
        self.store.clear()
        assert self.store.snapshot_count == 0

    def test_not_running_raises(self):
        store = RecoverySnapshotStore()
        with pytest.raises(SnapshotNotRunningError):
            store.save(_snap())

    def test_concurrent_saves(self):
        errors = []
        lock = threading.Lock()
        results = []

        def worker():
            try:
                s = _snap()
                self.store.save(s)
                with lock:
                    results.append(s.snapshot_id)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert len(results) == 30
        assert self.store.snapshot_count == 30


# ════════════════════════════════════════════════════════════════════════════
# 12. RecoverySnapshotCache
# ════════════════════════════════════════════════════════════════════════════

class TestRecoverySnapshotCache:
    def setup_method(self):
        self.cache = RecoverySnapshotCache()
        self.cache.start()

    def teardown_method(self):
        if self.cache.lifecycle_state() not in ("stopped", "STOPPED"):
            self.cache.stop()

    def test_put_and_get(self):
        s = _snap()
        self.cache.put(s)
        found = self.cache.get(s.recovery_session_id)
        assert found is s

    def test_get_miss_returns_none(self):
        result = self.cache.get("no-session")
        assert result is None

    def test_hit_miss_counts(self):
        s = _snap()
        self.cache.put(s)
        self.cache.get(s.recovery_session_id)  # hit
        self.cache.get("no-session")            # miss
        assert self.cache.hit_count  == 1
        assert self.cache.miss_count == 1

    def test_invalidate(self):
        s = _snap()
        self.cache.put(s)
        self.cache.invalidate(s.recovery_session_id)
        assert self.cache.get(s.recovery_session_id) is None

    def test_invalidate_missing_no_error(self):
        self.cache.invalidate("no-session")  # should not raise

    def test_capacity_evicts_oldest(self):
        cache = RecoverySnapshotCache(max_size=2)
        cache.start()
        s1 = _snap()
        s2 = _snap()
        s3 = _snap()
        cache.put(s1)
        cache.put(s2)
        cache.put(s3)
        assert cache.cache_size == 2
        cache.stop()

    def test_clear(self):
        self.cache.put(_snap())
        self.cache.clear()
        assert self.cache.cache_size == 0
        assert self.cache.hit_count  == 0

    def test_not_running_raises(self):
        c = RecoverySnapshotCache()
        with pytest.raises(SnapshotNotRunningError):
            c.put(_snap())


# ════════════════════════════════════════════════════════════════════════════
# 13. RecoverySnapshotRegistry
# ════════════════════════════════════════════════════════════════════════════

class TestRecoverySnapshotRegistry:
    def setup_method(self):
        self.reg = RecoverySnapshotRegistry()
        self.reg.start()

    def teardown_method(self):
        if self.reg.lifecycle_state() not in ("stopped", "STOPPED"):
            self.reg.stop()

    def test_register_and_check(self):
        self.reg.register("snap-1", "sess-1")
        assert self.reg.is_registered("snap-1")

    def test_duplicate_register_raises(self):
        self.reg.register("snap-1", "sess-1")
        with pytest.raises(SnapshotDuplicateError):
            self.reg.register("snap-1", "sess-1")

    def test_publish(self):
        self.reg.register("snap-1", "sess-1")
        self.reg.publish("snap-1")
        assert self.reg.is_published("snap-1")

    def test_archive(self):
        self.reg.register("snap-1", "sess-1")
        self.reg.archive("snap-1")
        assert self.reg.is_archived("snap-1")

    def test_validate(self):
        self.reg.register("snap-1", "sess-1")
        self.reg.validate("snap-1")
        assert self.reg.is_validated("snap-1")

    def test_publish_not_found_raises(self):
        with pytest.raises(SnapshotNotFoundError):
            self.reg.publish("no-such-id")

    def test_active_ids_excludes_archived(self):
        self.reg.register("s1", "sess-1")
        self.reg.register("s2", "sess-1")
        self.reg.archive("s1")
        assert "s1" not in self.reg.active_ids()
        assert "s2" in self.reg.active_ids()

    def test_ids_for_session(self):
        self.reg.register("s1", "sess-A")
        self.reg.register("s2", "sess-A")
        self.reg.register("s3", "sess-B")
        ids = self.reg.ids_for_session("sess-A")
        assert set(ids) == {"s1", "s2"}

    def test_counts(self):
        self.reg.register("s1", "sess-1")
        self.reg.register("s2", "sess-1")
        self.reg.publish("s1")
        self.reg.archive("s2")
        assert self.reg.registered_count == 2
        assert self.reg.published_count == 1
        assert self.reg.archived_count == 1

    def test_clear(self):
        self.reg.register("s1", "sess-1")
        self.reg.clear()
        assert not self.reg.is_registered("s1")

    def test_not_running_raises(self):
        r = RecoverySnapshotRegistry()
        with pytest.raises(SnapshotNotRunningError):
            r.register("s", "sess")


# ════════════════════════════════════════════════════════════════════════════
# 14. RecoverySnapshotBundle
# ════════════════════════════════════════════════════════════════════════════

class TestRecoverySnapshotBundle:
    def test_empty_bundle(self):
        b = make_snapshot_bundle("sess-1", [])
        assert b.version_count == 0
        assert b.latest is None
        assert b.oldest is None
        assert not b.is_complete
        assert not b.is_successful

    def test_bundle_with_snapshots(self):
        sid = str(uuid.uuid4())
        s1 = _snap(recovery_session_id=sid, snapshot_version=1)
        s2 = _snap(recovery_session_id=sid, snapshot_version=2)
        b = make_snapshot_bundle(sid, [s2, s1])  # out-of-order input
        assert b.version_count == 2
        assert b.latest.snapshot_version == 2
        assert b.oldest.snapshot_version == 1

    def test_filters_to_matching_session(self):
        sid = str(uuid.uuid4())
        s1 = _snap(recovery_session_id=sid, snapshot_version=1)
        s2 = _snap()  # different session
        b = make_snapshot_bundle(sid, [s1, s2])
        assert b.version_count == 1

    def test_is_complete_when_terminal_state(self):
        sid = str(uuid.uuid4())
        s = _snap(recovery_session_id=sid, lifecycle_state="completed")
        b = make_snapshot_bundle(sid, [s])
        assert b.is_complete

    def test_is_not_complete_when_active(self):
        sid = str(uuid.uuid4())
        s = _snap(recovery_session_id=sid, lifecycle_state="recovering")
        b = make_snapshot_bundle(sid, [s])
        assert not b.is_complete

    def test_is_successful(self):
        sid = str(uuid.uuid4())
        s = _snap(recovery_session_id=sid, recovery_result=RecoveryResult.SUCCESS)
        b = make_snapshot_bundle(sid, [s])
        assert b.is_successful

    def test_version_lookup(self):
        sid = str(uuid.uuid4())
        s1 = _snap(recovery_session_id=sid, snapshot_version=3)
        b = make_snapshot_bundle(sid, [s1])
        assert b.version(3) is s1
        assert b.version(99) is None

    def test_frozen(self):
        b = make_snapshot_bundle("sess-1", [])
        with pytest.raises((AttributeError, TypeError)):
            b.bundle_id = "other"  # type: ignore[misc]

    def test_to_dict(self):
        sid = str(uuid.uuid4())
        s = _snap(recovery_session_id=sid)
        b = make_snapshot_bundle(sid, [s])
        d = b.to_dict()
        assert "bundle_id" in d
        assert "snapshots" in d
        assert len(d["snapshots"]) == 1


# ════════════════════════════════════════════════════════════════════════════
# 15. RecoverySnapshotBuilder
# ════════════════════════════════════════════════════════════════════════════

class TestRecoverySnapshotBuilder:
    def setup_method(self):
        self.builder = RecoverySnapshotBuilder()
        self.builder.start()

    def teardown_method(self):
        if self.builder.lifecycle_state() not in ("stopped", "STOPPED"):
            self.builder.stop()

    def _build(self, **kw) -> ExecutionRecoverySnapshot:
        return self.builder.build(
            kw.pop("lifecycle_session", _mock_session()),
            kw.pop("engine_response",  _mock_engine_response()),
            **kw,
        )

    def test_basic_build(self):
        s = self._build()
        assert s.snapshot_id
        assert s.recovery_session_id
        assert s.is_successful
        assert s.lifecycle_state == "completed"

    def test_all_sources(self):
        s = self.builder.build(
            _mock_session(workflow_id="wf-1", failure_id="f-1"),
            _mock_engine_response(outcome="success", duration=200.0),
            engine_snapshot  = MagicMock(),
            policy_decision  = _mock_policy_decision("FailoverPolicy", "failover"),
            failover_response = _mock_failover_response(
                action_executed="switch_broker", verification_passed=True
            ),
            workflow_id = "wf-1",
            broker_id   = "bk-1",
        )
        assert s.selected_recovery_policy  == "FailoverPolicy"
        assert s.executed_failover_strategy == "switch_broker"
        assert s.is_verified
        assert s.recovery_health == SnapshotHealth.HEALTHY

    def test_missing_lifecycle_session_raises(self):
        with pytest.raises(SnapshotBuildError) as exc_info:
            self.builder.build(None, _mock_engine_response())
        assert exc_info.value.reason == "missing_lifecycle_session"

    def test_missing_engine_response_raises(self):
        with pytest.raises(SnapshotBuildError) as exc_info:
            self.builder.build(_mock_session(), None)
        assert exc_info.value.reason == "missing_engine_response"

    def test_no_policy_no_failover(self):
        s = self._build()
        # Should still build with empty policy / failover fields
        assert isinstance(s.recovery_result, RecoveryResult)
        assert isinstance(s.verification_result, VerificationOutcome)

    def test_failed_recovery_result(self):
        s = self.builder.build(
            _mock_session(state="failed"),
            _mock_engine_response(outcome="failure"),
        )
        assert s.recovery_result == RecoveryResult.FAILURE

    def test_aborted_recovery_result(self):
        s = self.builder.build(
            _mock_session(state="aborted"),
            _mock_engine_response(outcome="aborted"),
        )
        assert s.recovery_result == RecoveryResult.ABORTED

    def test_partial_recovery_result(self):
        s = self.builder.build(
            _mock_session(),
            _mock_engine_response(outcome="partial"),
        )
        assert s.recovery_result == RecoveryResult.PARTIAL

    def test_unhealthy_when_not_operational(self):
        fo = _mock_failover_response(is_operational=False)
        s = self.builder.build(
            _mock_session(),
            _mock_engine_response(),
            failover_response=fo,
        )
        assert s.recovery_health == SnapshotHealth.UNHEALTHY

    def test_verification_failed_when_fo_failed(self):
        fo = _mock_failover_response(verification_passed=False)
        s = self.builder.build(
            _mock_session(),
            _mock_engine_response(),
            failover_response=fo,
        )
        assert s.verification_result == VerificationOutcome.FAILED

    def test_audit_metadata_populated(self):
        s = self._build()
        assert s.audit_metadata.audit_id
        assert s.audit_metadata.build_time_ms >= 0

    def test_recovery_statistics_from_engine(self):
        s = self.builder.build(
            _mock_session(),
            _mock_engine_response(stages_done=5, stages_total=6),
        )
        assert s.recovery_statistics["pipeline_stages_completed"] == 5

    def test_custom_metadata_merged(self):
        s = self.builder.build(
            _mock_session(),
            _mock_engine_response(),
            metadata={"custom": "value"},
        )
        assert s.recovery_metadata["custom"] == "value"

    def test_optional_ids_propagated(self):
        s = self.builder.build(
            _mock_session(workflow_id="wf-X"),
            _mock_engine_response(),
            gateway_id  = "gw-X",
            portfolio_id = "pf-X",
        )
        assert s.gateway_id   == "gw-X"
        assert s.portfolio_id == "pf-X"

    def test_not_running_raises(self):
        b = RecoverySnapshotBuilder()
        with pytest.raises(SnapshotNotRunningError):
            b.build(_mock_session(), _mock_engine_response())

    def test_snapshot_version_custom(self):
        s = self._build(snapshot_version=3)
        assert s.snapshot_version == 3


# ════════════════════════════════════════════════════════════════════════════
# 16. Public surface
# ════════════════════════════════════════════════════════════════════════════

class TestPublicSurface:
    def test_primary_imports(self):
        from iios.execution.recovery.snapshot import (
            ExecutionRecoverySnapshot,
            RecoverySnapshotBuilder,
            RecoverySnapshotStore,
            RecoverySnapshotCache,
        )

    def test_exception_imports(self):
        from iios.execution.recovery.snapshot import (
            RecoverySnapshotError,
            SnapshotNotRunningError,
            SnapshotBuildError,
            SnapshotNotFoundError,
        )

    def test_constant_imports(self):
        from iios.execution.recovery.snapshot import VERSION, SYSTEM_ID, BUILDER_ID
        assert VERSION == "1.0.0"

    def test_enum_imports(self):
        from iios.execution.recovery.snapshot import (
            SnapshotStatus, RecoveryResult, VerificationOutcome, SnapshotHealth,
        )

    def test_factory_imports(self):
        from iios.execution.recovery.snapshot import (
            make_execution_recovery_snapshot,
            make_audit_metadata,
            make_snapshot_bundle,
        )

    def test_event_imports(self):
        from iios.execution.recovery.snapshot import (
            make_snapshot_created, make_snapshot_published,
            make_snapshot_archived, make_snapshot_cached,
        )


# ════════════════════════════════════════════════════════════════════════════
# 17. Edge cases
# ════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_to_json_round_trip(self):
        import json
        s = _snap(
            recovery_metadata={"key": "value"},
            recovery_statistics={"count": 10},
        )
        j = s.to_json()
        d = json.loads(j)
        assert d["recovery_metadata"]["key"] == "value"
        assert d["recovery_statistics"]["count"] == 10

    def test_unknown_outcome_maps_to_unknown_result(self):
        builder = RecoverySnapshotBuilder()
        builder.start()
        resp = _mock_engine_response(outcome="some_unknown_value")
        s = builder.build(_mock_session(), resp)
        assert s.recovery_result == RecoveryResult.UNKNOWN
        builder.stop()

    def test_no_action_needed_maps_to_success(self):
        builder = RecoverySnapshotBuilder()
        builder.start()
        resp = _mock_engine_response(outcome="no_action_needed")
        s = builder.build(_mock_session(), resp)
        assert s.recovery_result == RecoveryResult.SUCCESS
        builder.stop()

    def test_snapshot_with_all_optional_ids(self):
        s = make_execution_recovery_snapshot(
            recovery_session_id        = str(uuid.uuid4()),
            execution_session_id       = str(uuid.uuid4()),
            lifecycle_state            = "completed",
            recovery_result            = RecoveryResult.SUCCESS,
            verification_result        = VerificationOutcome.PASSED,
            recovery_duration_ms       = 1.0,
            execution_id               = "exec-1",
            workflow_id                = "wf-1",
            gateway_id                 = "gw-1",
            broker_id                  = "bk-1",
            portfolio_id               = "pf-1",
            strategy_id                = "st-1",
        )
        d = s.to_dict()
        assert d["execution_id"]  == "exec-1"
        assert d["gateway_id"]    == "gw-1"
        assert d["portfolio_id"]  == "pf-1"
        assert d["strategy_id"]   == "st-1"

    def test_builder_with_none_failover_verification(self):
        """When failover_response has no verification_report, use is_successful."""
        builder = RecoverySnapshotBuilder()
        builder.start()
        fo = MagicMock()
        fo.is_successful  = True
        fo.is_operational = True
        fo.result = MagicMock()
        fo.result.action_executed = MagicMock()
        fo.result.action_executed.value = "retry"
        fo.verification_report = None
        fo.response_time_ms = 5.0
        s = builder.build(_mock_session(), _mock_engine_response(), failover_response=fo)
        assert s.verification_result == VerificationOutcome.SKIPPED
        builder.stop()

    def test_store_by_timestamp_range_with_no_before(self):
        store = RecoverySnapshotStore()
        store.start()
        now = time.time()
        s1 = make_execution_recovery_snapshot(
            recovery_session_id  = str(uuid.uuid4()),
            execution_session_id = str(uuid.uuid4()),
            lifecycle_state      = "completed",
            recovery_result      = RecoveryResult.SUCCESS,
            verification_result  = VerificationOutcome.PASSED,
            recovery_duration_ms = 10.0,
            timestamp            = now,
        )
        store.save(s1)
        results = store.by_timestamp_range(since=now - 1)
        assert len(results) >= 1
        store.stop()

    def test_bundle_to_dict_includes_snapshot_dicts(self):
        sid = str(uuid.uuid4())
        s = _snap(recovery_session_id=sid, recovery_result=RecoveryResult.SUCCESS)
        b = make_snapshot_bundle(sid, [s])
        d = b.to_dict()
        assert d["is_successful"] is True
        assert d["version_count"] == 1

    def test_concurrent_builder_builds(self):
        builder = RecoverySnapshotBuilder()
        builder.start()
        errors = []
        results = []
        lock = threading.Lock()

        def worker():
            try:
                s = builder.build(_mock_session(), _mock_engine_response())
                with lock:
                    results.append(s)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent errors: {errors}"
        assert len(results) == 20
        ids = {s.snapshot_id for s in results}
        assert len(ids) == 20   # all unique
        builder.stop()
