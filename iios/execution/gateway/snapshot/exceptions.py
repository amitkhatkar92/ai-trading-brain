"""iios/execution/gateway/snapshot/exceptions.py
==================================================
Exception hierarchy for the Execution Gateway Snapshot module.

Error code prefix: GS

C6 Execution Intelligence — Phase 5, Module 5
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class GatewaySnapshotError(IIOSError):
    """Base exception for all Snapshot module errors.  GS-000."""

    error_code = "GS-000"

    def __init__(self, message: str = "Gateway snapshot error.") -> None:
        super().__init__(message)


class SnapshotBuildError(GatewaySnapshotError):
    """Snapshot could not be built due to missing or invalid input.  GS-001."""

    error_code = "GS-001"

    def __init__(self, reason: str = "") -> None:
        msg = "Snapshot build failed."
        if reason:
            msg = f"Snapshot build failed: {reason}"
        super().__init__(msg)
        self.reason = reason


class SnapshotValidationError(GatewaySnapshotError):
    """Snapshot failed validation.  GS-002."""

    error_code = "GS-002"

    def __init__(
        self,
        message: str = "Snapshot validation failed.",
        errors: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.errors = errors


class SnapshotNotFoundError(GatewaySnapshotError):
    """No snapshot with the given ID exists.  GS-003."""

    error_code = "GS-003"

    def __init__(self, snapshot_id: str) -> None:
        super().__init__(f"Snapshot '{snapshot_id}' not found.")
        self.snapshot_id = snapshot_id


class DuplicateSnapshotError(GatewaySnapshotError):
    """A snapshot with the same ID is already stored.  GS-004."""

    error_code = "GS-004"

    def __init__(self, snapshot_id: str) -> None:
        super().__init__(
            f"Snapshot '{snapshot_id}' is already stored. "
            "Each snapshot must have a unique ID."
        )
        self.snapshot_id = snapshot_id


class SnapshotVersionError(GatewaySnapshotError):
    """Snapshot version is invalid or incompatible.  GS-005."""

    error_code = "GS-005"

    def __init__(self, message: str = "Snapshot version error.") -> None:
        super().__init__(message)


class SnapshotStoreNotRunningError(GatewaySnapshotError):
    """The snapshot store is not in RUNNING state.  GS-006."""

    error_code = "GS-006"

    def __init__(self) -> None:
        super().__init__(
            "GatewaySnapshotStore is not running. "
            "Call start() before publishing or retrieving snapshots."
        )


class SnapshotStoreCapacityError(GatewaySnapshotError):
    """The snapshot store has reached maximum capacity.  GS-007."""

    error_code = "GS-007"

    def __init__(self, max_count: int) -> None:
        super().__init__(
            f"GatewaySnapshotStore is at capacity (max={max_count}). "
            "Archive or remove old snapshots before publishing new ones."
        )
        self.max_count = max_count
