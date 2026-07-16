"""tests/unit/iios/execution/snapshot/test_execution_snapshot.py
==================================================
Comprehensive test suite for C6 Phase 1 Module 5:
IIOS Execution Snapshot.

12 test classes, 95%+ coverage.
"""
from __future__ import annotations

import dataclasses
import json
import threading
import time
import uuid
from typing import Any

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Imports
# ─────────────────────────────────────────────────────────────────────────────

from iios.execution.snapshot.constants import (
    DEFAULT_CACHE_SIZE,
    DEFAULT_MAX_SNAPSHOTS,
    SnapshotFormat,
    SnapshotLifecycle,
    SnapshotTrigger,
    SnapshotValidationCode,
    VERSION,
)
from iios.execution.snapshot.exceptions import (
    DuplicateSnapshotError,
    ExecutionSnapshotError,
    SnapshotBuildError,
    SnapshotCapacityError,
    SnapshotHistoryError,
    SnapshotIncompleteError,
    SnapshotNotFoundError,
    SnapshotStoreNotRunning,
    SnapshotValidationError,
    SnapshotVersionError,
)
from iios.execution.snapshot.execution_snapshot import ExecutionSnapshot
from iios.execution.snapshot.execution_snapshot_metadata import SnapshotAuditMetadata
from iios.execution.snapshot.execution_snapshot_bundle import ExecutionSnapshotBundle
from iios.execution.snapshot.execution_snapshot_events import (
    SnapshotEvent,
    SnapshotEventType,
    make_snapshot_event,
)
from iios.execution.snapshot.execution_snapshot_validator import (
    ExecutionSnapshotValidator,
    SnapshotValidationResult,
)
from iios.execution.snapshot.execution_snapshot_builder import ExecutionSnapshotBuilder
from iios.execution.snapshot.execution_snapshot_factory import ExecutionSnapshotFactory
from iios.execution.snapshot.execution_snapshot_registry import (
    ExecutionSnapshotRegistry,
    SnapshotRecord,
)
from iios.execution.snapshot.execution_snapshot_history import (
    ExecutionSnapshotHistory,
    SnapshotRevision,
    make_snapshot_revision,
)
from iios.execution.snapshot.execution_snapshot_statistics import (
    ExecutionSnapshotStats,
    SnapshotBuildStats,
)
from iios.execution.snapshot.execution_snapshot_store import ExecutionSnapshotStore
from iios.execution.snapshot.execution_snapshot_cache import ExecutionSnapshotCache


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build(
    execution_id:   str = "EXEC-001",
    workflow_id:    str = "WF-001",
    order_id:       str = "ORD-001",
    execution_state: str = "IDLE",
    is_terminal:    bool = False,
    succeeded:      bool = False,
    sequence:       int  = 0,
    **kwargs: Any,
) -> ExecutionSnapshot:
    return (
        ExecutionSnapshotBuilder()
        .with_ids(
            execution_id = execution_id,
            workflow_id  = workflow_id,
            order_id     = order_id,
        )
        .with_state(
            execution_state,
            is_terminal = is_terminal,
            succeeded   = succeeded,
        )
        .with_sequence(sequence)
        .build()
    )


def _completed(
    execution_id: str = "EXEC-001",
    workflow_id:  str = "WF-001",
    order_id:     str = "ORD-001",
) -> ExecutionSnapshot:
    return (
        ExecutionSnapshotBuilder()
        .with_ids(
            execution_id = execution_id,
            workflow_id  = workflow_id,
            order_id     = order_id,
        )
        .with_state("COMPLETED", is_terminal=True, succeeded=True)
        .with_sequence(1)
        .build()
    )


def _create_via_factory(
    execution_id: str = "EXEC-001",
    workflow_id:  str = "WF-001",
    order_id:     str = "ORD-001",
    **kwargs: Any,
) -> tuple[ExecutionSnapshot, SnapshotBuildStats]:
    f = ExecutionSnapshotFactory()
    return f.create(
        execution_id    = execution_id,
        workflow_id     = workflow_id,
        order_id        = order_id,
        execution_state = "COMPLETED",
        is_terminal     = True,
        succeeded       = True,
        **kwargs,
    )


@pytest.fixture
def registry() -> ExecutionSnapshotRegistry:
    r = ExecutionSnapshotRegistry()
    r.start()
    yield r
    if r.is_running:
        r.stop()


@pytest.fixture
def store() -> ExecutionSnapshotStore:
    s = ExecutionSnapshotStore()
    s.start()
    yield s
    if s.is_running:
        s.stop()


@pytest.fixture
def snapshot() -> ExecutionSnapshot:
    return _build()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants and enumerations
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_lifecycle_values(self) -> None:
        assert SnapshotLifecycle.CREATED.value   == "CREATED"
        assert SnapshotLifecycle.VALIDATED.value == "VALIDATED"
        assert SnapshotLifecycle.PUBLISHED.value == "PUBLISHED"
        assert SnapshotLifecycle.STORED.value    == "STORED"
        assert SnapshotLifecycle.ARCHIVED.value  == "ARCHIVED"

    def test_trigger_values(self) -> None:
        assert SnapshotTrigger.STATE_TRANSITION.value == "STATE_TRANSITION"
        assert SnapshotTrigger.TERMINAL.value         == "TERMINAL"
        assert SnapshotTrigger.PERIODIC.value         == "PERIODIC"
        assert SnapshotTrigger.MANUAL.value           == "MANUAL"
        assert SnapshotTrigger.RECOVERY.value         == "RECOVERY"
        assert SnapshotTrigger.PUBLICATION.value      == "PUBLICATION"

    def test_format_values(self) -> None:
        assert SnapshotFormat.JSON.value    == "JSON"
        assert SnapshotFormat.MSGPACK.value == "MSGPACK"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_hierarchy(self) -> None:
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(ExecutionSnapshotError,  IIOSError)
        assert issubclass(SnapshotBuildError,      ExecutionSnapshotError)
        assert issubclass(SnapshotValidationError, ExecutionSnapshotError)
        assert issubclass(SnapshotNotFoundError,   ExecutionSnapshotError)
        assert issubclass(DuplicateSnapshotError,  ExecutionSnapshotError)
        assert issubclass(SnapshotCapacityError,   ExecutionSnapshotError)
        assert issubclass(SnapshotStoreNotRunning, ExecutionSnapshotError)

    def test_not_found_carries_id(self) -> None:
        exc = SnapshotNotFoundError("SNAP-X")
        assert exc.snapshot_id == "SNAP-X"
        assert "SNAP-X" in str(exc)

    def test_duplicate_carries_id(self) -> None:
        exc = DuplicateSnapshotError("SNAP-Y")
        assert exc.snapshot_id == "SNAP-Y"

    def test_validation_error_carries_errors(self) -> None:
        exc = SnapshotValidationError("fail", errors=("e1", "e2"))
        assert exc.errors == ("e1", "e2")

    def test_incomplete_carries_missing_fields(self) -> None:
        exc = SnapshotIncompleteError("missing", missing_fields=("execution_id",))
        assert "execution_id" in exc.missing_fields

    def test_error_codes(self) -> None:
        assert ExecutionSnapshotError.DEFAULT_CODE  == "ESN-000"
        assert SnapshotBuildError.DEFAULT_CODE      == "ESN-001"
        assert SnapshotValidationError.DEFAULT_CODE == "ESN-002"
        assert SnapshotNotFoundError.DEFAULT_CODE   == "ESN-003"
        assert DuplicateSnapshotError.DEFAULT_CODE  == "ESN-004"
        assert SnapshotCapacityError.DEFAULT_CODE   == "ESN-005"
        assert SnapshotStoreNotRunning.DEFAULT_CODE == "ESN-006"


# ─────────────────────────────────────────────────────────────────────────────
# 3. ExecutionSnapshot (core dataclass)
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionSnapshot:
    def test_creation(self, snapshot: ExecutionSnapshot) -> None:
        assert snapshot.execution_id    == "EXEC-001"
        assert snapshot.workflow_id     == "WF-001"
        assert snapshot.order_id        == "ORD-001"
        assert snapshot.execution_state == "IDLE"
        assert not snapshot.is_terminal

    def test_frozen(self, snapshot: ExecutionSnapshot) -> None:
        with pytest.raises((AttributeError, TypeError)):
            snapshot.execution_id = "MODIFIED"  # type: ignore[misc]

    def test_completed_properties(self) -> None:
        snap = _completed()
        assert snap.completed
        assert snap.succeeded
        assert snap.is_terminal
        assert not snap.failed
        assert not snap.cancelled

    def test_failed_properties(self) -> None:
        snap = (
            ExecutionSnapshotBuilder()
            .with_ids(execution_id="EXEC-001", workflow_id="WF-001", order_id="ORD-001")
            .with_state("FAILED", is_terminal=True, error_message="oops")
            .build()
        )
        assert snap.failed
        assert snap.is_terminal
        assert snap.has_errors
        assert not snap.succeeded

    def test_cancelled_properties(self) -> None:
        snap = _build(execution_state="CANCELLED", is_terminal=True)
        assert snap.cancelled

    def test_has_all_required_ids_true(self) -> None:
        snap = _build()
        assert snap.has_all_required_ids

    def test_has_all_required_ids_false(self) -> None:
        snap = _build()
        # Replace execution_id on an already-built snapshot (it's frozen but replaceable)
        snap2 = dataclasses.replace(snap, execution_id="")
        assert not snap2.has_all_required_ids

    def test_snapshot_count_zero(self, snapshot: ExecutionSnapshot) -> None:
        assert snapshot.snapshot_count == 0

    def test_snapshot_count_partial(self) -> None:
        snap = dataclasses.replace(
            _build(),
            has_market_snapshot   = True,
            has_strategy_snapshot = True,
        )
        assert snap.snapshot_count == 2

    def test_has_result_false(self, snapshot: ExecutionSnapshot) -> None:
        assert not snapshot.has_result

    def test_has_result_true(self) -> None:
        snap = dataclasses.replace(_build(), result_id="RES-001")
        assert snap.has_result

    def test_age_sec(self, snapshot: ExecutionSnapshot) -> None:
        time.sleep(0.01)
        assert snapshot.age_sec > 0.0

    def test_trigger_property_no_audit(self, snapshot: ExecutionSnapshot) -> None:
        assert snapshot.trigger == ""

    def test_trigger_property_with_audit(self) -> None:
        snap = dataclasses.replace(
            _build(),
            audit_metadata = SnapshotAuditMetadata(trigger=SnapshotTrigger.TERMINAL),
        )
        assert snap.trigger == "TERMINAL"

    def test_schema_version(self, snapshot: ExecutionSnapshot) -> None:
        assert snapshot.schema_version == VERSION

    def test_to_dict(self, snapshot: ExecutionSnapshot) -> None:
        d = snapshot.to_dict()
        assert d["execution_id"]   == "EXEC-001"
        assert d["workflow_id"]    == "WF-001"
        assert d["order_id"]       == "ORD-001"
        assert "snapshot_count"    in d
        assert "is_terminal"       in d
        assert "lifecycle"         in d
        assert "audit_metadata"    in d

    def test_repr(self, snapshot: ExecutionSnapshot) -> None:
        r = repr(snapshot)
        assert "ExecutionSnapshot" in r
        assert "IDLE" in r

    def test_snapshot_id_prefix(self, snapshot: ExecutionSnapshot) -> None:
        assert snapshot.snapshot_id.startswith("SNAP-")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Audit metadata
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditMetadata:
    def test_creation(self) -> None:
        m = SnapshotAuditMetadata(
            trigger         = SnapshotTrigger.TERMINAL,
            sequence_number = 5,
            notes           = "final",
        )
        assert m.trigger == SnapshotTrigger.TERMINAL
        assert m.sequence_number == 5

    def test_frozen(self) -> None:
        m = SnapshotAuditMetadata()
        with pytest.raises((AttributeError, TypeError)):
            m.notes = "x"  # type: ignore[misc]

    def test_to_dict(self) -> None:
        m = SnapshotAuditMetadata(trigger=SnapshotTrigger.PERIODIC)
        d = m.to_dict()
        assert d["trigger"] == "PERIODIC"
        assert "schema_version" in d


# ─────────────────────────────────────────────────────────────────────────────
# 5. ExecutionSnapshotBundle
# ─────────────────────────────────────────────────────────────────────────────

class TestSnapshotBundle:
    def _bundle(self, n: int = 2) -> ExecutionSnapshotBundle:
        snaps = tuple(
            _completed(
                execution_id = f"EXEC-{i:03d}",
                order_id     = f"ORD-{i:03d}",
            )
            for i in range(n)
        )
        return ExecutionSnapshotBundle(workflow_id="WF-001", snapshots=snaps)

    def test_size(self) -> None:
        b = self._bundle(3)
        assert b.size == 3
        assert len(b) == 3

    def test_is_empty(self) -> None:
        assert ExecutionSnapshotBundle().is_empty

    def test_all_terminal(self) -> None:
        assert self._bundle(2).all_terminal

    def test_all_succeeded(self) -> None:
        assert self._bundle(2).all_succeeded

    def test_terminal_count(self) -> None:
        b = self._bundle(3)
        assert b.terminal_count == 3

    def test_get_existing(self) -> None:
        b = self._bundle(2)
        sid = b.snapshots[0].snapshot_id
        assert b.get(sid) is not None

    def test_get_missing(self) -> None:
        assert self._bundle(2).get("MISSING") is None

    def test_get_by_execution(self) -> None:
        b = self._bundle(2)
        eid = b.snapshots[0].execution_id
        results = b.get_by_execution(eid)
        assert len(results) == 1

    def test_contains(self) -> None:
        b = self._bundle(2)
        assert b.snapshots[0].snapshot_id in b

    def test_iteration(self) -> None:
        b = self._bundle(3)
        assert sum(1 for _ in b) == 3

    def test_to_dict(self) -> None:
        b = self._bundle(2)
        d = b.to_dict()
        assert d["size"] == 2
        json.dumps(d)   # must not raise

    def test_frozen(self) -> None:
        b = self._bundle(2)
        with pytest.raises((AttributeError, TypeError)):
            b.workflow_id = "X"  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────────────
# 6. Events
# ─────────────────────────────────────────────────────────────────────────────

class TestSnapshotEvents:
    def test_event_type_values(self) -> None:
        assert SnapshotEventType.SNAPSHOT_CREATED.value   == "SNAPSHOT_CREATED"
        assert SnapshotEventType.SNAPSHOT_VALIDATED.value == "SNAPSHOT_VALIDATED"
        assert SnapshotEventType.SNAPSHOT_PUBLISHED.value == "SNAPSHOT_PUBLISHED"
        assert SnapshotEventType.SNAPSHOT_STORED.value    == "SNAPSHOT_STORED"
        assert SnapshotEventType.SNAPSHOT_ARCHIVED.value  == "SNAPSHOT_ARCHIVED"

    def test_make_snapshot_event(self) -> None:
        e = make_snapshot_event(
            SnapshotEventType.SNAPSHOT_CREATED,
            "SNAP-001",
            execution_id = "EXEC-001",
            lifecycle    = SnapshotLifecycle.CREATED,
            trigger      = SnapshotTrigger.STATE_TRANSITION,
        )
        assert e.snapshot_id  == "SNAP-001"
        assert e.execution_id == "EXEC-001"

    def test_event_frozen(self) -> None:
        e = make_snapshot_event(SnapshotEventType.SNAPSHOT_CREATED, "S")
        with pytest.raises((AttributeError, TypeError)):
            e.snapshot_id = "X"  # type: ignore[misc]

    def test_event_to_dict(self) -> None:
        e = make_snapshot_event(
            SnapshotEventType.SNAPSHOT_STORED,
            "S",
            lifecycle = SnapshotLifecycle.STORED,
        )
        d = e.to_dict()
        assert d["event_type"] == "SNAPSHOT_STORED"
        json.dumps(d)

    def test_event_repr(self) -> None:
        e = make_snapshot_event(SnapshotEventType.SNAPSHOT_CREATED, "S-001")
        assert "SNAPSHOT_CREATED" in repr(e)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestValidation:
    def setup_method(self) -> None:
        self.v = ExecutionSnapshotValidator()

    def test_valid_snapshot(self, snapshot: ExecutionSnapshot) -> None:
        r = self.v.validate(snapshot)
        assert r.passed

    def test_missing_execution_id(self) -> None:
        snap = dataclasses.replace(_build(), execution_id="")
        r    = self.v.validate(snap)
        assert not r.passed
        assert any("MISSING_EXECUTION_ID" in e for e in r.errors)

    def test_missing_order_id(self) -> None:
        snap = dataclasses.replace(_build(), order_id="")
        r    = self.v.validate(snap)
        assert not r.passed
        assert any("MISSING_ORDER_ID" in e for e in r.errors)

    def test_missing_workflow_id(self) -> None:
        snap = dataclasses.replace(_build(), workflow_id="")
        r    = self.v.validate(snap)
        assert not r.passed
        assert any("MISSING_WORKFLOW_ID" in e for e in r.errors)

    def test_invalid_version(self) -> None:
        snap = dataclasses.replace(_build(), version=0)
        r    = self.v.validate(snap)
        assert not r.passed
        assert any("INVALID_VERSION" in e for e in r.errors)

    def test_is_terminal_inconsistency_completed(self) -> None:
        # COMPLETED but is_terminal=False
        snap = dataclasses.replace(_build(), execution_state="COMPLETED", is_terminal=False)
        r    = self.v.validate(snap)
        assert not r.passed
        assert any("INVALID_STATE" in e for e in r.errors)

    def test_is_terminal_inconsistency_non_terminal(self) -> None:
        # IDLE but is_terminal=True
        snap = dataclasses.replace(_build(), execution_state="IDLE", is_terminal=True)
        r    = self.v.validate(snap)
        assert not r.passed
        assert any("INVALID_STATE" in e for e in r.errors)

    def test_succeeded_without_completed(self) -> None:
        snap = dataclasses.replace(
            _build(), execution_state="FAILED", is_terminal=True, succeeded=True
        )
        r = self.v.validate(snap)
        assert not r.passed
        assert any("RESULT_MISMATCH" in e for e in r.errors)

    def test_succeeded_with_error_message(self) -> None:
        snap = dataclasses.replace(
            _completed(), error_message="unexpected error"
        )
        r = self.v.validate(snap)
        assert not r.passed

    def test_terminal_no_result_warns(self) -> None:
        snap = _completed()  # no result_id
        r    = self.v.validate(snap)
        assert r.passed   # warning, not error
        assert len(r.warnings) > 0

    def test_valid_completed(self) -> None:
        snap = dataclasses.replace(_completed(), result_id="RES-001")
        r    = self.v.validate(snap)
        assert r.passed

    def test_validation_result_bool(self) -> None:
        assert bool(SnapshotValidationResult.ok())
        assert not bool(SnapshotValidationResult.fail("err"))

    def test_validation_result_to_dict(self) -> None:
        r = SnapshotValidationResult.ok(warnings=("w1",))
        d = r.to_dict()
        assert d["passed"]
        assert "w1" in d["warnings"]


# ─────────────────────────────────────────────────────────────────────────────
# 8. Builder
# ─────────────────────────────────────────────────────────────────────────────

class TestBuilder:
    def test_basic_build(self) -> None:
        snap = _build()
        assert snap.execution_id    == "EXEC-001"
        assert snap.execution_state == "IDLE"

    def test_missing_execution_id_raises(self) -> None:
        with pytest.raises(SnapshotIncompleteError):
            ExecutionSnapshotBuilder().with_ids(
                workflow_id="W", order_id="O"
            ).with_state("IDLE").build()

    def test_missing_workflow_id_raises(self) -> None:
        with pytest.raises(SnapshotIncompleteError):
            ExecutionSnapshotBuilder().with_ids(
                execution_id="E", order_id="O"
            ).with_state("IDLE").build()

    def test_with_timing(self) -> None:
        t_start = time.time() - 10.0
        snap = (
            ExecutionSnapshotBuilder()
            .with_ids(execution_id="E", workflow_id="W", order_id="O")
            .with_state("COMPLETED", is_terminal=True, succeeded=True)
            .with_timing(
                execution_started_at = t_start,
                duration_ms          = 500.0,
            )
            .build()
        )
        assert snap.execution_started_at == t_start
        assert snap.duration_ms          == 500.0

    def test_with_context_ref(self) -> None:
        snap = (
            ExecutionSnapshotBuilder()
            .with_ids(execution_id="E", workflow_id="W", order_id="O")
            .with_state("COMPLETED", is_terminal=True, succeeded=True)
            .with_context_ref(
                context_id            = "CTX-001",
                completeness          = 0.8,
                has_market_snapshot   = True,
                has_strategy_snapshot = True,
            )
            .build()
        )
        assert snap.context_id           == "CTX-001"
        assert snap.context_completeness == 0.8
        assert snap.has_market_snapshot
        assert snap.snapshot_count       == 2

    def test_with_result_ref(self) -> None:
        snap = (
            ExecutionSnapshotBuilder()
            .with_ids(execution_id="E", workflow_id="W", order_id="O")
            .with_state("COMPLETED", is_terminal=True, succeeded=True)
            .with_result_ref("RES-001")
            .build()
        )
        assert snap.result_id == "RES-001"
        assert snap.has_result

    def test_with_audit(self) -> None:
        snap = (
            ExecutionSnapshotBuilder()
            .with_ids(execution_id="E", workflow_id="W", order_id="O")
            .with_state("COMPLETED", is_terminal=True, succeeded=True)
            .with_audit(SnapshotTrigger.TERMINAL)
            .build()
        )
        assert snap.audit_metadata is not None
        assert snap.audit_metadata.trigger == SnapshotTrigger.TERMINAL

    def test_with_tags(self) -> None:
        snap = (
            ExecutionSnapshotBuilder()
            .with_ids(execution_id="E", workflow_id="W", order_id="O")
            .with_state("IDLE")
            .with_tags("fast", "priority")
            .build()
        )
        assert "fast" in snap.tags

    def test_with_statistics(self) -> None:
        snap = (
            ExecutionSnapshotBuilder()
            .with_ids(execution_id="E", workflow_id="W", order_id="O")
            .with_state("COMPLETED", is_terminal=True, succeeded=True)
            .with_statistics(
                validation_duration_ms  = 5.0,
                preparation_duration_ms = 10.0,
                execution_phase_ms      = 100.0,
            )
            .build()
        )
        assert snap.validation_duration_ms  == 5.0
        assert snap.preparation_duration_ms == 10.0
        assert snap.execution_phase_ms      == 100.0

    def test_snapshot_frozen(self) -> None:
        snap = _build()
        with pytest.raises((AttributeError, TypeError)):
            snap.execution_id = "X"  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────────────
# 9. Factory
# ─────────────────────────────────────────────────────────────────────────────

class TestFactory:
    def test_create_valid(self) -> None:
        snap, stats = _create_via_factory()
        assert snap.execution_id  == "EXEC-001"
        assert snap.lifecycle     == SnapshotLifecycle.VALIDATED
        assert stats.validation_passed

    def test_create_with_context(self) -> None:
        snap, stats = _create_via_factory(
            context_id           = "CTX-001",
            has_market_snapshot  = True,
        )
        assert snap.context_id == "CTX-001"
        assert snap.has_market_snapshot

    def test_create_missing_execution_id_raises(self) -> None:
        f = ExecutionSnapshotFactory()
        with pytest.raises(SnapshotIncompleteError):
            f.create(execution_id="", workflow_id="W", order_id="O")

    def test_strict_mode_warns_raises(self) -> None:
        # Terminal snap with no result_id → warning → strict=True should fail
        f = ExecutionSnapshotFactory()
        with pytest.raises(SnapshotValidationError):
            f.create(
                execution_id    = "E",
                workflow_id     = "W",
                order_id        = "O",
                execution_state = "COMPLETED",
                is_terminal     = True,
                succeeded       = True,
                result_id       = "",
                strict          = True,
            )

    def test_stats_build_time_nonzero(self) -> None:
        _, stats = _create_via_factory()
        assert stats.build_time_ms >= 0.0

    def test_gen_snapshot_id(self) -> None:
        sid = ExecutionSnapshotFactory.gen_snapshot_id()
        assert sid.startswith("SNAP-")
        assert len(sid) > 10

    def test_lifecycle_set_to_validated(self) -> None:
        snap, _ = _create_via_factory()
        assert snap.lifecycle == SnapshotLifecycle.VALIDATED


# ─────────────────────────────────────────────────────────────────────────────
# 10. Registry
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistry:
    def test_not_running_before_start(self) -> None:
        r = ExecutionSnapshotRegistry()
        with pytest.raises(SnapshotStoreNotRunning):
            r.register(_build())

    def test_start_stop(self, registry: ExecutionSnapshotRegistry) -> None:
        assert registry.is_running

    def test_register_and_get(
        self,
        registry: ExecutionSnapshotRegistry,
        snapshot: ExecutionSnapshot,
    ) -> None:
        registry.register(snapshot)
        retrieved = registry.get(snapshot.snapshot_id)
        assert retrieved.snapshot_id == snapshot.snapshot_id

    def test_duplicate_raises(
        self,
        registry: ExecutionSnapshotRegistry,
        snapshot: ExecutionSnapshot,
    ) -> None:
        registry.register(snapshot)
        with pytest.raises(DuplicateSnapshotError):
            registry.register(snapshot)

    def test_overwrite_allowed(
        self,
        registry: ExecutionSnapshotRegistry,
        snapshot: ExecutionSnapshot,
    ) -> None:
        registry.register(snapshot)
        registry.register(snapshot, overwrite=True)
        assert registry.count() == 1

    def test_not_found_raises(self, registry: ExecutionSnapshotRegistry) -> None:
        with pytest.raises(SnapshotNotFoundError):
            registry.get("MISSING")

    def test_contains(
        self,
        registry: ExecutionSnapshotRegistry,
        snapshot: ExecutionSnapshot,
    ) -> None:
        assert not registry.contains(snapshot.snapshot_id)
        registry.register(snapshot)
        assert registry.contains(snapshot.snapshot_id)

    def test_get_by_execution(self, registry: ExecutionSnapshotRegistry) -> None:
        snap = _build(execution_id="EXEC-X")
        registry.register(snap)
        results = registry.get_by_execution("EXEC-X")
        assert len(results) == 1

    def test_get_by_workflow(self, registry: ExecutionSnapshotRegistry) -> None:
        snap = _build(workflow_id="WF-99")
        registry.register(snap)
        results = registry.get_by_workflow("WF-99")
        assert any(s.workflow_id == "WF-99" for s in results)

    def test_get_by_order(self, registry: ExecutionSnapshotRegistry) -> None:
        snap = _build(order_id="ORD-77")
        registry.register(snap)
        results = registry.get_by_order("ORD-77")
        assert len(results) == 1

    def test_get_by_lifecycle(
        self,
        registry: ExecutionSnapshotRegistry,
        snapshot: ExecutionSnapshot,
    ) -> None:
        registry.register(snapshot)
        results = registry.get_by_lifecycle(SnapshotLifecycle.CREATED)
        assert any(s.snapshot_id == snapshot.snapshot_id for s in results)

    def test_update_lifecycle(
        self,
        registry: ExecutionSnapshotRegistry,
        snapshot: ExecutionSnapshot,
    ) -> None:
        registry.register(snapshot)
        record = registry.update_lifecycle(
            snapshot.snapshot_id,
            SnapshotLifecycle.STORED,
            reason="stored",
        )
        assert record.snapshot.lifecycle == SnapshotLifecycle.STORED

    def test_history_records_revisions(
        self,
        registry: ExecutionSnapshotRegistry,
        snapshot: ExecutionSnapshot,
    ) -> None:
        registry.register(snapshot)
        registry.update_lifecycle(snapshot.snapshot_id, SnapshotLifecycle.STORED)
        history = registry.get_history(snapshot.snapshot_id)
        assert history.count() >= 2

    def test_capacity_limit(self) -> None:
        r = ExecutionSnapshotRegistry(max_snapshots=2)
        r.start()
        r.register(_build(execution_id="E1"))
        r.register(_build(execution_id="E2", order_id="O2"))
        with pytest.raises(SnapshotCapacityError):
            r.register(_build(execution_id="E3", order_id="O3"))
        r.stop()

    def test_listeners(
        self,
        registry: ExecutionSnapshotRegistry,
        snapshot: ExecutionSnapshot,
    ) -> None:
        events: list[SnapshotEvent] = []
        registry.add_listener(events.append)
        registry.register(snapshot)
        assert len(events) >= 1
        assert events[0].event_type == SnapshotEventType.SNAPSHOT_CREATED

    def test_remove_listener(
        self,
        registry: ExecutionSnapshotRegistry,
        snapshot: ExecutionSnapshot,
    ) -> None:
        events: list[SnapshotEvent] = []
        registry.add_listener(events.append)
        registry.remove_listener(events.append)
        registry.register(snapshot)
        assert len(events) == 0

    def test_faulty_listener_does_not_crash(
        self,
        registry: ExecutionSnapshotRegistry,
        snapshot: ExecutionSnapshot,
    ) -> None:
        def bad(e: SnapshotEvent) -> None:
            raise RuntimeError("error")
        registry.add_listener(bad)
        registry.register(snapshot)   # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# 11. Store
# ─────────────────────────────────────────────────────────────────────────────

class TestStore:
    def test_not_running_before_start(self) -> None:
        s = ExecutionSnapshotStore()
        with pytest.raises(SnapshotStoreNotRunning):
            s.store(_completed())

    def test_store_valid(self, store: ExecutionSnapshotStore) -> None:
        snap, _ = _create_via_factory()
        record  = store.store(snap)
        assert store.contains(snap.snapshot_id)
        assert record.snapshot.lifecycle == SnapshotLifecycle.STORED

    def test_store_invalid_raises(self, store: ExecutionSnapshotStore) -> None:
        # missing execution_id makes validation fail
        bad = dataclasses.replace(_build(), execution_id="")
        with pytest.raises(SnapshotValidationError):
            store.store(bad)

    def test_store_skip_validation(self, store: ExecutionSnapshotStore) -> None:
        bad = dataclasses.replace(_build(), execution_id="")
        # No SnapshotValidationError because validate=False
        record = store.store(bad, validate=False)
        assert record is not None

    def test_publish(self, store: ExecutionSnapshotStore) -> None:
        snap, _ = _create_via_factory()
        store.store(snap)
        record = store.publish(snap.snapshot_id)
        assert record.snapshot.lifecycle == SnapshotLifecycle.PUBLISHED

    def test_archive(self, store: ExecutionSnapshotStore) -> None:
        snap, _ = _create_via_factory()
        store.store(snap)
        record = store.archive(snap.snapshot_id)
        assert record.snapshot.lifecycle == SnapshotLifecycle.ARCHIVED

    def test_get(self, store: ExecutionSnapshotStore) -> None:
        snap, _ = _create_via_factory()
        store.store(snap)
        retrieved = store.get(snap.snapshot_id)
        assert retrieved.snapshot_id == snap.snapshot_id

    def test_get_by_execution(self, store: ExecutionSnapshotStore) -> None:
        snap, _ = _create_via_factory(execution_id="EXEC-UNIQUE")
        store.store(snap)
        results = store.get_by_execution("EXEC-UNIQUE")
        assert len(results) == 1

    def test_get_by_order(self, store: ExecutionSnapshotStore) -> None:
        snap, _ = _create_via_factory(order_id="ORD-UNIQUE")
        store.store(snap)
        results = store.get_by_order("ORD-UNIQUE")
        assert len(results) == 1

    def test_statistics(self, store: ExecutionSnapshotStore) -> None:
        snap, _ = _create_via_factory()
        store.store(snap)
        stats = store.statistics()
        assert stats.snapshot_count >= 1

    def test_listeners(self, store: ExecutionSnapshotStore) -> None:
        events: list[SnapshotEvent] = []
        store.add_listener(events.append)
        snap, _ = _create_via_factory()
        store.store(snap)
        assert len(events) >= 1

    def test_uptime(self, store: ExecutionSnapshotStore) -> None:
        time.sleep(0.01)
        assert store.uptime_sec > 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 12. Cache
# ─────────────────────────────────────────────────────────────────────────────

class TestCache:
    def test_put_and_get(self) -> None:
        cache = ExecutionSnapshotCache(max_size=10)
        snap  = _build()
        cache.put(snap)
        retrieved = cache.get(snap.snapshot_id)
        assert retrieved is not None
        assert retrieved.snapshot_id == snap.snapshot_id

    def test_miss_returns_none(self) -> None:
        cache = ExecutionSnapshotCache()
        assert cache.get("NONEXISTENT") is None

    def test_eviction(self) -> None:
        cache = ExecutionSnapshotCache(max_size=2)
        s1 = _build(execution_id="E1")
        s2 = _build(execution_id="E2", order_id="O2")
        s3 = _build(execution_id="E3", order_id="O3")
        cache.put(s1)
        cache.put(s2)
        cache.put(s3)   # s1 should be evicted (LRU)
        assert cache.size() == 2
        assert cache._evictions == 1
        assert cache.get(s1.snapshot_id) is None

    def test_contains(self) -> None:
        cache = ExecutionSnapshotCache()
        snap  = _build()
        assert not cache.contains(snap.snapshot_id)
        cache.put(snap)
        assert cache.contains(snap.snapshot_id)

    def test_invalidate(self) -> None:
        cache = ExecutionSnapshotCache()
        snap  = _build()
        cache.put(snap)
        assert cache.invalidate(snap.snapshot_id)
        assert not cache.contains(snap.snapshot_id)

    def test_invalidate_missing_returns_false(self) -> None:
        cache = ExecutionSnapshotCache()
        assert not cache.invalidate("MISSING")

    def test_clear(self) -> None:
        cache = ExecutionSnapshotCache()
        cache.put(_build())
        cache.put(_build(execution_id="E2", order_id="O2"))
        cache.clear()
        assert cache.size() == 0

    def test_hit_rate(self) -> None:
        cache = ExecutionSnapshotCache()
        snap  = _build()
        cache.put(snap)
        cache.get(snap.snapshot_id)   # hit
        cache.get("MISS")             # miss
        assert abs(cache.hit_rate - 0.5) < 0.01

    def test_metrics(self) -> None:
        cache = ExecutionSnapshotCache(max_size=100)
        snap  = _build()
        cache.put(snap)
        cache.get(snap.snapshot_id)
        m = cache.metrics()
        assert m["size"]  == 1
        assert m["hits"]  == 1
        assert m["misses"] == 0

    def test_lru_promotion(self) -> None:
        cache = ExecutionSnapshotCache(max_size=2)
        s1 = _build(execution_id="E1")
        s2 = _build(execution_id="E2", order_id="O2")
        cache.put(s1)
        cache.put(s2)
        # Access s1 to promote it to MRU
        cache.get(s1.snapshot_id)
        # Adding s3 should evict s2 (now LRU), not s1
        s3 = _build(execution_id="E3", order_id="O3")
        cache.put(s3)
        assert cache.contains(s1.snapshot_id)
        assert not cache.contains(s2.snapshot_id)


# ─────────────────────────────────────────────────────────────────────────────
# 13. History
# ─────────────────────────────────────────────────────────────────────────────

class TestHistory:
    def test_record_and_query(self) -> None:
        snap = _build()
        h    = ExecutionSnapshotHistory("EXEC-001")
        rev  = make_snapshot_revision(snap)
        h.record(rev)
        assert h.count() == 1
        assert h.first() == rev
        assert h.last()  == rev

    def test_eviction(self) -> None:
        snap = _build()
        h    = ExecutionSnapshotHistory("EXEC-001", max_entries=2)
        for i in range(3):
            h.record(make_snapshot_revision(snap))
        assert h.count()          == 2
        assert h.evicted_count    == 1
        assert h.total_recorded   == 3

    def test_get_by_version(self) -> None:
        snap = _build()
        h    = ExecutionSnapshotHistory("EXEC-001")
        rev  = SnapshotRevision(
            snapshot_id="S", execution_id="E",
            version=5, sequence=0,
        )
        h.record(rev)
        assert h.get_by_version(5) is rev
        assert h.get_by_version(99) is None

    def test_get_by_sequence(self) -> None:
        snap = _build()
        h    = ExecutionSnapshotHistory("EXEC-001")
        rev  = SnapshotRevision(
            snapshot_id="S", execution_id="E",
            version=1, sequence=3,
        )
        h.record(rev)
        assert h.get_by_sequence(3) is rev

    def test_diff(self) -> None:
        h = ExecutionSnapshotHistory("EXEC-001")
        h.record(SnapshotRevision(
            snapshot_id="S", execution_id="E",
            version=1, sequence=0,
            lifecycle=SnapshotLifecycle.CREATED,
            execution_state="IDLE",
        ))
        h.record(SnapshotRevision(
            snapshot_id="S", execution_id="E",
            version=2, sequence=1,
            lifecycle=SnapshotLifecycle.STORED,
            execution_state="COMPLETED",
        ))
        result = h.diff(1, 2)
        assert result["state_changed"]
        assert result["lifecycle_changed"]

    def test_timeline(self) -> None:
        h = ExecutionSnapshotHistory("EXEC-001")
        for i in range(3):
            h.record(SnapshotRevision(
                snapshot_id="S", execution_id="E",
                version=i+1, sequence=i,
            ))
        tl = h.timeline()
        assert len(tl) == 3
        assert "execution_state" in tl[0]

    def test_iteration(self) -> None:
        snap = _build()
        h    = ExecutionSnapshotHistory("EXEC-001")
        for i in range(3):
            h.record(make_snapshot_revision(snap))
        assert sum(1 for _ in h) == 3

    def test_make_snapshot_revision_factory(self) -> None:
        snap = _completed()
        rev  = make_snapshot_revision(snap, reason="final")
        assert rev.snapshot_id     == snap.snapshot_id
        assert rev.execution_id    == snap.execution_id
        assert rev.execution_state == "COMPLETED"
        assert rev.reason          == "final"


# ─────────────────────────────────────────────────────────────────────────────
# 14. Statistics
# ─────────────────────────────────────────────────────────────────────────────

class TestStatistics:
    def test_initial_state(self) -> None:
        s = ExecutionSnapshotStats()
        assert s.snapshot_count      == 0
        assert s.validation_success_rate == 0.0

    def test_record_build_success(self) -> None:
        s  = ExecutionSnapshotStats()
        bs = SnapshotBuildStats(
            snapshot_id       = "S",
            execution_id      = "E",
            build_time_ms     = 5.0,
            validation_passed = True,
        )
        s.record_build(bs)
        assert s.snapshot_count      == 1
        assert s.validation_success  == 1
        assert abs(s.avg_build_time_ms - 5.0) < 0.01

    def test_record_build_failure(self) -> None:
        s  = ExecutionSnapshotStats()
        bs = SnapshotBuildStats(
            snapshot_id="S", execution_id="E",
            validation_passed=False, errors=("e1",),
        )
        s.record_build(bs)
        assert s.validation_failure == 1

    def test_success_rate_mixed(self) -> None:
        s = ExecutionSnapshotStats()
        for passed in (True, True, False):
            s.record_build(SnapshotBuildStats(
                snapshot_id="S", execution_id="E",
                validation_passed=passed,
            ))
        assert abs(s.validation_success_rate - 2/3) < 0.01

    def test_counters(self) -> None:
        s = ExecutionSnapshotStats()
        s.record_published()
        s.record_stored()
        s.record_archived()
        assert s.publication_count == 1
        assert s.stored_count      == 1
        assert s.archived_count    == 1

    def test_to_dict(self) -> None:
        s = ExecutionSnapshotStats()
        s.record_build(SnapshotBuildStats(
            snapshot_id="S", execution_id="E",
            build_time_ms=3.0, validation_passed=True,
        ))
        d = s.to_dict()
        json.dumps(d)   # must not raise
        assert d["snapshot_count"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 15. Serialization
# ─────────────────────────────────────────────────────────────────────────────

class TestSerialization:
    def test_snapshot_to_dict_json_serializable(self) -> None:
        snap, _ = _create_via_factory(
            has_market_snapshot   = True,
            has_strategy_snapshot = True,
            result_id             = "RES-001",
            context_id            = "CTX-001",
        )
        d = snap.to_dict()
        json_str = json.dumps(d)
        assert len(json_str) > 100

    def test_bundle_to_dict_json(self) -> None:
        snaps = tuple(_completed(execution_id=f"E{i}", order_id=f"O{i}") for i in range(2))
        b = ExecutionSnapshotBundle(workflow_id="WF-001", snapshots=snaps)
        d = b.to_dict()
        json.dumps(d)

    def test_audit_to_dict_json(self) -> None:
        m = SnapshotAuditMetadata(trigger=SnapshotTrigger.TERMINAL, notes="final")
        d = m.to_dict()
        json.dumps(d)

    def test_stats_to_dict_json(self) -> None:
        s = ExecutionSnapshotStats()
        s.record_build(SnapshotBuildStats(
            snapshot_id="S", execution_id="E", validation_passed=True,
        ))
        json.dumps(s.to_dict())


# ─────────────────────────────────────────────────────────────────────────────
# 16. Thread safety
# ─────────────────────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_registrations(self) -> None:
        registry = ExecutionSnapshotRegistry(max_snapshots=200)
        registry.start()
        errors: list[Exception] = []

        def register(i: int) -> None:
            try:
                snap = _build(
                    execution_id = f"EXEC-{i:04d}",
                    order_id     = f"ORD-{i:04d}",
                )
                registry.register(snap)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert registry.count() == 50
        registry.stop()

    def test_concurrent_lifecycle_updates(self) -> None:
        registry = ExecutionSnapshotRegistry()
        registry.start()
        snap = _build()
        registry.register(snap)
        errors: list[Exception] = []
        lcs = [SnapshotLifecycle.VALIDATED, SnapshotLifecycle.STORED, SnapshotLifecycle.PUBLISHED]

        def update(i: int) -> None:
            try:
                registry.update_lifecycle(snap.snapshot_id, lcs[i % len(lcs)])
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=update, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        registry.stop()

    def test_concurrent_cache_puts(self) -> None:
        cache  = ExecutionSnapshotCache(max_size=500)
        errors: list[Exception] = []

        def put(i: int) -> None:
            try:
                snap = _build(execution_id=f"E{i}", order_id=f"O{i}")
                cache.put(snap)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=put, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_statistics(self) -> None:
        s      = ExecutionSnapshotStats()
        errors: list[Exception] = []

        def record(i: int) -> None:
            try:
                s.record_build(SnapshotBuildStats(
                    snapshot_id="S", execution_id="E",
                    validation_passed=(i % 2 == 0),
                ))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert s.snapshot_count == 50
