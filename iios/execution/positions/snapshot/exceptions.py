"""iios/execution/positions/snapshot/exceptions.py
==================================================
Exception hierarchy for the IIOS Position Snapshot module.

Error Codes
-----------
PS5-000  PositionSnapshotError          — base
PS5-001  PositionSnapshotNotRunningError — store/registry not started
PS5-002  SnapshotNotFoundError           — snapshot not in store
PS5-003  DuplicateSnapshotError          — snapshot_id already exists
PS5-004  SnapshotValidationError         — validation checks failed
PS5-005  SnapshotBuildError              — builder rejected inputs
PS5-006  SnapshotCapacityError           — store at max capacity
PS5-007  SnapshotStoreError              — store operation failed
PS5-008  SnapshotCacheError              — cache operation failed
PS5-009  SnapshotVersionError            — version compatibility issue

C6 Execution Intelligence — Phase 3, Module 5
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from iios.common.errors.exceptions import IIOSError


class PositionSnapshotError(IIOSError):
    """Base for all Position Snapshot errors."""
    DEFAULT_CODE = "PS5-000"


class PositionSnapshotNotRunningError(PositionSnapshotError):
    """The snapshot store or registry has not been started."""
    DEFAULT_CODE = "PS5-001"

    def __init__(
        self,
        *,
        code:           str = "PS5-001",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            "PositionSnapshotStore is not running",
            code=code, context=context, correlation_id=correlation_id,
        )


class SnapshotNotFoundError(PositionSnapshotError):
    """No snapshot found for the given identifier."""
    DEFAULT_CODE = "PS5-002"

    def __init__(
        self,
        identifier: str,
        *,
        code:           str = "PS5-002",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Snapshot not found: '{identifier}'",
            code=code,
            context=context or {"identifier": identifier},
            correlation_id=correlation_id,
        )
        self.identifier = identifier


class DuplicateSnapshotError(PositionSnapshotError):
    """A snapshot with this ID already exists in the store."""
    DEFAULT_CODE = "PS5-003"

    def __init__(
        self,
        snapshot_id: str,
        *,
        code:           str = "PS5-003",
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


class SnapshotValidationError(PositionSnapshotError):
    """One or more snapshot validation checks failed."""
    DEFAULT_CODE = "PS5-004"

    def __init__(
        self,
        message: str,
        *,
        errors:         Tuple[str, ...] = (),
        code:           str = "PS5-004",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)
        self.errors = errors


class SnapshotBuildError(PositionSnapshotError):
    """The snapshot builder rejected the provided inputs."""
    DEFAULT_CODE = "PS5-005"

    def __init__(
        self,
        message:     str,
        position_id: str = "",
        *,
        errors:         Tuple[str, ...] = (),
        code:           str = "PS5-005",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code,
            context=context or {"position_id": position_id},
            correlation_id=correlation_id,
        )
        self.position_id = position_id
        self.errors      = errors


class SnapshotCapacityError(PositionSnapshotError):
    """The snapshot store has reached maximum capacity."""
    DEFAULT_CODE = "PS5-006"

    def __init__(
        self,
        capacity: int,
        *,
        code:           str = "PS5-006",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"SnapshotStore at maximum capacity ({capacity})",
            code=code,
            context=context or {"capacity": capacity},
            correlation_id=correlation_id,
        )
        self.capacity = capacity


class SnapshotStoreError(PositionSnapshotError):
    """A snapshot store operation failed unexpectedly."""
    DEFAULT_CODE = "PS5-007"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "PS5-007",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)


class SnapshotCacheError(PositionSnapshotError):
    """A snapshot cache operation failed unexpectedly."""
    DEFAULT_CODE = "PS5-008"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "PS5-008",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)


class SnapshotVersionError(PositionSnapshotError):
    """A snapshot schema version is incompatible."""
    DEFAULT_CODE = "PS5-009"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "PS5-009",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)
