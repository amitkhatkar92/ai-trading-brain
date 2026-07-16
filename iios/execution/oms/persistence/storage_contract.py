"""iios/execution/oms/persistence/storage_contract.py
==================================================
StorageContract — abstract base class every repository implementation must satisfy.

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from iios.execution.oms.persistence.storage_metadata import (
    HealthStatus,
    StorageRecord,
    StorageStatistics,
)
from iios.execution.oms.persistence.repository_request import RepositoryRequest
from iios.execution.oms.persistence.repository_response import RepositoryResponse


class StorageContract(ABC):
    """
    Abstract base class defining the required contract for every repository.

    Concrete implementations (e.g., InMemoryOrderRepository) must implement
    all abstract methods.  No I/O, no SQL, no filesystem requirements are
    imposed here; this is a pure interface.

    Method contract summary
    -----------------------
    save(request)      → RepositoryResponse   persist a new record
    update(request)    → RepositoryResponse   overwrite existing record (versions bump)
    delete(request)    → RepositoryResponse   permanently remove a record
    archive(request)   → RepositoryResponse   move to archived pool
    restore(request)   → RepositoryResponse   move back to active pool
    exists(record_id)  → bool                 cheap existence check
    find(request)      → RepositoryResponse   fetch one record by ID
    search(request)    → RepositoryResponse   query with filters
    health()           → HealthStatus         live health check
    statistics()       → StorageStatistics    operational counters
    snapshot()         → StorageSnapshot      point-in-time metadata dump
    """

    # ------------------------------------------------------------------
    # Every implementation must declare its repository_id.
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def repository_id(self) -> str: ...

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @abstractmethod
    def save(self, request: RepositoryRequest) -> RepositoryResponse:
        """Persist a new record.  Raises DuplicateRecordError if ID exists."""

    @abstractmethod
    def update(self, request: RepositoryRequest) -> RepositoryResponse:
        """
        Update an existing active record.

        Expected version must match the stored version (optimistic concurrency).
        Raises VersionConflictError on mismatch, RecordNotFoundError if absent.
        """

    @abstractmethod
    def delete(self, request: RepositoryRequest) -> RepositoryResponse:
        """
        Permanently remove a record.

        Returns error response (not exception) if record is not found.
        """

    @abstractmethod
    def archive(self, request: RepositoryRequest) -> RepositoryResponse:
        """Move an active record to the archived pool."""

    @abstractmethod
    def restore(self, request: RepositoryRequest) -> RepositoryResponse:
        """Move an archived record back to the active pool."""

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    @abstractmethod
    def exists(self, record_id: str) -> bool:
        """Return True if the record is in the active pool."""

    @abstractmethod
    def find(self, request: RepositoryRequest) -> RepositoryResponse:
        """
        Fetch one record by request.record_id.

        Returns a success response with record= populated, or an error
        response with error_code=PE-001 if not found.
        """

    @abstractmethod
    def search(self, request: RepositoryRequest) -> RepositoryResponse:
        """
        Search for records matching the filters in request.

        Honoured filters: portfolio_id, strategy_id, workflow_id,
        status_filter, time_range_start/end, include_archived.
        Respects limit and offset.
        """

    # ------------------------------------------------------------------
    # Health / monitoring
    # ------------------------------------------------------------------

    @abstractmethod
    def health(self) -> HealthStatus:
        """Return current health status of this repository."""

    @abstractmethod
    def statistics(self) -> StorageStatistics:
        """Return operational counters for this repository."""

    @abstractmethod
    def snapshot(self) -> Any:
        """
        Return a StorageSnapshot (point-in-time metadata view).

        Import deferred to avoid circular references; implementations
        must return a StorageSnapshot instance.
        """
