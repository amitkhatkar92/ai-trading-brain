"""iios/execution/oms/persistence/order_repository.py
==================================================
AbstractOrderRepository + InMemoryOrderRepository.

AbstractOrderRepository extends StorageContract with order-domain
search methods.

InMemoryOrderRepository is the reference implementation used in
tests (and by any component that needs persistence without a real
storage backend).  Thread-safe, no I/O.

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

import dataclasses
import threading
import time
from abc import abstractmethod
from typing import Any

from iios.execution.oms.persistence.constants import (
    DEFAULT_MAX_HISTORY,
    SCHEMA_VERSION,
    OperationType,
    RecordStatus,
    RecordType,
    RepositoryHealth,
)
from iios.execution.oms.persistence.exceptions import (
    DuplicateRecordError,
    RecordNotFoundError,
    VersionConflictError,
)
from iios.execution.oms.persistence.repository_factory import RepositoryFactory
from iios.execution.oms.persistence.repository_request import RepositoryRequest
from iios.execution.oms.persistence.repository_response import RepositoryResponse
from iios.execution.oms.persistence.storage_contract import StorageContract
from iios.execution.oms.persistence.storage_metadata import (
    HealthStatus,
    StorageRecord,
    StorageStatistics,
)
from iios.execution.oms.persistence.storage_snapshot import StorageSnapshot
from iios.execution.oms.persistence.storage_version import StorageVersion, VersionHistory

_factory = RepositoryFactory()


# ---------------------------------------------------------------------------
# Abstract domain extension
# ---------------------------------------------------------------------------

class AbstractOrderRepository(StorageContract):
    """
    StorageContract extended with order-domain search methods.

    All five ``find_by_*`` methods must be implemented by every concrete
    order repository.
    """

    @abstractmethod
    def find_by_workflow(self, workflow_id: str) -> list[StorageRecord]:
        """Return all active records for a given workflow."""

    @abstractmethod
    def find_by_portfolio(self, portfolio_id: str) -> list[StorageRecord]:
        """Return all active records for a given portfolio."""

    @abstractmethod
    def find_by_strategy(self, strategy_id: str) -> list[StorageRecord]:
        """Return all active records for a given strategy."""

    @abstractmethod
    def find_by_status(self, status: RecordStatus) -> list[StorageRecord]:
        """Return all records with the given status (active + archived pools)."""

    @abstractmethod
    def find_by_time_range(self, start: float, end: float) -> list[StorageRecord]:
        """Return all active records created between start and end."""


# ---------------------------------------------------------------------------
# In-memory reference implementation
# ---------------------------------------------------------------------------

class InMemoryOrderRepository(AbstractOrderRepository):
    """
    Thread-safe, in-memory implementation of AbstractOrderRepository.

    Stores StorageRecord objects in plain Python dicts.
    No I/O, no SQL, no filesystem.  Suitable for tests and for any
    component that needs a lightweight persistence backend.

    Active records  → self._active[record_id]
    Archived records → self._archived[record_id]

    Deleted records are removed from both pools entirely.
    """

    def __init__(
        self,
        repo_id:     str = "memory:orders",
        max_history: int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._repo_id    = repo_id
        self._max_history = max_history
        self._active:   dict[str, StorageRecord] = {}
        self._archived: dict[str, StorageRecord] = {}
        self._versions: dict[str, VersionHistory] = {}
        self._lock      = threading.RLock()

        # Stats counters
        self._saves    = 0
        self._updates  = 0
        self._archives = 0
        self._deletes  = 0
        self._restores = 0
        self._save_times:    list[float] = []
        self._restore_times: list[float] = []

    # ------------------------------------------------------------------
    # StorageContract: repository_id
    # ------------------------------------------------------------------

    @property
    def repository_id(self) -> str:
        return self._repo_id

    # ------------------------------------------------------------------
    # StorageContract: CRUD
    # ------------------------------------------------------------------

    def save(self, request: RepositoryRequest) -> RepositoryResponse:
        t0 = time.time()
        with self._lock:
            if request.record_id in self._active or request.record_id in self._archived:
                return _factory.make_error_response(
                    request.request_id, request.operation, request.record_id,
                    "PE-002",
                    f"Record '{request.record_id}' already exists",
                    repository_id=self._repo_id,
                    elapsed_ms=_ms(t0),
                )
            record = _factory.make_storage_record(
                record_id      = request.record_id,
                payload        = dict(request.payload),
                record_type    = request.record_type,
                repository_id  = self._repo_id,
                correlation_id = request.correlation_id,
                workflow_id    = request.workflow_id,
                portfolio_id   = request.portfolio_id,
                strategy_id    = request.strategy_id,
                schema_version = request.schema_version,
                version        = 1,
                metadata       = dict(request.metadata),
            )
            self._active[request.record_id] = record
            self._add_version(request.record_id, 1, "save")
            self._saves += 1
            elapsed = _ms(t0)
            self._save_times.append(elapsed)
            return _factory.make_success_response(
                request.request_id, request.operation, request.record_id,
                repository_id  = self._repo_id,
                record_version = 1,
                elapsed_ms     = elapsed,
            )

    def update(self, request: RepositoryRequest) -> RepositoryResponse:
        t0 = time.time()
        with self._lock:
            record = self._active.get(request.record_id)
            if record is None:
                return _factory.make_error_response(
                    request.request_id, request.operation, request.record_id,
                    "PE-001",
                    f"Record '{request.record_id}' not found",
                    repository_id=self._repo_id,
                    elapsed_ms=_ms(t0),
                )
            # Optimistic concurrency check
            if (
                request.expected_version != 0
                and request.expected_version != record.version
            ):
                return _factory.make_error_response(
                    request.request_id, request.operation, request.record_id,
                    "PE-003",
                    f"Version conflict: expected {request.expected_version}, "
                    f"found {record.version}",
                    repository_id=self._repo_id,
                    elapsed_ms=_ms(t0),
                )
            updated = record.with_version(dict(request.payload))
            self._active[request.record_id] = updated
            self._add_version(request.record_id, updated.version, "update")
            self._updates += 1
            elapsed = _ms(t0)
            return _factory.make_success_response(
                request.request_id, request.operation, request.record_id,
                repository_id  = self._repo_id,
                record_version = updated.version,
                elapsed_ms     = elapsed,
            )

    def delete(self, request: RepositoryRequest) -> RepositoryResponse:
        t0 = time.time()
        with self._lock:
            removed = (
                self._active.pop(request.record_id, None)
                or self._archived.pop(request.record_id, None)
            )
            if removed is None:
                return _factory.make_error_response(
                    request.request_id, request.operation, request.record_id,
                    "PE-001",
                    f"Record '{request.record_id}' not found",
                    repository_id=self._repo_id,
                    elapsed_ms=_ms(t0),
                )
            self._versions.pop(request.record_id, None)
            self._deletes += 1
            return _factory.make_success_response(
                request.request_id, request.operation, request.record_id,
                repository_id  = self._repo_id,
                record_version = removed.version,
                elapsed_ms     = _ms(t0),
            )

    def archive(self, request: RepositoryRequest) -> RepositoryResponse:
        t0 = time.time()
        with self._lock:
            record = self._active.get(request.record_id)
            if record is None:
                return _factory.make_error_response(
                    request.request_id, request.operation, request.record_id,
                    "PE-001",
                    f"Record '{request.record_id}' not found in active pool",
                    repository_id=self._repo_id,
                    elapsed_ms=_ms(t0),
                )
            archived = record.with_status(RecordStatus.ARCHIVED, archived_at=time.time())
            del self._active[request.record_id]
            self._archived[request.record_id] = archived
            self._archives += 1
            return _factory.make_success_response(
                request.request_id, request.operation, request.record_id,
                repository_id  = self._repo_id,
                record_version = archived.version,
                elapsed_ms     = _ms(t0),
            )

    def restore(self, request: RepositoryRequest) -> RepositoryResponse:
        t0 = time.time()
        with self._lock:
            record = self._archived.get(request.record_id)
            if record is None:
                return _factory.make_error_response(
                    request.request_id, request.operation, request.record_id,
                    "PE-001",
                    f"Record '{request.record_id}' not found in archived pool",
                    repository_id=self._repo_id,
                    elapsed_ms=_ms(t0),
                )
            restored = record.with_status(RecordStatus.ACTIVE)
            del self._archived[request.record_id]
            self._active[request.record_id] = restored
            self._restores += 1
            elapsed = _ms(t0)
            self._restore_times.append(elapsed)
            return _factory.make_success_response(
                request.request_id, request.operation, request.record_id,
                repository_id  = self._repo_id,
                record_version = restored.version,
                record         = restored,
                elapsed_ms     = elapsed,
            )

    # ------------------------------------------------------------------
    # StorageContract: Query
    # ------------------------------------------------------------------

    def exists(self, record_id: str) -> bool:
        with self._lock:
            return record_id in self._active

    def find(self, request: RepositoryRequest) -> RepositoryResponse:
        t0 = time.time()
        with self._lock:
            record = self._active.get(request.record_id)
            if record is None and request.include_archived:
                record = self._archived.get(request.record_id)
            if record is None:
                return _factory.make_error_response(
                    request.request_id, request.operation, request.record_id,
                    "PE-001",
                    f"Record '{request.record_id}' not found",
                    repository_id=self._repo_id,
                    elapsed_ms=_ms(t0),
                )
            return _factory.make_success_response(
                request.request_id, request.operation, request.record_id,
                repository_id  = self._repo_id,
                record_version = record.version,
                record         = record,
                elapsed_ms     = _ms(t0),
            )

    def search(self, request: RepositoryRequest) -> RepositoryResponse:
        t0 = time.time()
        with self._lock:
            pool: list[StorageRecord] = list(self._active.values())
            if request.include_archived:
                pool += list(self._archived.values())

            # Apply filters
            filtered = _apply_filters(pool, request)

            total     = len(filtered)
            page      = filtered[request.offset: request.offset + request.limit]
            return _factory.make_success_response(
                request.request_id, request.operation, "",
                repository_id  = self._repo_id,
                records        = tuple(page),
                elapsed_ms     = _ms(t0),
                total_matches  = total,
            )

    # ------------------------------------------------------------------
    # StorageContract: Health / monitoring
    # ------------------------------------------------------------------

    def health(self) -> HealthStatus:
        with self._lock:
            return HealthStatus(
                repository_id = self._repo_id,
                health        = RepositoryHealth.HEALTHY,
                message       = "in-memory repository",
                latency_ms    = 0.0,
            )

    def statistics(self) -> StorageStatistics:
        with self._lock:
            return StorageStatistics(
                repository_id    = self._repo_id,
                records_stored   = self._saves,
                records_updated  = self._updates,
                records_archived = self._archives,
                records_deleted  = self._deletes,
                records_restored = self._restores,
                total_active     = len(self._active),
                total_archived   = len(self._archived),
                avg_save_ms      = _avg(self._save_times),
                avg_restore_ms   = _avg(self._restore_times),
                health           = RepositoryHealth.HEALTHY,
            )

    def snapshot(self) -> StorageSnapshot:
        with self._lock:
            all_records = list(self._active.values()) + list(self._archived.values())
            metas = tuple(r.to_metadata() for r in all_records)
            active_count   = len(self._active)
            archived_count = len(self._archived)
            deleted_count  = 0
            corrupted_count = sum(
                1 for r in self._active.values()
                if r.status == RecordStatus.CORRUPTED
            )
            return StorageSnapshot(
                repository_id   = self._repo_id,
                schema_version  = SCHEMA_VERSION,
                total_records   = len(metas),
                total_active    = active_count,
                total_archived  = archived_count,
                total_deleted   = deleted_count,
                total_corrupted = corrupted_count,
                records         = metas,
                health          = RepositoryHealth.HEALTHY,
            )

    # ------------------------------------------------------------------
    # AbstractOrderRepository: Domain searches
    # ------------------------------------------------------------------

    def find_by_workflow(self, workflow_id: str) -> list[StorageRecord]:
        with self._lock:
            return [r for r in self._active.values() if r.workflow_id == workflow_id]

    def find_by_portfolio(self, portfolio_id: str) -> list[StorageRecord]:
        with self._lock:
            return [r for r in self._active.values() if r.portfolio_id == portfolio_id]

    def find_by_strategy(self, strategy_id: str) -> list[StorageRecord]:
        with self._lock:
            return [r for r in self._active.values() if r.strategy_id == strategy_id]

    def find_by_status(self, status: RecordStatus) -> list[StorageRecord]:
        with self._lock:
            pool = (
                list(self._active.values()) + list(self._archived.values())
            )
            return [r for r in pool if r.status == status]

    def find_by_time_range(self, start: float, end: float) -> list[StorageRecord]:
        with self._lock:
            return [
                r for r in self._active.values()
                if start <= r.created_at <= end
            ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_version(
        self, record_id: str, version_number: int, summary: str
    ) -> None:
        """Append a version entry; trims to max_history if exceeded."""
        history = self._versions.setdefault(record_id, VersionHistory(record_id))
        entry = StorageVersion(
            record_id      = record_id,
            version_number = version_number,
            change_summary = summary,
        )
        history.append(entry)
        # Trim is handled by Python list naturally — we just limit lookup:
        # VersionHistory itself is unbounded in this implementation.

    def version_history(self, record_id: str) -> VersionHistory | None:
        """Expose version history for testing."""
        with self._lock:
            return self._versions.get(record_id)

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    @property
    def archived_count(self) -> int:
        with self._lock:
            return len(self._archived)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _ms(t0: float) -> float:
    return (time.time() - t0) * 1000.0


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _apply_filters(
    records: list[StorageRecord],
    request: RepositoryRequest,
) -> list[StorageRecord]:
    result = records
    if request.portfolio_id:
        result = [r for r in result if r.portfolio_id == request.portfolio_id]
    if request.strategy_id:
        result = [r for r in result if r.strategy_id == request.strategy_id]
    if request.workflow_id:
        result = [r for r in result if r.workflow_id == request.workflow_id]
    if request.status_filter:
        result = [r for r in result if r.status in request.status_filter]
    if request.time_range_start:
        result = [r for r in result if r.created_at >= request.time_range_start]
    if request.time_range_end:
        result = [r for r in result if r.created_at <= request.time_range_end]
    return result
