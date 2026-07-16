"""iios/execution/snapshot/exceptions.py
==================================================
Exception hierarchy for the IIOS Execution Snapshot package.

All exceptions inherit from IIOSError.

Error Codes
-----------
ESN-000  ExecutionSnapshotError       — base
ESN-001  SnapshotBuildError           — builder failure
ESN-002  SnapshotValidationError      — validation failure
ESN-003  SnapshotNotFoundError        — snapshot_id not in store/registry
ESN-004  DuplicateSnapshotError       — duplicate snapshot_id
ESN-005  SnapshotCapacityError        — store/registry full
ESN-006  SnapshotStoreNotRunning      — store not started
ESN-007  SnapshotIncompleteError      — required fields missing
ESN-008  SnapshotInconsistencyError   — ID or state mismatch
ESN-009  SnapshotSerializationError   — cannot serialize/deserialize
ESN-010  SnapshotHistoryError         — history operation failure
ESN-011  SnapshotVersionError         — incompatible schema version

C6 Execution Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError


class ExecutionSnapshotError(IIOSError):
    """Base for all Execution Snapshot errors."""
    DEFAULT_CODE = "ESN-000"


class SnapshotBuildError(ExecutionSnapshotError):
    """Builder failed to assemble the snapshot."""
    DEFAULT_CODE = "ESN-001"


class SnapshotValidationError(ExecutionSnapshotError):
    """Snapshot validation failed."""
    DEFAULT_CODE = "ESN-002"

    def __init__(
        self,
        message:        str,
        *,
        code:           str = "ESN-002",
        errors:         tuple[str, ...] = (),
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context,
                         correlation_id=correlation_id)
        self.errors = errors


class SnapshotNotFoundError(ExecutionSnapshotError):
    """No snapshot registered under the given snapshot_id."""
    DEFAULT_CODE = "ESN-003"

    def __init__(
        self,
        snapshot_id: str,
        *,
        code:           str = "ESN-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"ExecutionSnapshot not found: '{snapshot_id}'",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.snapshot_id = snapshot_id


class DuplicateSnapshotError(ExecutionSnapshotError):
    """A snapshot with this ID already exists."""
    DEFAULT_CODE = "ESN-004"

    def __init__(
        self,
        snapshot_id: str,
        *,
        code:           str = "ESN-004",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"ExecutionSnapshot already registered: '{snapshot_id}'",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.snapshot_id = snapshot_id


class SnapshotCapacityError(ExecutionSnapshotError):
    """Store or registry has reached maximum capacity."""
    DEFAULT_CODE = "ESN-005"


class SnapshotStoreNotRunning(ExecutionSnapshotError):
    """Store was not started before use."""
    DEFAULT_CODE = "ESN-006"


class SnapshotIncompleteError(ExecutionSnapshotError):
    """Required fields are missing from the snapshot."""
    DEFAULT_CODE = "ESN-007"

    def __init__(
        self,
        message:        str,
        *,
        missing_fields: tuple[str, ...] = (),
        code:           str = "ESN-007",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context,
                         correlation_id=correlation_id)
        self.missing_fields = missing_fields


class SnapshotInconsistencyError(ExecutionSnapshotError):
    """ID or state mismatch detected between snapshot fields."""
    DEFAULT_CODE = "ESN-008"


class SnapshotSerializationError(ExecutionSnapshotError):
    """Cannot serialize or deserialize the snapshot."""
    DEFAULT_CODE = "ESN-009"


class SnapshotHistoryError(ExecutionSnapshotError):
    """History operation failed."""
    DEFAULT_CODE = "ESN-010"


class SnapshotVersionError(ExecutionSnapshotError):
    """Snapshot schema version is incompatible."""
    DEFAULT_CODE = "ESN-011"
