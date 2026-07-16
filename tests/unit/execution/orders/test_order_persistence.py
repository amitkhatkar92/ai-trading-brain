"""tests/unit/execution/orders/test_order_persistence.py
==============================================================
Test suite for C6 Phase 2 M5 — Order Persistence.

Coverage targets:
  - All constants and enums
  - All 11 exception types
  - StorageMetadata, StorageRecord (frozen helpers), StorageStatistics, HealthStatus
  - StorageVersion, VersionHistory
  - StorageSnapshot
  - RepositoryContext
  - RepositoryRequest
  - RepositoryResponse
  - PersistenceEvent + 7 factory functions
  - RecoveryRecord (frozen helpers, state transitions)
  - RecoveryIndex (CRUD, thread-safety)
  - StorageContract (ABC enforcement)
  - RepositoryInterface (Protocol check)
  - RepositoryValidator (all validation paths)
  - RepositoryFactory (all builders)
  - InMemoryOrderRepository (full CRUD + domain searches)
  - RepositoryRegistry (lifecycle, capacity)
  - RepositoryManager (full pipeline, event emission)
  - Concurrency (100 threads, shared InMemoryOrderRepository)
"""
from __future__ import annotations

import dataclasses
import threading
import time
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

from iios.execution.oms.persistence import (
    DEFAULT_MAX_REPOSITORIES,
    DEFAULT_SAVE_TTL_SEC,
    DEFAULT_SEARCH_LIMIT,
    PERSISTENCE_SYSTEM_ID,
    REQUIRED_METHODS,
    SCHEMA_VERSION,
    TERMINAL_RECORD_STATUSES,
    VERSION,
    AbstractOrderRepository,
    DuplicateRecordError,
    HealthStatus,
    InMemoryOrderRepository,
    OperationType,
    PersistenceError,
    PersistenceEventType,
    PersistenceValidationCode,
    PersistenceValidationError,
    PersistenceEvent,
    RecordNotFoundError,
    RecordStatus,
    RecordType,
    RecoveryError,
    RecoveryIndex,
    RecoveryRecord,
    RecoveryState,
    RepositoryCapacityError,
    RepositoryContext,
    RepositoryFactory,
    RepositoryHealth,
    RepositoryInterface,
    RepositoryManager,
    RepositoryNotRunning,
    RepositoryRegistry,
    RepositoryRequest,
    RepositoryResponse,
    RepositoryValidator,
    SchemaVersionError,
    SnapshotCorruptedError,
    StorageContract,
    StorageContractViolationError,
    StorageMetadata,
    StorageRecord,
    StorageSnapshot,
    StorageStatistics,
    StorageVersion,
    VersionConflictError,
    VersionHistory,
    VersionType,
    make_record_archived,
    make_record_restored,
    make_record_saved,
    make_record_updated,
    make_recovery_completed,
    make_recovery_started,
    make_repository_validated,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    return str(uuid.uuid4())


def _repo(repo_id: str = "") -> InMemoryOrderRepository:
    return InMemoryOrderRepository(repo_id or f"test-{_uid()}")


def _payload() -> dict[str, Any]:
    return {"symbol": "NIFTY", "qty": 10, "price": 100.0}


def _save(repo: InMemoryOrderRepository, record_id: str = "", **kwargs) -> RepositoryResponse:
    factory = RepositoryFactory()
    return repo.save(factory.make_save_request(
        record_id or _uid(), _payload(), **kwargs
    ))


def _started_manager() -> tuple[RepositoryManager, InMemoryOrderRepository, RepositoryFactory]:
    repo    = _repo()
    manager = RepositoryManager()
    manager.start()
    manager.register_repository(repo)
    factory = RepositoryFactory()
    return manager, repo, factory


def _ctx(op: OperationType = OperationType.SAVE) -> RepositoryContext:
    return RepositoryContext(operation=op)


# ===========================================================================
# TestConstants
# ===========================================================================

class TestConstants:
    def test_system_id(self):
        assert PERSISTENCE_SYSTEM_ID.startswith("iios:")

    def test_version_format(self):
        parts = VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_schema_version(self):
        assert SCHEMA_VERSION

    def test_defaults(self):
        assert DEFAULT_MAX_REPOSITORIES >= 1
        assert DEFAULT_SAVE_TTL_SEC > 0
        assert DEFAULT_SEARCH_LIMIT >= 1

    def test_terminal_record_statuses(self):
        assert RecordStatus.DELETED in TERMINAL_RECORD_STATUSES
        assert RecordStatus.CORRUPTED in TERMINAL_RECORD_STATUSES

    def test_record_type_members(self):
        names = {m.value for m in RecordType}
        for n in ("ORDER", "LIFECYCLE", "QUEUE", "ROUTING", "EXECUTION", "SNAPSHOT", "AUDIT"):
            assert n in names

    def test_record_status_members(self):
        names = {m.value for m in RecordStatus}
        for n in ("ACTIVE", "ARCHIVED", "DELETED", "RECOVERING", "CORRUPTED"):
            assert n in names

    def test_operation_type_members(self):
        names = {m.value for m in OperationType}
        for n in ("SAVE", "UPDATE", "DELETE", "ARCHIVE", "RESTORE", "FIND", "SEARCH"):
            assert n in names

    def test_repository_health_members(self):
        names = {m.value for m in RepositoryHealth}
        assert "HEALTHY" in names and "DEGRADED" in names

    def test_version_type_members(self):
        names = {m.value for m in VersionType}
        for n in ("RECORD", "SCHEMA", "SNAPSHOT", "MIGRATION", "AUDIT"):
            assert n in names

    def test_recovery_state_members(self):
        names = {m.value for m in RecoveryState}
        for n in ("PENDING", "IN_PROGRESS", "COMPLETED", "FAILED", "PARTIAL"):
            assert n in names

    def test_event_type_members(self):
        names = {m.value for m in PersistenceEventType}
        for n in (
            "RECORD_SAVED", "RECORD_UPDATED", "RECORD_ARCHIVED", "RECORD_RESTORED",
            "RECOVERY_STARTED", "RECOVERY_COMPLETED", "REPOSITORY_VALIDATED",
        ):
            assert n in names

    def test_validation_code_members(self):
        names = {m.value for m in PersistenceValidationCode}
        for n in (
            "MISSING_RECORD_ID", "DUPLICATE_RECORD", "RECORD_NOT_FOUND",
            "VERSION_CONFLICT", "SCHEMA_MISMATCH",
        ):
            assert n in names


# ===========================================================================
# TestExceptions
# ===========================================================================

class TestExceptions:
    def test_hierarchy_root(self):
        e = PersistenceError("base error", code="PE-000")
        assert isinstance(e, Exception)
        assert "PE-000" in str(e.code)

    def test_record_not_found(self):
        e = RecordNotFoundError("rec-1")
        assert e.record_id == "rec-1"
        assert "PE-001" in str(e.code)
        assert isinstance(e, PersistenceError)

    def test_duplicate_record(self):
        e = DuplicateRecordError("rec-2")
        assert e.record_id == "rec-2"
        assert "PE-002" in str(e.code)

    def test_version_conflict(self):
        e = VersionConflictError("rec-3", expected_version=1, actual_version=5)
        assert e.expected_version == 1
        assert e.actual_version   == 5
        assert "PE-003" in str(e.code)

    def test_capacity_error(self):
        e = RepositoryCapacityError("full", code="PE-004")
        assert isinstance(e, PersistenceError)

    def test_not_running(self):
        e = RepositoryNotRunning("not started", code="PE-005")
        assert isinstance(e, PersistenceError)

    def test_validation_error_with_errors(self):
        e = PersistenceValidationError("bad", errors=("e1", "e2"))
        assert e.errors == ("e1", "e2")
        assert "PE-006" in str(e.code)

    def test_recovery_error(self):
        e = RecoveryError("rec-4", "timeout")
        assert e.recovery_id == "rec-4"
        assert e.reason      == "timeout"
        assert "PE-007" in str(e.code)

    def test_contract_violation(self):
        e = StorageContractViolationError("repo-1", violations=("missing save",))
        assert "save" in e.violations[0]
        assert "PE-008" in str(e.code)

    def test_schema_version(self):
        e = SchemaVersionError("rec-5", "1.0.0", "2.0.0")
        assert e.expected_schema == "1.0.0"
        assert "PE-009" in str(e.code)

    def test_snapshot_corrupted(self):
        e = SnapshotCorruptedError("snap-1")
        assert e.snapshot_id == "snap-1"
        assert "PE-010" in str(e.code)

    def test_all_have_pe_code(self):
        codes = [
            PersistenceError("x", code="PE-000").code,
            RecordNotFoundError("x").code,
            DuplicateRecordError("x").code,
            VersionConflictError("x", 1, 2).code,
            RepositoryCapacityError("x", code="PE-004").code,
            RepositoryNotRunning("x", code="PE-005").code,
            PersistenceValidationError("x").code,
            RecoveryError("x").code,
            StorageContractViolationError("x").code,
            SchemaVersionError("x", "1", "2").code,
            SnapshotCorruptedError("x").code,
        ]
        for i, code in enumerate(codes):
            assert code == f"PE-{i:03d}", f"Code mismatch at index {i}: {code}"


# ===========================================================================
# TestStorageMetadata
# ===========================================================================

class TestStorageMetadata:
    def test_defaults(self):
        m = StorageMetadata()
        assert m.record_id  == ""
        assert m.version    == 1
        assert m.schema_version == SCHEMA_VERSION

    def test_frozen(self):
        m = StorageMetadata(record_id="r1")
        with pytest.raises((AttributeError, TypeError)):
            m.record_id = "r2"  # type: ignore

    def test_to_dict(self):
        m = StorageMetadata(record_id="r1", version=3)
        d = m.to_dict()
        assert d["record_id"] == "r1"
        assert d["version"]   == 3

    def test_status_default(self):
        m = StorageMetadata()
        assert m.status == RecordStatus.ACTIVE


# ===========================================================================
# TestStorageRecord
# ===========================================================================

class TestStorageRecord:
    def test_defaults(self):
        r = StorageRecord()
        assert r.version == 1
        assert r.status  == RecordStatus.ACTIVE

    def test_frozen(self):
        r = StorageRecord(record_id="r1")
        with pytest.raises((AttributeError, TypeError)):
            r.record_id = "r2"  # type: ignore

    def test_with_version_increments(self):
        r  = StorageRecord(record_id="r1", version=1, payload={"a": 1})
        r2 = r.with_version({"a": 2})
        assert r2.version    == 2
        assert r2.payload    == {"a": 2}
        assert r.version     == 1   # original unchanged

    def test_with_status(self):
        r  = StorageRecord(record_id="r1")
        r2 = r.with_status(RecordStatus.ARCHIVED, archived_at=time.time())
        assert r2.status      == RecordStatus.ARCHIVED
        assert r2.archived_at > 0
        assert r.status       == RecordStatus.ACTIVE   # original unchanged

    def test_to_metadata(self):
        r = StorageRecord(record_id="r1", version=5, portfolio_id="pf1")
        m = r.to_metadata()
        assert isinstance(m, StorageMetadata)
        assert m.record_id == "r1"
        assert m.version   == 5

    def test_to_dict(self):
        r = StorageRecord(record_id="r1")
        d = r.to_dict()
        assert d["record_id"] == "r1"
        assert "payload"      in d


# ===========================================================================
# TestStorageStatistics
# ===========================================================================

class TestStorageStatistics:
    def test_defaults(self):
        s = StorageStatistics()
        assert s.records_stored   == 0
        assert s.health           == RepositoryHealth.HEALTHY

    def test_frozen(self):
        s = StorageStatistics()
        with pytest.raises((AttributeError, TypeError)):
            s.records_stored = 5  # type: ignore

    def test_to_dict(self):
        s = StorageStatistics(repository_id="r1", records_stored=10)
        d = s.to_dict()
        assert d["records_stored"] == 10


# ===========================================================================
# TestHealthStatus
# ===========================================================================

class TestHealthStatus:
    def test_healthy(self):
        h = HealthStatus(repository_id="r1", health=RepositoryHealth.HEALTHY)
        assert h.is_healthy

    def test_unhealthy(self):
        h = HealthStatus(repository_id="r1", health=RepositoryHealth.DEGRADED)
        assert not h.is_healthy

    def test_to_dict(self):
        h = HealthStatus(repository_id="r1", health=RepositoryHealth.HEALTHY)
        d = h.to_dict()
        assert d["is_healthy"] is True


# ===========================================================================
# TestStorageVersion
# ===========================================================================

class TestStorageVersion:
    def test_defaults(self):
        v = StorageVersion(record_id="r1", version_number=1)
        assert v.version_number == 1
        assert v.schema_version == SCHEMA_VERSION

    def test_frozen(self):
        v = StorageVersion(record_id="r1", version_number=1)
        with pytest.raises((AttributeError, TypeError)):
            v.version_number = 2  # type: ignore

    def test_to_dict(self):
        v = StorageVersion(record_id="r1", version_number=3, author="tester")
        d = v.to_dict()
        assert d["version_number"] == 3
        assert d["author"]         == "tester"


# ===========================================================================
# TestVersionHistory
# ===========================================================================

class TestVersionHistory:
    def test_empty(self):
        h = VersionHistory("r1")
        assert h.count          == 0
        assert h.current_version == 0
        assert h.latest()        is None

    def test_append_and_latest(self):
        h = VersionHistory("r1")
        v = StorageVersion(record_id="r1", version_number=1)
        h.append(v)
        assert h.count           == 1
        assert h.current_version == 1
        assert h.latest()        is v

    def test_at_version(self):
        h = VersionHistory("r1")
        h.append(StorageVersion(record_id="r1", version_number=1))
        h.append(StorageVersion(record_id="r1", version_number=2))
        v = h.at_version(1)
        assert v is not None
        assert v.version_number == 1

    def test_by_type(self):
        h = VersionHistory("r1")
        h.append(StorageVersion(record_id="r1", version_number=1, version_type=VersionType.RECORD))
        h.append(StorageVersion(record_id="r1", version_number=2, version_type=VersionType.SCHEMA))
        assert len(h.by_type(VersionType.RECORD)) == 1
        assert len(h.by_type(VersionType.SCHEMA)) == 1

    def test_all_returns_copy(self):
        h = VersionHistory("r1")
        h.append(StorageVersion(record_id="r1", version_number=1))
        first = h.all()
        h.append(StorageVersion(record_id="r1", version_number=2))
        assert len(first) == 1    # snapshot was not mutated

    def test_iter(self):
        h = VersionHistory("r1")
        for i in range(1, 4):
            h.append(StorageVersion(record_id="r1", version_number=i))
        versions = list(h)
        assert [v.version_number for v in versions] == [1, 2, 3]

    def test_len(self):
        h = VersionHistory("r1")
        h.append(StorageVersion(record_id="r1", version_number=1))
        assert len(h) == 1


# ===========================================================================
# TestStorageSnapshot
# ===========================================================================

class TestStorageSnapshot:
    def _meta(self, status: RecordStatus = RecordStatus.ACTIVE) -> StorageMetadata:
        return StorageMetadata(record_id=_uid(), status=status)

    def test_defaults(self):
        s = StorageSnapshot()
        assert s.total_records == 0
        assert s.records       == ()

    def test_frozen(self):
        s = StorageSnapshot()
        with pytest.raises((AttributeError, TypeError)):
            s.total_records = 5  # type: ignore

    def test_active_records(self):
        m1 = self._meta(RecordStatus.ACTIVE)
        m2 = self._meta(RecordStatus.ARCHIVED)
        s  = StorageSnapshot(records=(m1, m2), total_records=2)
        assert len(s.active_records())   == 1
        assert len(s.archived_records()) == 1

    def test_by_type(self):
        m1 = StorageMetadata(record_id=_uid(), record_type=RecordType.ORDER)
        m2 = StorageMetadata(record_id=_uid(), record_type=RecordType.QUEUE)
        s  = StorageSnapshot(records=(m1, m2))
        assert len(s.by_type(RecordType.ORDER)) == 1

    def test_is_healthy(self):
        s = StorageSnapshot(health=RepositoryHealth.HEALTHY)
        assert s.is_healthy
        s2 = StorageSnapshot(health=RepositoryHealth.DEGRADED)
        assert not s2.is_healthy

    def test_to_dict(self):
        s = StorageSnapshot(repository_id="r1", total_records=5)
        d = s.to_dict()
        assert d["total_records"] == 5


# ===========================================================================
# TestRepositoryContext
# ===========================================================================

class TestRepositoryContext:
    def test_defaults(self):
        ctx = RepositoryContext()
        assert ctx.operation == OperationType.SAVE
        assert ctx.requester == "iios:system"

    def test_frozen(self):
        ctx = RepositoryContext()
        with pytest.raises((AttributeError, TypeError)):
            ctx.operation = OperationType.DELETE  # type: ignore

    def test_is_read_only(self):
        assert RepositoryContext(operation=OperationType.FIND).is_read_only
        assert RepositoryContext(operation=OperationType.SEARCH).is_read_only
        assert not RepositoryContext(operation=OperationType.SAVE).is_read_only

    def test_is_mutating(self):
        assert RepositoryContext(operation=OperationType.SAVE).is_mutating
        assert RepositoryContext(operation=OperationType.UPDATE).is_mutating
        assert not RepositoryContext(operation=OperationType.FIND).is_mutating

    def test_to_dict(self):
        ctx = RepositoryContext(portfolio_id="pf1")
        d   = ctx.to_dict()
        assert d["portfolio_id"] == "pf1"


# ===========================================================================
# TestRepositoryRequest
# ===========================================================================

class TestRepositoryRequest:
    def test_defaults(self):
        r = RepositoryRequest()
        assert r.operation   == OperationType.SAVE
        assert r.limit       == DEFAULT_SEARCH_LIMIT

    def test_mutable(self):
        r = RepositoryRequest()
        r.record_id = "rec-1"
        assert r.record_id == "rec-1"

    def test_to_dict(self):
        r = RepositoryRequest(record_id="r1", operation=OperationType.FIND)
        d = r.to_dict()
        assert d["record_id"]  == "r1"
        assert d["operation"]  == "FIND"


# ===========================================================================
# TestRepositoryResponse
# ===========================================================================

class TestRepositoryResponse:
    def test_success_defaults(self):
        r = RepositoryResponse(succeeded=True, record_id="r1")
        assert r.succeeded
        assert not r.is_error
        assert r.record_count == 0

    def test_error_response(self):
        r = RepositoryResponse(succeeded=False, error_code="PE-001")
        assert r.is_error
        assert r.error_code == "PE-001"

    def test_frozen(self):
        r = RepositoryResponse()
        with pytest.raises((AttributeError, TypeError)):
            r.succeeded = False  # type: ignore

    def test_to_dict(self):
        r = RepositoryResponse(record_id="r1", succeeded=True, elapsed_ms=3.14)
        d = r.to_dict()
        assert d["succeeded"] is True
        assert d["elapsed_ms"] > 0

    def test_record_count_with_records(self):
        rec  = StorageRecord(record_id=_uid())
        resp = RepositoryResponse(records=(rec, rec))
        assert resp.record_count == 2


# ===========================================================================
# TestPersistenceEvents
# ===========================================================================

class TestPersistenceEvents:
    def test_event_frozen(self):
        e = PersistenceEvent()
        with pytest.raises((AttributeError, TypeError)):
            e.succeeded = False  # type: ignore

    def test_make_record_saved(self):
        e = make_record_saved("r1", "repo1", version=2, correlation_id="c1")
        assert e.event_type    == PersistenceEventType.RECORD_SAVED
        assert e.record_id     == "r1"
        assert e.repository_id == "repo1"
        assert e.record_version == 2
        assert e.succeeded     is True

    def test_make_record_updated(self):
        e = make_record_updated("r1", "repo1", version=3)
        assert e.event_type    == PersistenceEventType.RECORD_UPDATED
        assert e.record_version == 3

    def test_make_record_archived(self):
        e = make_record_archived("r1", "repo1")
        assert e.event_type == PersistenceEventType.RECORD_ARCHIVED

    def test_make_record_restored(self):
        e = make_record_restored("r1", "repo1")
        assert e.event_type == PersistenceEventType.RECORD_RESTORED

    def test_make_recovery_started(self):
        e = make_recovery_started("r1", "rec-id-1")
        assert e.event_type  == PersistenceEventType.RECOVERY_STARTED
        assert e.recovery_id == "rec-id-1"

    def test_make_recovery_completed_success(self):
        e = make_recovery_completed("r1", "rec-id-2", succeeded=True)
        assert e.event_type  == PersistenceEventType.RECOVERY_COMPLETED
        assert e.succeeded   is True

    def test_make_recovery_completed_failure(self):
        e = make_recovery_completed("r1", "rec-id-3", succeeded=False)
        assert e.succeeded is False

    def test_make_repository_validated_pass(self):
        e = make_repository_validated("repo1", is_valid=True)
        assert e.event_type == PersistenceEventType.REPOSITORY_VALIDATED
        assert e.succeeded  is True

    def test_make_repository_validated_fail(self):
        e = make_repository_validated("repo1", is_valid=False)
        assert e.succeeded is False

    def test_to_dict(self):
        e = make_record_saved("r1", "repo1", 1)
        d = e.to_dict()
        assert d["event_type"] == "RECORD_SAVED"


# ===========================================================================
# TestRecoveryRecord
# ===========================================================================

class TestRecoveryRecord:
    def test_defaults(self):
        r = RecoveryRecord()
        assert r.recovery_state == RecoveryState.PENDING
        assert r.is_pending
        assert not r.is_complete
        assert not r.is_successful

    def test_frozen(self):
        r = RecoveryRecord()
        with pytest.raises((AttributeError, TypeError)):
            r.recovery_state = RecoveryState.COMPLETED  # type: ignore

    def test_with_state_to_in_progress(self):
        r = RecoveryRecord(recovery_id="r1", order_id="o1")
        r2 = r.with_state(RecoveryState.IN_PROGRESS)
        assert r2.is_in_progress
        assert r2.completed_at == 0.0
        assert r.is_pending    # original unchanged

    def test_with_state_to_completed(self):
        r  = RecoveryRecord()
        r2 = r.with_state(RecoveryState.COMPLETED)
        assert r2.is_complete
        assert r2.is_successful
        assert r2.completed_at > 0

    def test_with_state_to_failed(self):
        r  = RecoveryRecord()
        r2 = r.with_state(RecoveryState.FAILED, failure_reason="timeout")
        assert r2.is_complete
        assert not r2.is_successful
        assert r2.failure_reason == "timeout"

    def test_to_dict(self):
        r = RecoveryRecord(order_id="o1", record_id="rec1")
        d = r.to_dict()
        assert d["order_id"]  == "o1"
        assert d["record_id"] == "rec1"


# ===========================================================================
# TestRecoveryIndex
# ===========================================================================

class TestRecoveryIndex:
    def _record(self, order_id: str = "", record_id: str = "") -> RecoveryRecord:
        return RecoveryRecord(
            order_id  = order_id  or _uid(),
            record_id = record_id or _uid(),
        )

    def test_register_and_get(self):
        idx = RecoveryIndex()
        r   = self._record()
        idx.register(r)
        assert idx.get(r.recovery_id) is r

    def test_register_duplicate_raises(self):
        idx = RecoveryIndex()
        r   = self._record()
        idx.register(r)
        with pytest.raises(ValueError):
            idx.register(r)

    def test_by_order_id(self):
        idx = RecoveryIndex()
        oid = _uid()
        r1  = RecoveryRecord(order_id=oid)
        r2  = RecoveryRecord(order_id=oid)
        idx.register(r1)
        idx.register(r2)
        results = idx.by_order_id(oid)
        assert len(results) == 2

    def test_by_record_id(self):
        idx = RecoveryIndex()
        rid = _uid()
        r   = RecoveryRecord(record_id=rid)
        idx.register(r)
        assert len(idx.by_record_id(rid)) == 1

    def test_replace(self):
        idx = RecoveryIndex()
        r   = self._record()
        idx.register(r)
        r2  = r.with_state(RecoveryState.COMPLETED)
        idx.replace(r2)
        stored = idx.get(r.recovery_id)
        assert stored is not None
        assert stored.recovery_state == RecoveryState.COMPLETED

    def test_replace_not_found_raises(self):
        idx = RecoveryIndex()
        r   = self._record()
        with pytest.raises(KeyError):
            idx.replace(r)

    def test_remove(self):
        idx = RecoveryIndex()
        r   = self._record()
        idx.register(r)
        assert idx.remove(r.recovery_id) is True
        assert idx.get(r.recovery_id)    is None
        assert idx.remove(r.recovery_id) is False

    def test_pending(self):
        idx = RecoveryIndex()
        r1  = RecoveryRecord()
        r2  = RecoveryRecord().with_state(RecoveryState.COMPLETED)
        r3  = RecoveryRecord().with_state(RecoveryState.IN_PROGRESS)
        idx.register(r1)
        idx.register(dataclasses.replace(r2, recovery_id=_uid()))
        idx.register(dataclasses.replace(r3, recovery_id=_uid()))
        assert len(idx.pending()) == 1

    def test_completed(self):
        idx = RecoveryIndex()
        r1  = RecoveryRecord()
        r2  = dataclasses.replace(RecoveryRecord(), recovery_id=_uid())
        r2  = r2.with_state(RecoveryState.FAILED)
        r3  = dataclasses.replace(RecoveryRecord(), recovery_id=_uid())
        r3  = r3.with_state(RecoveryState.COMPLETED)
        idx.register(r1)
        idx.register(r2)
        idx.register(r3)
        assert len(idx.completed()) == 2

    def test_all(self):
        idx = RecoveryIndex()
        for _ in range(5):
            idx.register(self._record())
        assert len(idx.all()) == 5

    def test_count_and_len(self):
        idx = RecoveryIndex()
        for _ in range(3):
            idx.register(self._record())
        assert idx.count == 3
        assert len(idx)  == 3

    def test_iter(self):
        idx = RecoveryIndex()
        for _ in range(4):
            idx.register(self._record())
        all_recovered = list(idx)
        assert len(all_recovered) == 4

    def test_pending_count(self):
        idx = RecoveryIndex()
        for _ in range(3):
            idx.register(self._record())
        assert idx.pending_count == 3

    def test_thread_safety(self):
        idx     = RecoveryIndex()
        errors  = []
        records = []
        lock    = threading.Lock()

        def worker(n):
            try:
                for _ in range(10):
                    r = self._record()
                    idx.register(r)
                    with lock:
                        records.append(r)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert idx.count == 100


# ===========================================================================
# TestStorageContract
# ===========================================================================

class TestStorageContract:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            StorageContract()  # type: ignore

    def test_in_memory_is_concrete(self):
        repo = _repo()
        assert isinstance(repo, StorageContract)

    def test_incomplete_implementation_fails(self):
        class Partial(StorageContract):
            @property
            def repository_id(self): return "partial"
            def save(self, r): ...
            def update(self, r): ...
            def delete(self, r): ...
            def archive(self, r): ...
            def restore(self, r): ...
            def exists(self, i): ...
            def find(self, r): ...
            def search(self, r): ...
            def health(self): ...
            def statistics(self): ...
            # missing snapshot()
        with pytest.raises(TypeError):
            Partial()  # type: ignore


# ===========================================================================
# TestRepositoryInterface
# ===========================================================================

class TestRepositoryInterface:
    def test_required_methods_non_empty(self):
        assert len(REQUIRED_METHODS) >= 10

    def test_in_memory_satisfies_protocol(self):
        repo = _repo()
        assert isinstance(repo, RepositoryInterface)

    def test_incomplete_does_not_satisfy(self):
        class Incomplete:
            @property
            def repository_id(self): return "x"
            def save(self, r): ...
            # many methods missing

        obj = Incomplete()
        assert not isinstance(obj, RepositoryInterface)


# ===========================================================================
# TestRepositoryValidation
# ===========================================================================

class TestRepositoryValidation:
    def setup_method(self):
        self.v = RepositoryValidator()

    def test_valid_save_request(self):
        req = RepositoryRequest(
            operation = OperationType.SAVE,
            record_id = "r1",
            payload   = {"a": 1},
        )
        self.v.validate_request(req)   # must not raise

    def test_save_missing_record_id(self):
        req = RepositoryRequest(operation=OperationType.SAVE, payload={"a": 1})
        with pytest.raises(PersistenceValidationError):
            self.v.validate_request(req)

    def test_update_missing_record_id(self):
        req = RepositoryRequest(operation=OperationType.UPDATE, payload={"a": 1})
        with pytest.raises(PersistenceValidationError):
            self.v.validate_request(req)

    def test_save_empty_payload(self):
        req = RepositoryRequest(operation=OperationType.SAVE, record_id="r1", payload={})
        with pytest.raises(PersistenceValidationError):
            self.v.validate_request(req)

    def test_invalid_limit(self):
        req = RepositoryRequest(
            operation=OperationType.SEARCH, record_id="r1", payload={"a": 1}, limit=0
        )
        with pytest.raises(PersistenceValidationError):
            self.v.validate_request(req)

    def test_invalid_offset(self):
        req = RepositoryRequest(
            operation=OperationType.SEARCH, record_id="r1", payload={"a": 1}, offset=-1
        )
        with pytest.raises(PersistenceValidationError):
            self.v.validate_request(req)

    def test_invalid_time_range(self):
        req = RepositoryRequest(
            operation=OperationType.SEARCH,
            time_range_start=time.time() + 100,
            time_range_end=time.time(),
        )
        with pytest.raises(PersistenceValidationError):
            self.v.validate_request(req)

    def test_validate_no_duplicate_passes(self):
        repo = _repo()
        self.v.validate_no_duplicate("non-existent", repo)  # should not raise

    def test_validate_no_duplicate_raises(self):
        repo = _repo()
        _save(repo, "dup-1")
        with pytest.raises(DuplicateRecordError):
            self.v.validate_no_duplicate("dup-1", repo)

    def test_validate_record_exists_passes(self):
        repo = _repo()
        _save(repo, "ex-1")
        self.v.validate_record_exists("ex-1", repo)  # should not raise

    def test_validate_record_exists_raises(self):
        repo = _repo()
        with pytest.raises(RecordNotFoundError):
            self.v.validate_record_exists("missing", repo)

    def test_validate_version_no_conflict(self):
        self.v.validate_version("r1", expected_version=2, actual_version=2)

    def test_validate_version_conflict(self):
        with pytest.raises(VersionConflictError):
            self.v.validate_version("r1", expected_version=1, actual_version=3)

    def test_validate_version_zero_skips(self):
        # expected_version=0 means "skip check"
        self.v.validate_version("r1", expected_version=0, actual_version=99)

    def test_validate_contract_passes(self):
        repo = _repo()
        violations = self.v.validate_contract(repo)
        assert violations == []

    def test_validate_contract_violations(self):
        obj = MagicMock(spec=[])  # no attributes at all
        violations = self.v.validate_contract(obj)
        assert len(violations) > 0

    def test_assert_contract_raises(self):
        obj = object()
        with pytest.raises(StorageContractViolationError):
            self.v.assert_contract(obj)

    def test_validate_snapshot_valid(self):
        m1 = StorageMetadata(record_id=_uid(), status=RecordStatus.ACTIVE)
        m2 = StorageMetadata(record_id=_uid(), status=RecordStatus.ARCHIVED)
        snap = StorageSnapshot(
            total_records  = 2,
            total_active   = 1,
            total_archived = 1,
            records        = (m1, m2),
        )
        assert self.v.validate_snapshot(snap) is True

    def test_validate_snapshot_invalid(self):
        m1 = StorageMetadata(record_id=_uid(), status=RecordStatus.ACTIVE)
        snap = StorageSnapshot(
            total_records  = 5,   # mismatch
            total_active   = 1,
            total_archived = 0,
            records        = (m1,),
        )
        assert self.v.validate_snapshot(snap) is False

    def test_validate_schema_version_pass(self):
        self.v.validate_schema_version("r1", SCHEMA_VERSION, SCHEMA_VERSION)

    def test_validate_schema_version_fail(self):
        with pytest.raises(SchemaVersionError):
            self.v.validate_schema_version("r1", "99.0.0", SCHEMA_VERSION)


# ===========================================================================
# TestRepositoryFactory
# ===========================================================================

class TestRepositoryFactory:
    def setup_method(self):
        self.f = RepositoryFactory()

    def test_make_save_request(self):
        req = self.f.make_save_request("r1", {"a": 1})
        assert req.operation == OperationType.SAVE
        assert req.record_id == "r1"
        assert req.payload   == {"a": 1}

    def test_make_update_request(self):
        req = self.f.make_update_request("r1", {"a": 2}, expected_version=1)
        assert req.operation        == OperationType.UPDATE
        assert req.expected_version == 1

    def test_make_find_request(self):
        req = self.f.make_find_request("r1")
        assert req.operation == OperationType.FIND
        assert req.record_id == "r1"

    def test_make_search_request(self):
        req = self.f.make_search_request(portfolio_id="pf1", limit=50)
        assert req.operation     == OperationType.SEARCH
        assert req.portfolio_id  == "pf1"
        assert req.limit         == 50

    def test_make_delete_request(self):
        req = self.f.make_delete_request("r1")
        assert req.operation == OperationType.DELETE

    def test_make_archive_request(self):
        req = self.f.make_archive_request("r1")
        assert req.operation == OperationType.ARCHIVE

    def test_make_restore_request(self):
        req = self.f.make_restore_request("r1")
        assert req.operation == OperationType.RESTORE

    def test_make_success_response(self):
        resp = self.f.make_success_response("req1", OperationType.SAVE, "r1")
        assert resp.succeeded
        assert resp.request_id == "req1"

    def test_make_error_response(self):
        resp = self.f.make_error_response(
            "req1", OperationType.FIND, "r1", "PE-001", "not found"
        )
        assert not resp.succeeded
        assert resp.error_code == "PE-001"

    def test_make_storage_record(self):
        rec = self.f.make_storage_record(
            "r1", {"qty": 5}, portfolio_id="pf1", strategy_id="s1"
        )
        assert rec.record_id    == "r1"
        assert rec.portfolio_id == "pf1"
        assert rec.version      == 1
        assert rec.status       == RecordStatus.ACTIVE

    def test_make_recovery_record(self):
        r = self.f.make_recovery_record("o1", "rec1", {"data": 1})
        assert r.order_id       == "o1"
        assert r.record_id      == "rec1"
        assert r.recovery_state == RecoveryState.PENDING

    def test_make_version_entry(self):
        v = self.f.make_version_entry("r1", version_number=3, author="bot")
        assert v.version_number == 3
        assert v.author         == "bot"


# ===========================================================================
# TestOrderRepository
# ===========================================================================

class TestOrderRepository:
    def setup_method(self):
        self.repo    = _repo()
        self.factory = RepositoryFactory()

    # ---- save ----

    def test_save_success(self):
        rid  = _uid()
        resp = self.repo.save(self.factory.make_save_request(rid, _payload()))
        assert resp.succeeded
        assert resp.record_id      == rid
        assert resp.record_version == 1

    def test_save_duplicate_returns_error(self):
        rid = _uid()
        self.repo.save(self.factory.make_save_request(rid, _payload()))
        resp = self.repo.save(self.factory.make_save_request(rid, _payload()))
        assert not resp.succeeded
        assert resp.error_code == "PE-002"

    # ---- update ----

    def test_update_success(self):
        rid = _uid()
        self.repo.save(self.factory.make_save_request(rid, _payload()))
        resp = self.repo.update(self.factory.make_update_request(rid, {"qty": 20}))
        assert resp.succeeded
        assert resp.record_version == 2

    def test_update_not_found(self):
        resp = self.repo.update(self.factory.make_update_request(_uid(), {"a": 1}))
        assert not resp.succeeded
        assert resp.error_code == "PE-001"

    def test_update_version_conflict(self):
        rid = _uid()
        self.repo.save(self.factory.make_save_request(rid, _payload()))
        # update twice to version=2
        self.repo.update(self.factory.make_update_request(rid, {"qty": 20}))
        # now try with expected_version=1 (stale)
        resp = self.repo.update(
            self.factory.make_update_request(rid, {"qty": 30}, expected_version=1)
        )
        assert not resp.succeeded
        assert resp.error_code == "PE-003"

    def test_update_version_zero_skips_check(self):
        rid = _uid()
        self.repo.save(self.factory.make_save_request(rid, _payload()))
        resp = self.repo.update(
            self.factory.make_update_request(rid, {"qty": 99}, expected_version=0)
        )
        assert resp.succeeded

    # ---- delete ----

    def test_delete_active(self):
        rid = _uid()
        self.repo.save(self.factory.make_save_request(rid, _payload()))
        resp = self.repo.delete(self.factory.make_delete_request(rid))
        assert resp.succeeded
        assert not self.repo.exists(rid)

    def test_delete_archived(self):
        rid = _uid()
        self.repo.save(self.factory.make_save_request(rid, _payload()))
        self.repo.archive(self.factory.make_archive_request(rid))
        resp = self.repo.delete(self.factory.make_delete_request(rid))
        assert resp.succeeded

    def test_delete_not_found(self):
        resp = self.repo.delete(self.factory.make_delete_request(_uid()))
        assert not resp.succeeded
        assert resp.error_code == "PE-001"

    # ---- archive ----

    def test_archive_success(self):
        rid = _uid()
        self.repo.save(self.factory.make_save_request(rid, _payload()))
        resp = self.repo.archive(self.factory.make_archive_request(rid))
        assert resp.succeeded
        assert not self.repo.exists(rid)   # not in active pool

    def test_archive_not_found(self):
        resp = self.repo.archive(self.factory.make_archive_request(_uid()))
        assert not resp.succeeded
        assert resp.error_code == "PE-001"

    # ---- restore ----

    def test_restore_success(self):
        rid = _uid()
        self.repo.save(self.factory.make_save_request(rid, _payload()))
        self.repo.archive(self.factory.make_archive_request(rid))
        resp = self.repo.restore(self.factory.make_restore_request(rid))
        assert resp.succeeded
        assert self.repo.exists(rid)       # back in active pool

    def test_restore_not_in_archive(self):
        resp = self.repo.restore(self.factory.make_restore_request(_uid()))
        assert not resp.succeeded
        assert resp.error_code == "PE-001"

    # ---- exists ----

    def test_exists_true_and_false(self):
        rid = _uid()
        assert not self.repo.exists(rid)
        self.repo.save(self.factory.make_save_request(rid, _payload()))
        assert self.repo.exists(rid)

    # ---- find ----

    def test_find_success(self):
        rid = _uid()
        self.repo.save(self.factory.make_save_request(rid, _payload()))
        resp = self.repo.find(self.factory.make_find_request(rid))
        assert resp.succeeded
        assert resp.record is not None
        assert resp.record.record_id == rid

    def test_find_not_found(self):
        resp = self.repo.find(self.factory.make_find_request(_uid()))
        assert not resp.succeeded
        assert resp.error_code == "PE-001"

    def test_find_archived_with_flag(self):
        rid = _uid()
        self.repo.save(self.factory.make_save_request(rid, _payload()))
        self.repo.archive(self.factory.make_archive_request(rid))
        req = self.factory.make_find_request(rid)
        req.include_archived = True
        resp = self.repo.find(req)
        assert resp.succeeded

    # ---- search ----

    def test_search_all(self):
        for _ in range(5):
            _save(self.repo)
        resp = self.repo.search(self.factory.make_search_request())
        assert resp.succeeded
        assert resp.total_matches >= 5

    def test_search_by_portfolio(self):
        pf = _uid()
        for _ in range(3):
            _save(self.repo, portfolio_id=pf)
        _save(self.repo, portfolio_id="other")
        req  = self.factory.make_search_request(portfolio_id=pf)
        resp = self.repo.search(req)
        assert resp.total_matches == 3

    def test_search_by_strategy(self):
        sid = _uid()
        _save(self.repo, strategy_id=sid)
        _save(self.repo, strategy_id=sid)
        _save(self.repo)
        resp = self.repo.search(self.factory.make_search_request(strategy_id=sid))
        assert resp.total_matches == 2

    def test_search_by_workflow(self):
        wid = _uid()
        _save(self.repo, workflow_id=wid)
        _save(self.repo)
        resp = self.repo.search(self.factory.make_search_request(workflow_id=wid))
        assert resp.total_matches == 1

    def test_search_pagination(self):
        for _ in range(10):
            _save(self.repo)
        req = self.factory.make_search_request(limit=3, offset=0)
        r1  = self.repo.search(req)
        req2 = self.factory.make_search_request(limit=3, offset=3)
        r2   = self.repo.search(req2)
        assert r1.record_count == 3
        assert r2.record_count == 3
        ids1 = {r.record_id for r in r1.records}
        ids2 = {r.record_id for r in r2.records}
        assert ids1.isdisjoint(ids2)

    def test_search_by_time_range(self):
        t0 = time.time()
        _save(self.repo)
        t1 = time.time()
        resp = self.repo.search(
            self.factory.make_search_request(time_range_start=t0, time_range_end=t1)
        )
        assert resp.total_matches >= 1

    def test_search_include_archived(self):
        rid = _uid()
        self.repo.save(self.factory.make_save_request(rid, _payload()))
        self.repo.archive(self.factory.make_archive_request(rid))
        req  = self.factory.make_search_request(include_archived=True)
        resp = self.repo.search(req)
        ids  = {r.record_id for r in resp.records}
        assert rid in ids

    # ---- health / statistics / snapshot ----

    def test_health(self):
        h = self.repo.health()
        assert h.is_healthy

    def test_statistics(self):
        for _ in range(3):
            _save(self.repo)
        s = self.repo.statistics()
        assert s.records_stored  == 3
        assert s.total_active    == 3
        assert s.health          == RepositoryHealth.HEALTHY

    def test_statistics_after_archive(self):
        rid = _uid()
        self.repo.save(self.factory.make_save_request(rid, _payload()))
        self.repo.archive(self.factory.make_archive_request(rid))
        s = self.repo.statistics()
        assert s.records_archived == 1
        assert s.total_archived   == 1

    def test_snapshot(self):
        for _ in range(4):
            _save(self.repo)
        snap = self.repo.snapshot()
        assert isinstance(snap, StorageSnapshot)
        assert snap.total_records == 4
        assert snap.total_active  == 4
        assert snap.is_healthy

    # ---- domain searches ----

    def test_find_by_workflow(self):
        wid = _uid()
        for _ in range(2):
            _save(self.repo, workflow_id=wid)
        _save(self.repo)
        result = self.repo.find_by_workflow(wid)
        assert len(result) == 2

    def test_find_by_portfolio(self):
        pid = _uid()
        _save(self.repo, portfolio_id=pid)
        _save(self.repo)
        result = self.repo.find_by_portfolio(pid)
        assert len(result) == 1

    def test_find_by_strategy(self):
        sid = _uid()
        for _ in range(3):
            _save(self.repo, strategy_id=sid)
        result = self.repo.find_by_strategy(sid)
        assert len(result) == 3

    def test_find_by_status_active(self):
        _save(self.repo)
        result = self.repo.find_by_status(RecordStatus.ACTIVE)
        assert len(result) >= 1

    def test_find_by_status_archived(self):
        rid = _uid()
        self.repo.save(self.factory.make_save_request(rid, _payload()))
        self.repo.archive(self.factory.make_archive_request(rid))
        result = self.repo.find_by_status(RecordStatus.ARCHIVED)
        assert any(r.record_id == rid for r in result)

    def test_find_by_time_range(self):
        t0 = time.time()
        _save(self.repo)
        t1 = time.time()
        result = self.repo.find_by_time_range(t0, t1)
        assert len(result) >= 1

    # ---- version history ----

    def test_version_history_created_on_save(self):
        rid = _uid()
        self.repo.save(self.factory.make_save_request(rid, _payload()))
        history = self.repo.version_history(rid)
        assert history is not None
        assert history.count == 1

    def test_version_history_grows_on_update(self):
        rid = _uid()
        self.repo.save(self.factory.make_save_request(rid, _payload()))
        self.repo.update(self.factory.make_update_request(rid, {"qty": 5}))
        history = self.repo.version_history(rid)
        assert history is not None
        assert history.count == 2

    # ---- counts ----

    def test_active_and_archived_count(self):
        rid = _uid()
        _save(self.repo, rid)
        assert self.repo.active_count >= 1
        self.repo.archive(self.factory.make_archive_request(rid))
        assert self.repo.archived_count >= 1


# ===========================================================================
# TestRepositoryRegistry
# ===========================================================================

class TestRepositoryRegistry:
    def test_not_started_raises_on_register(self):
        registry = RepositoryRegistry()
        repo     = _repo()
        with pytest.raises(RepositoryNotRunning):
            registry.register(repo)

    def test_lifecycle_running(self):
        registry = RepositoryRegistry()
        registry.start()
        assert registry.lifecycle_state().value == "running"
        registry.stop()

    def test_register_and_get(self):
        registry = RepositoryRegistry()
        registry.start()
        repo = _repo("my-repo")
        registry.register(repo)
        assert registry.get("my-repo") is repo
        registry.stop()

    def test_unregister(self):
        registry = RepositoryRegistry()
        registry.start()
        repo = _repo("to-remove")
        registry.register(repo)
        assert registry.unregister("to-remove") is True
        assert registry.get("to-remove")         is None
        assert registry.unregister("to-remove")  is False
        registry.stop()

    def test_capacity_limit(self):
        registry = RepositoryRegistry(max_repositories=2)
        registry.start()
        registry.register(_repo())
        registry.register(_repo())
        with pytest.raises(RepositoryCapacityError):
            registry.register(_repo())
        registry.stop()

    def test_default_returns_first(self):
        registry = RepositoryRegistry()
        registry.start()
        r1 = _repo("first")
        r2 = _repo("second")
        registry.register(r1)
        registry.register(r2)
        assert registry.default() is r1
        registry.stop()

    def test_repository_ids(self):
        registry = RepositoryRegistry()
        registry.start()
        r1 = _repo("r-a")
        r2 = _repo("r-b")
        registry.register(r1)
        registry.register(r2)
        ids = registry.repository_ids()
        assert "r-a" in ids and "r-b" in ids
        registry.stop()

    def test_count_and_iter_and_len(self):
        registry = RepositoryRegistry()
        registry.start()
        for _ in range(3):
            registry.register(_repo())
        assert registry.count == 3
        assert len(registry)  == 3
        all_repos = list(registry)
        assert len(all_repos) == 3
        registry.stop()

    def test_contract_violation_prevents_register(self):
        registry = RepositoryRegistry()
        registry.start()
        with pytest.raises(StorageContractViolationError):
            registry.register(object())  # type: ignore
        registry.stop()


# ===========================================================================
# TestRepositoryManager
# ===========================================================================

class TestRepositoryManager:
    def test_not_started_raises(self):
        manager = RepositoryManager()
        factory = RepositoryFactory()
        ctx     = _ctx()
        req     = factory.make_save_request("r1", {"a": 1})
        with pytest.raises(RepositoryNotRunning):
            manager.save(ctx, req)

    def test_lifecycle(self):
        manager = RepositoryManager()
        manager.start()
        assert manager.lifecycle_state().value == "running"
        manager.stop()
        assert manager.lifecycle_state().value == "stopped"

    def test_save_and_find(self):
        manager, repo, factory = _started_manager()
        rid     = _uid()
        ctx_save = _ctx(OperationType.SAVE)
        req_save = factory.make_save_request(rid, _payload(), repository_id=repo.repository_id)
        resp = manager.save(ctx_save, req_save)
        assert resp.succeeded

        ctx_find = _ctx(OperationType.FIND)
        req_find = factory.make_find_request(rid, repository_id=repo.repository_id)
        resp_find = manager.find(ctx_find, req_find)
        assert resp_find.succeeded
        assert resp_find.record is not None
        assert resp_find.record.record_id == rid
        manager.stop()

    def test_save_emits_event(self):
        manager, repo, factory = _started_manager()
        rid  = _uid()
        req  = factory.make_save_request(rid, _payload(), repository_id=repo.repository_id)
        manager.save(_ctx(), req)
        events = manager.events()
        types  = [e.event_type for e in events]
        assert PersistenceEventType.RECORD_SAVED in types
        manager.stop()

    def test_update_emits_event(self):
        manager, repo, factory = _started_manager()
        rid  = _uid()
        manager.save(_ctx(), factory.make_save_request(rid, _payload(), repository_id=repo.repository_id))
        manager.update(_ctx(OperationType.UPDATE), factory.make_update_request(rid, {"qty": 9}, repository_id=repo.repository_id))
        events = [e for e in manager.events() if e.event_type == PersistenceEventType.RECORD_UPDATED]
        assert len(events) == 1
        manager.stop()

    def test_archive_and_restore_emit_events(self):
        manager, repo, factory = _started_manager()
        rid  = _uid()
        manager.save(_ctx(), factory.make_save_request(rid, _payload(), repository_id=repo.repository_id))
        manager.archive(_ctx(OperationType.ARCHIVE), factory.make_archive_request(rid, repository_id=repo.repository_id))
        manager.restore(_ctx(OperationType.RESTORE), factory.make_restore_request(rid, repository_id=repo.repository_id))
        types = [e.event_type for e in manager.events()]
        assert PersistenceEventType.RECORD_ARCHIVED in types
        assert PersistenceEventType.RECORD_RESTORED in types
        manager.stop()

    def test_delete(self):
        manager, repo, factory = _started_manager()
        rid  = _uid()
        manager.save(_ctx(), factory.make_save_request(rid, _payload(), repository_id=repo.repository_id))
        resp = manager.delete(_ctx(OperationType.DELETE), factory.make_delete_request(rid, repository_id=repo.repository_id))
        assert resp.succeeded
        assert not repo.exists(rid)
        manager.stop()

    def test_search(self):
        manager, repo, factory = _started_manager()
        pf = _uid()
        for _ in range(4):
            manager.save(_ctx(), factory.make_save_request(_uid(), _payload(), repository_id=repo.repository_id, portfolio_id=pf))
        resp = manager.search(
            _ctx(OperationType.SEARCH),
            factory.make_search_request(repository_id=repo.repository_id, portfolio_id=pf),
        )
        assert resp.succeeded
        assert resp.total_matches == 4
        manager.stop()

    def test_exists_convenience(self):
        manager, repo, factory = _started_manager()
        rid  = _uid()
        manager.save(_ctx(), factory.make_save_request(rid, _payload(), repository_id=repo.repository_id))
        assert manager.exists(repo.repository_id, rid)
        manager.stop()

    def test_validate_repository_valid(self):
        manager, repo, factory = _started_manager()
        assert manager.validate_repository(repo.repository_id)
        events = [e for e in manager.events() if e.event_type == PersistenceEventType.REPOSITORY_VALIDATED]
        assert events[-1].succeeded is True
        manager.stop()

    def test_validate_repository_missing(self):
        manager, _, _ = _started_manager()
        assert not manager.validate_repository("does-not-exist")
        manager.stop()

    def test_health(self):
        manager, repo, _ = _started_manager()
        h = manager.health(repo.repository_id)
        assert h is not None
        assert h.is_healthy
        manager.stop()

    def test_statistics(self):
        manager, repo, factory = _started_manager()
        for _ in range(3):
            manager.save(_ctx(), factory.make_save_request(_uid(), _payload(), repository_id=repo.repository_id))
        s = manager.statistics(repo.repository_id)
        assert s is not None
        assert s.records_stored == 3
        manager.stop()

    def test_summary(self):
        manager, _, _ = _started_manager()
        s = manager.summary()
        assert "ops_total"   in s
        assert "repositories" in s
        manager.stop()

    def test_latest_events(self):
        manager, repo, factory = _started_manager()
        for _ in range(10):
            manager.save(_ctx(), factory.make_save_request(_uid(), _payload(), repository_id=repo.repository_id))
        latest = manager.latest_events(5)
        assert len(latest) == 5
        manager.stop()

    def test_validation_error_propagates(self):
        manager, repo, factory = _started_manager()
        # SAVE with no record_id
        req = RepositoryRequest(operation=OperationType.SAVE, payload={"a": 1})
        with pytest.raises(PersistenceValidationError):
            manager.save(_ctx(), req)
        manager.stop()

    def test_fallback_to_default_repository(self):
        manager, repo, factory = _started_manager()
        rid = _uid()
        # No repository_id in request — should fall back to default
        req  = factory.make_save_request(rid, _payload())
        resp = manager.save(RepositoryContext(operation=OperationType.SAVE), req)
        assert resp.succeeded
        manager.stop()

    def test_stop_also_stops_registry(self):
        manager, _, _ = _started_manager()
        manager.stop()
        from iios.investment.workflow.engine_lifecycle import EngineState
        assert manager._registry.lifecycle_state() == EngineState.STOPPED


# ===========================================================================
# TestConcurrency
# ===========================================================================

class TestConcurrency:
    def test_100_concurrent_saves(self):
        repo   = _repo()
        errors = []
        saved  = []
        lock   = threading.Lock()

        def worker():
            try:
                rid  = _uid()
                resp = _save(repo, rid)
                if resp.succeeded:
                    with lock:
                        saved.append(rid)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors: {errors}"
        assert len(saved)           == 100
        assert repo.active_count    == 100

    def test_concurrent_update_and_find(self):
        repo    = _repo()
        factory = RepositoryFactory()
        rid     = _uid()
        _save(repo, rid)
        errors  = []

        def updater():
            for _ in range(20):
                try:
                    repo.update(factory.make_update_request(rid, {"qty": 1}))
                except Exception as e:
                    errors.append(e)

        def reader():
            for _ in range(20):
                try:
                    repo.find(factory.make_find_request(rid))
                except Exception as e:
                    errors.append(e)

        threads = (
            [threading.Thread(target=updater) for _ in range(5)]
            + [threading.Thread(target=reader) for _ in range(5)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors

    def test_concurrent_archive_restore(self):
        repo    = _repo()
        factory = RepositoryFactory()
        # Pre-populate 50 records
        rids = [_uid() for _ in range(50)]
        for rid in rids:
            _save(repo, rid)

        errors = []

        def cycle(rid):
            try:
                repo.archive(factory.make_archive_request(rid))
                repo.restore(factory.make_restore_request(rid))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=cycle, args=(rid,)) for rid in rids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert repo.active_count == 50

    def test_manager_concurrent_saves(self):
        manager, repo, factory = _started_manager()
        errors = []

        def worker():
            try:
                manager.save(
                    _ctx(),
                    factory.make_save_request(
                        _uid(), _payload(), repository_id=repo.repository_id
                    ),
                )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        s = manager.summary()
        assert s["ops_success"] == 100
        manager.stop()
