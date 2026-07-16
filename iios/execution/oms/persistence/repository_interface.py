"""iios/execution/oms/persistence/repository_interface.py
==================================================
RepositoryInterface — structural typing Protocol for storage backends.

Provides duck-typing support alongside StorageContract so that
implementations can satisfy the interface without inheriting from
StorageContract (useful for third-party adapters).

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from iios.execution.oms.persistence.storage_metadata import (
    HealthStatus,
    StorageStatistics,
)
from iios.execution.oms.persistence.repository_request import RepositoryRequest
from iios.execution.oms.persistence.repository_response import RepositoryResponse


@runtime_checkable
class RepositoryInterface(Protocol):
    """
    Structural typing Protocol for any persistence backend.

    Implementing this Protocol (implicitly, via duck typing) gives the
    same guarantees as inheriting from StorageContract without requiring
    an inheritance relationship.

    Used by RepositoryValidator.validate_contract() and by type checkers.
    """

    @property
    def repository_id(self) -> str: ...

    def save(self, request: RepositoryRequest) -> RepositoryResponse: ...
    def update(self, request: RepositoryRequest) -> RepositoryResponse: ...
    def delete(self, request: RepositoryRequest) -> RepositoryResponse: ...
    def archive(self, request: RepositoryRequest) -> RepositoryResponse: ...
    def restore(self, request: RepositoryRequest) -> RepositoryResponse: ...
    def exists(self, record_id: str) -> bool: ...
    def find(self, request: RepositoryRequest) -> RepositoryResponse: ...
    def search(self, request: RepositoryRequest) -> RepositoryResponse: ...
    def health(self) -> HealthStatus: ...
    def statistics(self) -> StorageStatistics: ...
    def snapshot(self) -> Any: ...


# The required method names any conforming implementation must expose.
REQUIRED_METHODS: tuple[str, ...] = (
    "repository_id", "save", "update", "delete", "archive", "restore",
    "exists", "find", "search", "health", "statistics", "snapshot",
)
