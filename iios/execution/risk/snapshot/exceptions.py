"""iios/execution/risk/snapshot/exceptions.py
==================================================
Exception hierarchy for the IIOS Execution Risk Snapshot layer.

Error Codes
-----------
ERS-000  ExecutionRiskSnapshotError      — base
ERS-001  SnapshotBuildError              — builder failed
ERS-002  SnapshotValidationError         — validation failed
ERS-003  SnapshotNotFoundError           — snapshot not found by ID
ERS-004  DuplicateSnapshotError          — snapshot_id already stored
ERS-005  SnapshotVersionError            — incompatible schema version
ERS-006  SnapshotStoreError              — store/cache operation failed
ERS-007  SnapshotRegistryNotRunningError — registry not started
ERS-008  SnapshotSerializationError      — to_dict / to_json failed

C6 Execution Intelligence — Phase 4, Module 5
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError


class ExecutionRiskSnapshotError(IIOSError):
    """Base for all Execution Risk Snapshot errors."""
    DEFAULT_CODE = "ERS-000"


class SnapshotBuildError(ExecutionRiskSnapshotError):
    """Builder failed to assemble a snapshot."""
    DEFAULT_CODE = "ERS-001"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "ERS-001",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code, context=context, correlation_id=correlation_id,
        )


class SnapshotValidationError(ExecutionRiskSnapshotError):
    """Snapshot failed validation."""
    DEFAULT_CODE = "ERS-002"

    def __init__(
        self,
        message: str,
        *,
        snapshot_id:    str = "",
        code:           str = "ERS-002",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code,
            context=context or {"snapshot_id": snapshot_id},
            correlation_id=correlation_id,
        )
        self.snapshot_id = snapshot_id


class SnapshotNotFoundError(ExecutionRiskSnapshotError):
    """No snapshot found for the given identifier."""
    DEFAULT_CODE = "ERS-003"

    def __init__(
        self,
        snapshot_id: str,
        *,
        code:           str = "ERS-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Snapshot '{snapshot_id}' not found",
            code=code,
            context=context or {"snapshot_id": snapshot_id},
            correlation_id=correlation_id,
        )
        self.snapshot_id = snapshot_id


class DuplicateSnapshotError(ExecutionRiskSnapshotError):
    """A snapshot with the same ID already exists."""
    DEFAULT_CODE = "ERS-004"

    def __init__(
        self,
        snapshot_id: str,
        *,
        code:           str = "ERS-004",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Snapshot '{snapshot_id}' already exists",
            code=code,
            context=context or {"snapshot_id": snapshot_id},
            correlation_id=correlation_id,
        )
        self.snapshot_id = snapshot_id


class SnapshotVersionError(ExecutionRiskSnapshotError):
    """Incompatible snapshot schema version."""
    DEFAULT_CODE = "ERS-005"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "ERS-005",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code, context=context, correlation_id=correlation_id,
        )


class SnapshotStoreError(ExecutionRiskSnapshotError):
    """Store or cache operation failed."""
    DEFAULT_CODE = "ERS-006"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "ERS-006",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code, context=context, correlation_id=correlation_id,
        )


class SnapshotRegistryNotRunningError(ExecutionRiskSnapshotError):
    """The registry is not in the RUNNING state."""
    DEFAULT_CODE = "ERS-007"

    def __init__(
        self,
        *,
        code:           str = "ERS-007",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            "SnapshotRegistry is not running; call start() before use",
            code=code, context=context, correlation_id=correlation_id,
        )


class SnapshotSerializationError(ExecutionRiskSnapshotError):
    """Snapshot serialization (to_dict / to_json) failed."""
    DEFAULT_CODE = "ERS-008"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "ERS-008",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code, context=context, correlation_id=correlation_id,
        )
