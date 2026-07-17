"""tests/unit/execution/gateway/snapshot/test_gateway_snapshot.py
==============================================================
Unit tests for C6 Phase 5 M5 — Execution Gateway Snapshot.

~240 tests across 16 test classes.
"""
from __future__ import annotations

import time
import threading
import uuid
from typing import List
from unittest.mock import MagicMock

import pytest

from iios.execution.gateway.snapshot import (
    ACTIVE_GATEWAY_STATES,
    ACTOR_SNAPSHOT_BUILDER,
    ACTOR_SNAPSHOT_STORE,
    ACTOR_SNAPSHOT_SYSTEM,
    DEFAULT_MAX_CACHE_SIZE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SNAPSHOTS,
    SCHEMA_VERSION,
    SNAPSHOT_STORE_SYSTEM_ID,
    SUCCESSFUL_DISPATCH_STATUSES,
    TERMINAL_GATEWAY_STATES,
    VERSION,
    DispatchStatus,
    DuplicateSnapshotError,
    ExecutionGatewaySnapshot,
    GatewaySnapshotBuilder,
    GatewaySnapshotBundle,
    GatewaySnapshotCache,
    GatewaySnapshotError,
    GatewaySnapshotFactory,
    GatewaySnapshotHistory,
    GatewaySnapshotMetadata,
    GatewaySnapshotRegistry,
    GatewaySnapshotStatistics,
    GatewaySnapshotStore,
    GatewaySnapshotValidationResult,
    GatewaySnapshotValidator,
    GatewayState,
    GatewayStatus,
    QueueStatus,
    SnapshotBuildError,
    SnapshotEvent,
    SnapshotEventType,
    SnapshotNotFoundError,
    SnapshotStoreCapacityError,
    SnapshotStoreNotRunningError,
    SnapshotValidationError,
    SnapshotVersionError,
    make_audit_metadata,
    make_bundle_from_snapshots,
    make_snapshot_archived_event,
    make_snapshot_cached_event,
    make_snapshot_created_event,
    make_snapshot_published_event,
    make_snapshot_retrieved_event,
    make_snapshot_validated_event,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_snapshot(
    gateway_id:    str = "gw-test",
    execution_id:  str = "exec-test",
    order_id:      str = "ord-test",
    portfolio_id:  str = "port-test",
    strategy_id:   str = "strat-test",
    **kwargs,
) -> ExecutionGatewaySnapshot:
    return GatewaySnapshotFactory.create_snapshot(
        gateway_id=gateway_id,
        execution_id=execution_id,
        order_id=order_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        **kwargs,
    )


def _started_store(**kwargs) -> GatewaySnapshotStore:
    store = GatewaySnapshotStore(**kwargs)
    store.start()
    return store


# ─────────────────────────────────────────────────────────────────────────────
# TestConstants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_version_string(self):
        assert VERSION == "1.0.0"

    def test_schema_version_string(self):
        assert SCHEMA_VERSION == "1.0"

    def test_default_max_snapshots(self):
        assert DEFAULT_MAX_SNAPSHOTS == 10_000

    def test_default_max_history(self):
        assert DEFAULT_MAX_HISTORY == 5_000

    def test_default_max_cache_size(self):
        assert DEFAULT_MAX_CACHE_SIZE == 500

    def test_actor_constants_non_empty(self):
        assert ACTOR_SNAPSHOT_STORE
        assert ACTOR_SNAPSHOT_BUILDER
        assert ACTOR_SNAPSHOT_SYSTEM

    def test_terminal_states(self):
        assert GatewayState.COMPLETED in TERMINAL_GATEWAY_STATES
        assert GatewayState.FAILED    in TERMINAL_GATEWAY_STATES

    def test_active_states_excludes_terminal(self):
        for s in TERMINAL_GATEWAY_STATES:
            assert s not in ACTIVE_GATEWAY_STATES

    def test_successful_dispatch_statuses(self):
        assert DispatchStatus.DISPATCHED    in SUCCESSFUL_DISPATCH_STATUSES
        assert DispatchStatus.ACKNOWLEDGED  in SUCCESSFUL_DISPATCH_STATUSES
        assert DispatchStatus.COMPLETED     in SUCCESSFUL_DISPATCH_STATUSES
        assert DispatchStatus.FAILED not in SUCCESSFUL_DISPATCH_STATUSES

    def test_gateway_state_enum_values(self):
        assert GatewayState.READY.value == "READY"
        assert GatewayState.FAILED.value == "FAILED"

    def test_gateway_status_enum_values(self):
        assert GatewayStatus.HEALTHY.value == "HEALTHY"
        assert GatewayStatus.OFFLINE.value == "OFFLINE"

    def test_dispatch_status_enum_values(self):
        assert DispatchStatus.PENDING.value == "PENDING"
        assert DispatchStatus.COMPLETED.value == "COMPLETED"

    def test_queue_status_enum_values(self):
        assert QueueStatus.EMPTY.value == "EMPTY"
        assert QueueStatus.FULL.value  == "FULL"

    def test_snapshot_event_types(self):
        assert SnapshotEventType.SNAPSHOT_CREATED.value  == "SNAPSHOT_CREATED"
        assert SnapshotEventType.SNAPSHOT_PUBLISHED.value == "SNAPSHOT_PUBLISHED"


# ─────────────────────────────────────────────────────────────────────────────
# TestExceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_gateway_snapshot_error_is_base(self):
        err = GatewaySnapshotError("base")
        assert isinstance(err, Exception)

    def test_snapshot_build_error_message(self):
        err = SnapshotBuildError("missing field")
        assert err.error_code == "GS-001"
        assert "missing field" in str(err)

    def test_snapshot_validation_error_carries_errors(self):
        err = SnapshotValidationError("invalid", errors=("e1", "e2"))
        assert err.error_code == "GS-002"
        assert err.errors == ("e1", "e2")

    def test_snapshot_not_found_error(self):
        err = SnapshotNotFoundError("snap-123")
        assert "snap-123" in str(err)
        assert err.error_code == "GS-003"

    def test_duplicate_snapshot_error(self):
        err = DuplicateSnapshotError("snap-dup")
        assert "snap-dup" in str(err)
        assert err.error_code == "GS-004"

    def test_snapshot_version_error(self):
        err = SnapshotVersionError("version mismatch")
        assert err.error_code == "GS-005"

    def test_store_not_running_error(self):
        err = SnapshotStoreNotRunningError()
        assert err.error_code == "GS-006"

    def test_store_capacity_error(self):
        err = SnapshotStoreCapacityError(1000)
        assert "1000" in str(err)
        assert err.error_code == "GS-007"

    def test_all_inherit_from_base(self):
        errors = [
            SnapshotBuildError("x"),
            SnapshotValidationError("x", errors=()),
            SnapshotNotFoundError("x"),
            DuplicateSnapshotError("x"),
            SnapshotVersionError("x"),
            SnapshotStoreNotRunningError(),
            SnapshotStoreCapacityError(1),
        ]
        for e in errors:
            assert isinstance(e, GatewaySnapshotError)


# ─────────────────────────────────────────────────────────────────────────────
# TestSnapshotMetadata
# ─────────────────────────────────────────────────────────────────────────────

class TestSnapshotMetadata:
    def test_create_metadata(self):
        m = make_audit_metadata("snap-1", source_system="sys", created_by="user",
                                environment="PROD", tags=None, notes="n")
        assert m.snapshot_id == "snap-1"
        assert m.environment == "PROD"

    def test_metadata_is_frozen(self):
        m = make_audit_metadata("snap-1", source_system="sys", created_by="user",
                                environment="PROD")
        with pytest.raises((TypeError, AttributeError)):
            m.environment = "DEV"  # type: ignore

    def test_is_production(self):
        m = make_audit_metadata("s", source_system="s", created_by="s",
                                environment="PROD")
        assert m.is_production is True
        m2 = make_audit_metadata("s", source_system="s", created_by="s",
                                 environment="DEV")
        assert m2.is_production is False

    def test_has_tags_and_notes(self):
        m = make_audit_metadata("s", source_system="s", created_by="s",
                                environment="PROD", tags=("tag1",), notes="hello")
        assert m.has_tags is True
        assert m.has_notes is True

    def test_to_dict_keys(self):
        m = make_audit_metadata("snap-1", source_system="sys", created_by="user",
                                environment="PROD")
        d = m.to_dict()
        assert "snapshot_id" in d
        assert "environment" in d
        assert "created_at" in d

    def test_custom_fields(self):
        m = GatewaySnapshotMetadata(
            snapshot_id="s", source_system="sys", created_by="u",
            environment="PROD", schema_version="1.0", custom={"k": "v"},
        )
        assert m.custom["k"] == "v"


# ─────────────────────────────────────────────────────────────────────────────
# TestExecutionGatewaySnapshot
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionGatewaySnapshot:
    def test_create_minimal(self):
        snap = _make_snapshot()
        assert snap.gateway_id == "gw-test"
        assert snap.execution_id == "exec-test"

    def test_snapshot_id_is_uuid(self):
        snap = _make_snapshot()
        uuid.UUID(snap.snapshot_id)  # should not raise

    def test_is_frozen(self):
        snap = _make_snapshot()
        with pytest.raises((TypeError, AttributeError)):
            snap.gateway_id = "modified"  # type: ignore

    def test_default_state_ready(self):
        snap = _make_snapshot()
        assert snap.gateway_state == GatewayState.READY

    def test_is_terminal_false_for_ready(self):
        snap = _make_snapshot()
        assert snap.is_terminal is False

    def test_is_terminal_true_for_completed(self):
        snap = _make_snapshot(gateway_state=GatewayState.COMPLETED)
        assert snap.is_terminal is True

    def test_is_terminal_true_for_failed(self):
        snap = _make_snapshot(gateway_state=GatewayState.FAILED)
        assert snap.is_terminal is True

    def test_is_active_for_processing(self):
        snap = _make_snapshot(gateway_state=GatewayState.PROCESSING)
        assert snap.is_active is True

    def test_is_completed(self):
        snap = _make_snapshot(gateway_state=GatewayState.COMPLETED)
        assert snap.is_completed is True

    def test_is_failed(self):
        snap = _make_snapshot(gateway_state=GatewayState.FAILED)
        assert snap.is_failed is True

    def test_is_routed_with_broker(self):
        snap = _make_snapshot(selected_broker_id="broker-1")
        assert snap.is_routed is True

    def test_is_routed_without_broker(self):
        snap = _make_snapshot()
        assert snap.is_routed is False

    def test_is_dispatched(self):
        snap = _make_snapshot(dispatch_status=DispatchStatus.DISPATCHED)
        assert snap.is_dispatched is True

    def test_has_failure_with_reason(self):
        snap = _make_snapshot(
            gateway_state=GatewayState.FAILED,
            failure_reason="timeout",
        )
        assert snap.has_failure is True

    def test_has_failure_without_reason(self):
        snap = _make_snapshot()
        assert snap.has_failure is False

    def test_has_retried(self):
        snap = _make_snapshot(retry_count=2)
        assert snap.has_retried is True

    def test_has_not_retried(self):
        snap = _make_snapshot(retry_count=0)
        assert snap.has_retried is False

    def test_is_healthy(self):
        snap = _make_snapshot(gateway_status=GatewayStatus.HEALTHY)
        assert snap.is_healthy is True

    def test_not_healthy_degraded(self):
        snap = _make_snapshot(gateway_status=GatewayStatus.DEGRADED)
        assert snap.is_healthy is False

    def test_estimated_size_positive(self):
        snap = _make_snapshot()
        assert snap.estimated_size_bytes > 0

    def test_to_dict_completeness(self):
        snap = _make_snapshot()
        d = snap.to_dict()
        required = [
            "snapshot_id", "gateway_id", "execution_id", "order_id",
            "portfolio_id", "strategy_id", "gateway_state", "lifecycle_state",
            "dispatch_status", "queue_status", "retry_count",
            "processing_duration_ms", "created_at", "framework_version",
        ]
        for key in required:
            assert key in d, f"Missing key: {key}"

    def test_to_dict_includes_derived_flags(self):
        snap = _make_snapshot(gateway_state=GatewayState.COMPLETED)
        d = snap.to_dict()
        assert d["is_terminal"] is True
        assert d.get("is_completed", snap.is_completed) is True

    def test_framework_version(self):
        snap = _make_snapshot()
        assert snap.framework_version == VERSION


# ─────────────────────────────────────────────────────────────────────────────
# TestSnapshotBundle
# ─────────────────────────────────────────────────────────────────────────────

class TestSnapshotBundle:
    def _three_snaps(self) -> List[ExecutionGatewaySnapshot]:
        return [
            _make_snapshot(execution_id="exec-1", order_id=f"ord-{i}")
            for i in range(3)
        ]

    def test_create_bundle(self):
        snaps = self._three_snaps()
        bundle = make_bundle_from_snapshots(snaps, "bundle-1")
        assert bundle.snapshot_count == 3
        assert bundle.bundle_name == "bundle-1"

    def test_bundle_is_frozen(self):
        bundle = make_bundle_from_snapshots(self._three_snaps(), "b")
        with pytest.raises((TypeError, AttributeError)):
            bundle.bundle_name = "new"  # type: ignore

    def test_bundle_contains(self):
        snaps = self._three_snaps()
        bundle = make_bundle_from_snapshots(snaps, "b")
        assert bundle.contains(snaps[0].snapshot_id)
        assert not bundle.contains("non-existent")

    def test_bundle_is_not_empty(self):
        bundle = make_bundle_from_snapshots(self._three_snaps(), "b")
        assert bundle.is_empty is False

    def test_bundle_time_span(self):
        snaps = self._three_snaps()
        bundle = make_bundle_from_snapshots(snaps, "b")
        assert bundle.time_span_seconds >= 0

    def test_bundle_age_positive(self):
        bundle = make_bundle_from_snapshots(self._three_snaps(), "b")
        assert bundle.age_seconds >= 0

    def test_bundle_requires_same_execution_id(self):
        snaps = [
            _make_snapshot(execution_id="exec-1"),
            _make_snapshot(execution_id="exec-2"),  # different
        ]
        with pytest.raises(ValueError):
            make_bundle_from_snapshots(snaps, "b")

    def test_bundle_rejects_empty(self):
        with pytest.raises(ValueError):
            make_bundle_from_snapshots([], "b")


# ─────────────────────────────────────────────────────────────────────────────
# TestSnapshotEvents
# ─────────────────────────────────────────────────────────────────────────────

class TestSnapshotEvents:
    def test_make_created_event(self):
        ev = make_snapshot_created_event("snap-1")
        assert ev.event_type == SnapshotEventType.SNAPSHOT_CREATED
        assert ev.snapshot_id == "snap-1"

    def test_make_validated_event(self):
        ev = make_snapshot_validated_event("snap-1")
        assert ev.event_type == SnapshotEventType.SNAPSHOT_VALIDATED

    def test_make_published_event(self):
        ev = make_snapshot_published_event("snap-1")
        assert ev.event_type == SnapshotEventType.SNAPSHOT_PUBLISHED

    def test_make_archived_event(self):
        ev = make_snapshot_archived_event("snap-1")
        assert ev.event_type == SnapshotEventType.SNAPSHOT_ARCHIVED

    def test_make_retrieved_event(self):
        ev = make_snapshot_retrieved_event("snap-1")
        assert ev.event_type == SnapshotEventType.SNAPSHOT_RETRIEVED

    def test_make_cached_event(self):
        ev = make_snapshot_cached_event("snap-1")
        assert ev.event_type == SnapshotEventType.SNAPSHOT_CACHED

    def test_event_is_frozen(self):
        ev = make_snapshot_created_event("snap-1")
        with pytest.raises((TypeError, AttributeError)):
            ev.snapshot_id = "new"  # type: ignore

    def test_event_has_event_id(self):
        ev = make_snapshot_created_event("snap-1")
        uuid.UUID(ev.event_id)

    def test_event_occurred_at_positive(self):
        ev = make_snapshot_created_event("snap-1")
        assert ev.occurred_at > 0

    def test_event_optional_ids(self):
        ev = make_snapshot_created_event(
            "snap-1", execution_id="exec-1", gateway_id="gw-1"
        )
        assert ev.execution_id == "exec-1"
        assert ev.gateway_id == "gw-1"


# ─────────────────────────────────────────────────────────────────────────────
# TestSnapshotValidation
# ─────────────────────────────────────────────────────────────────────────────

class TestSnapshotValidation:
    def _valid_snap(self) -> ExecutionGatewaySnapshot:
        return _make_snapshot()

    def test_valid_snapshot_passes(self):
        validator = GatewaySnapshotValidator()
        result = validator.validate_snapshot(self._valid_snap())
        assert result.is_valid is True

    def test_validation_result_frozen(self):
        result = GatewaySnapshotValidationResult(is_valid=True, errors=(), warnings=())
        with pytest.raises((TypeError, AttributeError)):
            result.is_valid = False  # type: ignore

    def test_no_errors_on_valid(self):
        validator = GatewaySnapshotValidator()
        result = validator.validate_snapshot(self._valid_snap())
        assert len(result.errors) == 0

    def test_raise_if_invalid_raises(self):
        bad_result = GatewaySnapshotValidationResult(
            is_valid=False, errors=("error",), warnings=()
        )
        validator = GatewaySnapshotValidator()
        with pytest.raises(SnapshotValidationError):
            validator.raise_if_invalid(bad_result)

    def test_raise_if_valid_does_not_raise(self):
        ok_result = GatewaySnapshotValidationResult(
            is_valid=True, errors=(), warnings=()
        )
        GatewaySnapshotValidator().raise_if_invalid(ok_result)  # no exception

    def test_unknown_state_triggers_warning(self):
        snap = _make_snapshot(gateway_state=GatewayState.UNKNOWN)
        validator = GatewaySnapshotValidator()
        result = validator.validate_snapshot(snap)
        assert result.has_warnings

    def test_has_warnings_property(self):
        result = GatewaySnapshotValidationResult(
            is_valid=True, errors=(), warnings=("w1",)
        )
        assert result.has_warnings is True

    def test_to_dict(self):
        result = GatewaySnapshotValidationResult(
            is_valid=True, errors=(), warnings=("w",)
        )
        d = result.to_dict()
        assert "is_valid" in d
        assert "warnings" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestSnapshotBuilder
# ─────────────────────────────────────────────────────────────────────────────

class TestSnapshotBuilder:
    def _full_builder(self) -> GatewaySnapshotBuilder:
        b = GatewaySnapshotBuilder()
        b.set_identifiers(
            gateway_id="gw-1", execution_id="exec-1",
            order_id="ord-1", portfolio_id="port-1", strategy_id="strat-1",
        )
        return b

    def test_build_minimal(self):
        snap = self._full_builder().build()
        assert snap.gateway_id == "gw-1"
        assert snap.execution_id == "exec-1"

    def test_build_generates_uuid(self):
        snap = self._full_builder().build()
        uuid.UUID(snap.snapshot_id)  # no raise

    def test_builder_is_fluent(self):
        b = GatewaySnapshotBuilder()
        ret = b.set_identifiers(
            gateway_id="g", execution_id="e",
            order_id="o", portfolio_id="p", strategy_id="s",
        )
        assert ret is b

    def test_missing_required_raises(self):
        b = GatewaySnapshotBuilder()
        b.set_identifiers(
            gateway_id="g", execution_id="e",
            order_id="o", portfolio_id="p",
            strategy_id="",  # empty
        )
        with pytest.raises(SnapshotBuildError):
            b.build()

    def test_reset_clears_state(self):
        b = self._full_builder()
        b.build()
        b.reset()
        with pytest.raises(SnapshotBuildError):
            b.build()  # identifiers gone

    def test_set_gateway_state(self):
        b = self._full_builder()
        b.set_gateway_state(
            gateway_state=GatewayState.PROCESSING,
            lifecycle_state="RUNNING",
            gateway_status=GatewayStatus.HEALTHY,
        )
        snap = b.build()
        assert snap.gateway_state == GatewayState.PROCESSING

    def test_set_routing(self):
        b = self._full_builder()
        b.set_routing(
            selected_broker_id="broker-1",
            selected_broker_name="Zerodha",
            routing_policy_id="policy-1",
        )
        snap = b.build()
        assert snap.selected_broker_id == "broker-1"
        assert snap.selected_broker_name == "Zerodha"

    def test_set_dispatch(self):
        b = self._full_builder()
        b.set_dispatch(dispatch_status=DispatchStatus.DISPATCHED,
                       queue_status=QueueStatus.PROCESSING)
        snap = b.build()
        assert snap.dispatch_status == DispatchStatus.DISPATCHED

    def test_set_retry(self):
        b = self._full_builder()
        b.set_retry(retry_count=3, failure_reason="timeout")
        snap = b.build()
        assert snap.retry_count == 3
        assert snap.failure_reason == "timeout"

    def test_set_processing_duration(self):
        b = self._full_builder()
        b.set_processing_duration(42.5)
        snap = b.build()
        assert snap.processing_duration_ms == pytest.approx(42.5)

    def test_set_broker_capabilities(self):
        b = self._full_builder()
        b.set_broker_capabilities(("EQUITY", "OPTIONS"))
        snap = b.build()
        assert "EQUITY" in snap.broker_capability_summary

    def test_set_audit_metadata_from_object(self):
        meta = make_audit_metadata("snap-1", source_system="sys",
                                   created_by="user", environment="PROD")
        b = self._full_builder()
        b.set_audit_metadata(meta)
        snap = b.build()
        assert snap.audit_metadata.get("snapshot_id") == "snap-1"

    def test_set_audit_metadata_from_dict(self):
        b = self._full_builder()
        b.set_audit_metadata({"key": "value"})
        snap = b.build()
        assert snap.audit_metadata.get("key") == "value"

    def test_set_routing_from_decision_duck_typing(self):
        mock_decision = MagicMock()
        mock_decision.selected_broker_id   = "broker-1"
        mock_decision.selected_broker_name  = "Zerodha"
        mock_decision.routing_policy_id     = "policy-1"
        mock_decision.outcome               = "SELECTED"
        b = self._full_builder()
        b.set_routing_from_decision(mock_decision)
        snap = b.build()
        assert snap.selected_broker_id == "broker-1"

    def test_snapshot_version_default_one(self):
        snap = self._full_builder().build()
        assert snap.snapshot_version == 1

    def test_snapshot_version_custom(self):
        b = self._full_builder()
        b.set_snapshot_version(5)
        snap = b.build()
        assert snap.snapshot_version == 5


# ─────────────────────────────────────────────────────────────────────────────
# TestSnapshotStatistics
# ─────────────────────────────────────────────────────────────────────────────

class TestSnapshotStatistics:
    def test_initial_zeros(self):
        s = GatewaySnapshotStatistics()
        assert s.snapshots_created == 0
        assert s.snapshots_published == 0

    def test_record_published(self):
        s = GatewaySnapshotStatistics()
        s.record_published()
        s.record_published()
        assert s.snapshots_published == 2

    def test_record_retrieved(self):
        s = GatewaySnapshotStatistics()
        s.record_retrieved()
        assert s.snapshots_retrieved == 1

    def test_record_archived(self):
        s = GatewaySnapshotStatistics()
        s.record_archived()
        assert s.snapshots_archived == 1

    def test_record_cached(self):
        s = GatewaySnapshotStatistics()
        s.record_cached()
        assert s.snapshots_cached == 1

    def test_validation_success_rate(self):
        s = GatewaySnapshotStatistics()
        s.record_validation_success()
        s.record_validation_success()
        s.record_validation_failure()
        assert s.validation_success_rate == pytest.approx(2 / 3)

    def test_validation_success_rate_zero_division(self):
        s = GatewaySnapshotStatistics()
        assert s.validation_success_rate == 0.0

    def test_average_build_time_ms(self):
        s = GatewaySnapshotStatistics()
        s.record_created(10.0)
        s.record_created(20.0)
        assert s.average_build_time_ms == pytest.approx(15.0)

    def test_average_snapshot_size(self):
        s = GatewaySnapshotStatistics()
        s.record_published()
        s.record_size(100)
        s.record_published()
        s.record_size(200)
        assert s.average_snapshot_size_bytes == pytest.approx(150.0, abs=1)

    def test_copy_is_independent(self):
        s = GatewaySnapshotStatistics()
        s.record_published()
        c = s.copy()
        c.record_published()
        assert s.snapshots_published == 1
        assert c.snapshots_published == 2

    def test_reset(self):
        s = GatewaySnapshotStatistics()
        s.record_published()
        s.reset()
        assert s.snapshots_published == 0

    def test_to_dict_keys(self):
        s = GatewaySnapshotStatistics()
        d = s.to_dict()
        assert "snapshots_published" in d
        assert "validation_success_rate" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestSnapshotHistory
# ─────────────────────────────────────────────────────────────────────────────

class TestSnapshotHistory:
    def test_append_and_all(self):
        h = GatewaySnapshotHistory(max_snapshots=10)
        s = _make_snapshot()
        h.append(s)
        assert len(h.all()) == 1

    def test_latest(self):
        h = GatewaySnapshotHistory(max_snapshots=10)
        s1 = _make_snapshot()
        s2 = _make_snapshot()
        h.append(s1)
        h.append(s2)
        assert h.latest() is s2

    def test_latest_empty(self):
        h = GatewaySnapshotHistory()
        assert h.latest() is None

    def test_bounded_max_snapshots(self):
        h = GatewaySnapshotHistory(max_snapshots=3)
        for _ in range(5):
            h.append(_make_snapshot())
        assert h.snapshot_count == 3

    def test_by_execution_id(self):
        h = GatewaySnapshotHistory(max_snapshots=20)
        s = _make_snapshot(execution_id="exec-X")
        h.append(s)
        h.append(_make_snapshot(execution_id="exec-Y"))
        result = h.by_execution_id("exec-X")
        assert len(result) == 1
        assert result[0].execution_id == "exec-X"

    def test_by_gateway_id(self):
        h = GatewaySnapshotHistory(max_snapshots=10)
        h.append(_make_snapshot(gateway_id="gw-A"))
        h.append(_make_snapshot(gateway_id="gw-B"))
        assert len(h.by_gateway_id("gw-A")) == 1

    def test_by_order_id(self):
        h = GatewaySnapshotHistory(max_snapshots=10)
        h.append(_make_snapshot(order_id="ord-Z"))
        assert len(h.by_order_id("ord-Z")) == 1

    def test_completed_filter(self):
        h = GatewaySnapshotHistory(max_snapshots=10)
        h.append(_make_snapshot(gateway_state=GatewayState.COMPLETED))
        h.append(_make_snapshot(gateway_state=GatewayState.READY))
        assert len(h.completed()) == 1

    def test_failed_filter(self):
        h = GatewaySnapshotHistory(max_snapshots=10)
        h.append(_make_snapshot(gateway_state=GatewayState.FAILED))
        h.append(_make_snapshot(gateway_state=GatewayState.READY))
        assert len(h.failed()) == 1

    def test_append_event(self):
        h = GatewaySnapshotHistory(max_events=10)
        ev = make_snapshot_created_event("snap-1")
        h.append_event(ev)
        assert h.event_count == 1

    def test_latest_event(self):
        h = GatewaySnapshotHistory(max_events=10)
        ev1 = make_snapshot_created_event("snap-1")
        ev2 = make_snapshot_validated_event("snap-1")
        h.append_event(ev1)
        h.append_event(ev2)
        assert h.latest_event() is ev2

    def test_clear(self):
        h = GatewaySnapshotHistory(max_snapshots=10)
        h.append(_make_snapshot())
        h.clear()
        assert h.snapshot_count == 0


# ─────────────────────────────────────────────────────────────────────────────
# TestSnapshotCache
# ─────────────────────────────────────────────────────────────────────────────

class TestSnapshotCache:
    def test_put_and_get(self):
        cache = GatewaySnapshotCache(max_size=10)
        s = _make_snapshot()
        cache.put(s)
        assert cache.get(s.snapshot_id) is s

    def test_get_unknown_returns_none(self):
        cache = GatewaySnapshotCache(max_size=10)
        assert cache.get("non-existent") is None

    def test_evict(self):
        cache = GatewaySnapshotCache(max_size=10)
        s = _make_snapshot()
        cache.put(s)
        cache.evict(s.snapshot_id)
        assert cache.get(s.snapshot_id) is None

    def test_evict_unknown_returns_false(self):
        cache = GatewaySnapshotCache(max_size=10)
        assert cache.evict("non-existent") is False

    def test_lru_eviction(self):
        cache = GatewaySnapshotCache(max_size=2)
        s1 = _make_snapshot()
        s2 = _make_snapshot()
        s3 = _make_snapshot()
        cache.put(s1)
        cache.put(s2)
        evicted = cache.put(s3)
        assert evicted is True
        assert cache.get(s1.snapshot_id) is None  # LRU evicted
        assert cache.get(s2.snapshot_id) is s2
        assert cache.get(s3.snapshot_id) is s3

    def test_get_promotes_to_mru(self):
        cache = GatewaySnapshotCache(max_size=2)
        s1 = _make_snapshot()
        s2 = _make_snapshot()
        s3 = _make_snapshot()
        cache.put(s1)
        cache.put(s2)
        cache.get(s1.snapshot_id)  # promote s1 to MRU
        cache.put(s3)               # s2 is now LRU
        assert cache.get(s1.snapshot_id) is s1
        assert cache.get(s2.snapshot_id) is None  # evicted

    def test_peek_no_promotion(self):
        cache = GatewaySnapshotCache(max_size=2)
        s1 = _make_snapshot()
        s2 = _make_snapshot()
        s3 = _make_snapshot()
        cache.put(s1)
        cache.put(s2)
        cache.peek(s1.snapshot_id)  # NO promotion
        cache.put(s3)
        assert cache.get(s1.snapshot_id) is None  # s1 still LRU

    def test_size_and_is_full(self):
        cache = GatewaySnapshotCache(max_size=2)
        cache.put(_make_snapshot())
        assert cache.is_full is False
        cache.put(_make_snapshot())
        assert cache.is_full is True

    def test_is_empty(self):
        cache = GatewaySnapshotCache(max_size=5)
        assert cache.is_empty is True
        cache.put(_make_snapshot())
        assert cache.is_empty is False

    def test_contains(self):
        cache = GatewaySnapshotCache(max_size=5)
        s = _make_snapshot()
        cache.put(s)
        assert cache.contains(s.snapshot_id)
        assert not cache.contains("x")

    def test_clear(self):
        cache = GatewaySnapshotCache(max_size=5)
        cache.put(_make_snapshot())
        cache.clear()
        assert cache.is_empty

    def test_snapshot_ids_order(self):
        cache = GatewaySnapshotCache(max_size=3)
        s1 = _make_snapshot()
        s2 = _make_snapshot()
        cache.put(s1)
        cache.put(s2)
        ids = cache.snapshot_ids()
        assert ids[0] == s1.snapshot_id   # LRU first
        assert ids[1] == s2.snapshot_id   # MRU last


# ─────────────────────────────────────────────────────────────────────────────
# TestSnapshotRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestSnapshotRegistry:
    def _started(self) -> GatewaySnapshotRegistry:
        r = GatewaySnapshotRegistry(max_snapshots=100)
        r.start()
        return r

    def test_store_and_get(self):
        r = self._started()
        s = _make_snapshot()
        r.store(s)
        retrieved = r.get(s.snapshot_id)
        assert retrieved is s
        r.stop()

    def test_get_not_found_raises(self):
        r = self._started()
        with pytest.raises(SnapshotNotFoundError):
            r.get("non-existent")
        r.stop()

    def test_duplicate_raises(self):
        r = self._started()
        s = _make_snapshot()
        r.store(s)
        with pytest.raises(DuplicateSnapshotError):
            r.store(s)
        r.stop()

    def test_capacity_error(self):
        r = GatewaySnapshotRegistry(max_snapshots=1)
        r.start()
        r.store(_make_snapshot())
        with pytest.raises(SnapshotStoreCapacityError):
            r.store(_make_snapshot())
        r.stop()

    def test_not_running_raises(self):
        r = GatewaySnapshotRegistry()
        with pytest.raises(SnapshotStoreNotRunningError):
            r.store(_make_snapshot())

    def test_archive(self):
        r = self._started()
        s = _make_snapshot()
        r.store(s)
        r.archive(s.snapshot_id)
        assert r.is_archived(s.snapshot_id) is True
        r.stop()

    def test_archive_not_found_raises(self):
        r = self._started()
        with pytest.raises(SnapshotNotFoundError):
            r.archive("non-existent")
        r.stop()

    def test_all_returns_list(self):
        r = self._started()
        r.store(_make_snapshot())
        r.store(_make_snapshot())
        assert len(r.all()) == 2
        r.stop()

    def test_by_execution_id(self):
        r = self._started()
        r.store(_make_snapshot(execution_id="exec-A"))
        r.store(_make_snapshot(execution_id="exec-B"))
        result = r.by_execution_id("exec-A")
        assert len(result) == 1
        assert result[0].execution_id == "exec-A"
        r.stop()

    def test_by_order_id(self):
        r = self._started()
        r.store(_make_snapshot(order_id="ord-X"))
        result = r.by_order_id("ord-X")
        assert len(result) == 1
        r.stop()

    def test_by_gateway_state(self):
        r = self._started()
        r.store(_make_snapshot(gateway_state=GatewayState.COMPLETED))
        r.store(_make_snapshot(gateway_state=GatewayState.READY))
        result = r.by_gateway_state("COMPLETED")
        assert len(result) == 1
        r.stop()

    def test_by_broker_id(self):
        r = self._started()
        r.store(_make_snapshot(selected_broker_id="broker-42"))
        result = r.by_broker_id("broker-42")
        assert len(result) == 1
        r.stop()

    def test_latest_for_execution(self):
        r = self._started()
        s1 = _make_snapshot(execution_id="exec-Z")
        time.sleep(0.01)
        s2 = _make_snapshot(execution_id="exec-Z")
        r.store(s1)
        r.store(s2)
        latest = r.latest_for_execution("exec-Z")
        assert latest is s2
        r.stop()

    def test_latest_returns_most_recent(self):
        r = self._started()
        s1 = _make_snapshot()
        time.sleep(0.01)
        s2 = _make_snapshot()
        r.store(s1)
        r.store(s2)
        assert r.latest() is s2
        r.stop()

    def test_latest_empty_returns_none(self):
        r = self._started()
        assert r.latest() is None
        r.stop()


# ─────────────────────────────────────────────────────────────────────────────
# TestSnapshotStore
# ─────────────────────────────────────────────────────────────────────────────

class TestSnapshotStore:
    def test_publish_and_get(self):
        store = _started_store()
        s = _make_snapshot()
        store.publish(s)
        r = store.get(s.snapshot_id)
        assert r is s
        store.stop()

    def test_not_running_publish_raises(self):
        store = GatewaySnapshotStore()
        with pytest.raises(SnapshotStoreNotRunningError):
            store.publish(_make_snapshot())

    def test_not_running_get_raises(self):
        store = GatewaySnapshotStore()
        with pytest.raises((SnapshotNotFoundError, Exception)):
            store.get("x")

    def test_get_not_found_raises(self):
        store = _started_store()
        with pytest.raises(SnapshotNotFoundError):
            store.get("non-existent")
        store.stop()

    def test_duplicate_publish_raises(self):
        store = _started_store()
        s = _make_snapshot()
        store.publish(s)
        with pytest.raises(DuplicateSnapshotError):
            store.publish(s)
        store.stop()

    def test_archive(self):
        store = _started_store()
        s = _make_snapshot()
        store.publish(s)
        store.archive(s.snapshot_id)
        assert store.is_archived(s.snapshot_id)
        store.stop()

    def test_archive_not_found_raises(self):
        store = _started_store()
        with pytest.raises(SnapshotNotFoundError):
            store.archive("non-existent")
        store.stop()

    def test_statistics_update_on_publish(self):
        store = _started_store()
        store.publish(_make_snapshot())
        stats = store.statistics()
        assert stats.snapshots_published == 1
        store.stop()

    def test_statistics_update_on_retrieve(self):
        store = _started_store()
        s = _make_snapshot()
        store.publish(s)
        store.get(s.snapshot_id)
        stats = store.statistics()
        assert stats.snapshots_retrieved >= 1
        store.stop()

    def test_event_listener_fired(self):
        store = _started_store()
        received: List[SnapshotEvent] = []
        store.add_event_listener(received.append)
        store.publish(_make_snapshot())
        assert any(e.event_type == SnapshotEventType.SNAPSHOT_PUBLISHED
                   for e in received)
        store.stop()

    def test_remove_event_listener(self):
        store = _started_store()
        received: List[SnapshotEvent] = []
        store.add_event_listener(received.append)
        store.remove_event_listener(received.append)
        store.publish(_make_snapshot())
        assert len(received) == 0
        store.stop()

    def test_next_version_for(self):
        store = _started_store()
        assert store.next_version_for("exec-1") == 1
        assert store.next_version_for("exec-1") == 2
        assert store.next_version_for("exec-2") == 1
        store.stop()

    def test_by_execution_id(self):
        store = _started_store()
        s = _make_snapshot(execution_id="exec-Q")
        store.publish(s)
        result = store.by_execution_id("exec-Q")
        assert len(result) == 1
        store.stop()

    def test_latest(self):
        store = _started_store()
        s1 = _make_snapshot()
        time.sleep(0.01)
        s2 = _make_snapshot()
        store.publish(s1)
        store.publish(s2)
        assert store.latest() is s2
        store.stop()

    def test_snapshot_dict(self):
        store = _started_store()
        d = store.snapshot()
        assert "system_id" in d
        assert "snapshot_count" in d
        store.stop()

    def test_cache_hit_path(self):
        store = _started_store()
        s = _make_snapshot()
        store.publish(s)
        # first get populates cache; second get should hit cache
        store.get(s.snapshot_id)
        store.get(s.snapshot_id)
        stats = store.statistics()
        assert stats.snapshots_retrieved >= 2
        store.stop()

    def test_history_receives_snapshot(self):
        store = _started_store()
        s = _make_snapshot()
        store.publish(s)
        h = store.history()
        assert h.snapshot_count >= 1
        store.stop()

    def test_capacity_error_on_full_store(self):
        store = GatewaySnapshotStore(max_snapshots=1)
        store.start()
        store.publish(_make_snapshot())
        with pytest.raises(SnapshotStoreCapacityError):
            store.publish(_make_snapshot())
        store.stop()


# ─────────────────────────────────────────────────────────────────────────────
# TestSnapshotFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestSnapshotFactory:
    def test_create_snapshot(self):
        s = GatewaySnapshotFactory.create_snapshot(
            gateway_id="gw-f", execution_id="exec-f",
            order_id="ord-f", portfolio_id="port-f", strategy_id="strat-f",
        )
        assert s.gateway_id == "gw-f"

    def test_create_metadata(self):
        m = GatewaySnapshotFactory.create_metadata("snap-1", source_system="sys",
                                                    created_by="u")
        assert m.snapshot_id == "snap-1"

    def test_create_bundle(self):
        snaps = [_make_snapshot(execution_id="exec-B") for _ in range(2)]
        bundle = GatewaySnapshotFactory.create_bundle(snaps, "factory-bundle")
        assert bundle.snapshot_count == 2

    def test_create_store(self):
        store = GatewaySnapshotFactory.create_store(max_snapshots=50)
        assert isinstance(store, GatewaySnapshotStore)

    def test_create_builder(self):
        b = GatewaySnapshotFactory.create_builder()
        assert isinstance(b, GatewaySnapshotBuilder)

    def test_create_snapshot_from_routing_decision(self):
        mock_decision = MagicMock()
        mock_decision.selected_broker_id   = "broker-99"
        mock_decision.selected_broker_name  = "Dhan"
        mock_decision.routing_policy_id     = "pol-1"
        mock_decision.outcome               = "SELECTED"
        s = GatewaySnapshotFactory.create_snapshot_from_routing_decision(
            routing_decision=mock_decision,
            gateway_id="gw-1", execution_id="exec-1",
            order_id="ord-1", portfolio_id="port-1", strategy_id="strat-1",
        )
        assert s.selected_broker_id == "broker-99"


# ─────────────────────────────────────────────────────────────────────────────
# TestConcurrency
# ─────────────────────────────────────────────────────────────────────────────

class TestConcurrency:
    def test_registry_concurrent_writes(self):
        r = GatewaySnapshotRegistry(max_snapshots=1000)
        r.start()
        errors: List[Exception] = []

        def writer():
            try:
                for _ in range(20):
                    r.store(_make_snapshot())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent registry writes raised: {errors}"
        assert r.snapshot_count == 100
        r.stop()

    def test_cache_concurrent_access(self):
        cache = GatewaySnapshotCache(max_size=50)
        errors: List[Exception] = []

        def worker():
            try:
                for _ in range(30):
                    s = _make_snapshot()
                    cache.put(s)
                    cache.get(s.snapshot_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_store_concurrent_publishes(self):
        store = GatewaySnapshotStore(max_snapshots=500)
        store.start()
        errors: List[Exception] = []

        def publisher():
            try:
                for _ in range(10):
                    store.publish(_make_snapshot())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=publisher) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert store.snapshot_count() == 50
        store.stop()

    def test_history_concurrent_appends(self):
        h = GatewaySnapshotHistory(max_snapshots=500)
        errors: List[Exception] = []

        def appender():
            try:
                for _ in range(20):
                    h.append(_make_snapshot())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=appender) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors


# ─────────────────────────────────────────────────────────────────────────────
# TestRegressionEdgeCases
# ─────────────────────────────────────────────────────────────────────────────

class TestRegressionEdgeCases:
    def test_snapshot_with_all_optional_ids_set(self):
        s = GatewaySnapshotFactory.create_snapshot(
            gateway_id="gw", execution_id="exec", order_id="ord",
            portfolio_id="port", strategy_id="strat",
            position_id="pos-1", workflow_id="wf-1", decision_id="dec-1",
        )
        assert s.position_id == "pos-1"
        assert s.workflow_id  == "wf-1"
        assert s.decision_id  == "dec-1"

    def test_registry_indexes_optional_ids(self):
        r = GatewaySnapshotRegistry(max_snapshots=100)
        r.start()
        s = GatewaySnapshotFactory.create_snapshot(
            gateway_id="gw", execution_id="exec", order_id="ord",
            portfolio_id="port", strategy_id="strat",
            position_id="pos-reg", workflow_id="wf-reg",
        )
        r.store(s)
        assert len(r.by_position_id("pos-reg")) == 1
        assert len(r.by_workflow_id("wf-reg"))  == 1
        r.stop()

    def test_store_lifecycle_start_stop_cycle(self):
        store = GatewaySnapshotStore()
        store.start()
        store.publish(_make_snapshot())
        store.stop()
        with pytest.raises(SnapshotStoreNotRunningError):
            store.publish(_make_snapshot())

    def test_builder_reuse_after_build(self):
        b = GatewaySnapshotBuilder()
        b.set_identifiers(
            gateway_id="g", execution_id="e",
            order_id="o", portfolio_id="p", strategy_id="s",
        )
        s1 = b.build()
        # builder auto-resets after build
        b.set_identifiers(
            gateway_id="g2", execution_id="e2",
            order_id="o2", portfolio_id="p2", strategy_id="s2",
        )
        s2 = b.build()
        assert s1.snapshot_id != s2.snapshot_id
        assert s2.gateway_id == "g2"

    def test_empty_broker_capability_tuple(self):
        s = _make_snapshot(broker_capability_summary=())
        assert s.broker_capability_summary == ()

    def test_failure_reason_none_when_no_failure(self):
        s = _make_snapshot()
        assert s.failure_reason is None

    def test_statistics_copy_after_operations(self):
        store = _started_store()
        store.publish(_make_snapshot())
        stats = store.statistics()
        assert stats.snapshots_published == 1
        # publishing more doesn't affect the copy
        store.publish(_make_snapshot())
        assert stats.snapshots_published == 1
        store.stop()

    def test_bundle_metadata_stored(self):
        snaps = [_make_snapshot(execution_id="exec-M") for _ in range(2)]
        bundle = make_bundle_from_snapshots(snaps, "b", metadata={"key": "val"})
        assert bundle.metadata.get("key") == "val"

    def test_validation_error_carries_multiple_errors(self):
        err = SnapshotValidationError("multi", errors=("e1", "e2", "e3"))
        assert len(err.errors) == 3

    def test_history_event_bounded(self):
        h = GatewaySnapshotHistory(max_events=3)
        for _ in range(5):
            h.append_event(make_snapshot_created_event("snap-1"))
        assert h.event_count == 3
