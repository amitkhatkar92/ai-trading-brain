"""iios/execution/oms/persistence/exceptions.py
==================================================
Exception hierarchy for the IIOS Order Persistence layer.

Error Codes
-----------
PE-000  PersistenceError              — base
PE-001  RecordNotFoundError           — record does not exist
PE-002  DuplicateRecordError          — record_id already in use
PE-003  VersionConflictError          — optimistic concurrency failure
PE-004  RepositoryCapacityError       — repository at max size
PE-005  RepositoryNotRunning          — manager/registry not started
PE-006  PersistenceValidationError    — request validation failure
PE-007  RecoveryError                 — recovery operation failed
PE-008  StorageContractViolationError — implementation misses required method
PE-009  SchemaVersionError            — incompatible schema version
PE-010  SnapshotCorruptedError        — snapshot integrity check failed

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError


class PersistenceError(IIOSError):
    """Base for all Order Persistence errors."""
    DEFAULT_CODE = "PE-000"


class RecordNotFoundError(PersistenceError):
    """No record found for the given identifier."""
    DEFAULT_CODE = "PE-001"

    def __init__(
        self,
        record_id: str,
        *,
        code:           str = "PE-001",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Record '{record_id}' not found",
            code=code, context=context, correlation_id=correlation_id,
        )
        self.record_id = record_id


class DuplicateRecordError(PersistenceError):
    """Record with this ID already exists."""
    DEFAULT_CODE = "PE-002"

    def __init__(
        self,
        record_id: str,
        *,
        code:           str = "PE-002",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Record '{record_id}' already exists",
            code=code, context=context, correlation_id=correlation_id,
        )
        self.record_id = record_id


class VersionConflictError(PersistenceError):
    """Optimistic concurrency conflict on update."""
    DEFAULT_CODE = "PE-003"

    def __init__(
        self,
        record_id:       str,
        expected_version: int,
        actual_version:   int,
        *,
        code:           str = "PE-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Version conflict on '{record_id}': "
            f"expected {expected_version}, found {actual_version}",
            code=code, context=context, correlation_id=correlation_id,
        )
        self.record_id        = record_id
        self.expected_version = expected_version
        self.actual_version   = actual_version


class RepositoryCapacityError(PersistenceError):
    """Repository has reached maximum registered instances."""
    DEFAULT_CODE = "PE-004"


class RepositoryNotRunning(PersistenceError):
    """Manager or registry has not been started."""
    DEFAULT_CODE = "PE-005"


class PersistenceValidationError(PersistenceError):
    """Repository request failed validation."""
    DEFAULT_CODE = "PE-006"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "PE-006",
        errors:         tuple[str, ...] = (),
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context,
                         correlation_id=correlation_id)
        self.errors = errors


class RecoveryError(PersistenceError):
    """Recovery operation failed."""
    DEFAULT_CODE = "PE-007"

    def __init__(
        self,
        recovery_id: str,
        reason:      str = "",
        *,
        code:           str = "PE-007",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Recovery '{recovery_id}' failed: {reason}",
            code=code, context=context, correlation_id=correlation_id,
        )
        self.recovery_id = recovery_id
        self.reason      = reason


class StorageContractViolationError(PersistenceError):
    """Implementation does not satisfy the storage contract."""
    DEFAULT_CODE = "PE-008"

    def __init__(
        self,
        repository_id: str,
        violations:    tuple[str, ...] = (),
        *,
        code:           str = "PE-008",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Repository '{repository_id}' violates storage contract: "
            f"{', '.join(violations)}",
            code=code, context=context, correlation_id=correlation_id,
        )
        self.repository_id = repository_id
        self.violations    = violations


class SchemaVersionError(PersistenceError):
    """Incompatible schema version."""
    DEFAULT_CODE = "PE-009"

    def __init__(
        self,
        record_id:       str,
        expected_schema: str,
        actual_schema:   str,
        *,
        code:           str = "PE-009",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Schema version mismatch on '{record_id}': "
            f"expected '{expected_schema}', found '{actual_schema}'",
            code=code, context=context, correlation_id=correlation_id,
        )
        self.record_id       = record_id
        self.expected_schema = expected_schema
        self.actual_schema   = actual_schema


class SnapshotCorruptedError(PersistenceError):
    """Snapshot failed integrity check."""
    DEFAULT_CODE = "PE-010"

    def __init__(
        self,
        snapshot_id: str,
        *,
        code:           str = "PE-010",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Snapshot '{snapshot_id}' is corrupted",
            code=code, context=context, correlation_id=correlation_id,
        )
        self.snapshot_id = snapshot_id
