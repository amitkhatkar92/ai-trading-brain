"""
exceptions.py — iios.supervisor.snapshot
-------------------------------------------
Exception hierarchy for the AI Supervisor Snapshot.

Error-code prefix: SSN (Supervisor Snapshot).

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 5
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class SupervisorSnapshotError(IIOSError):
    """Base exception for the Supervisor Snapshot subsystem (SSN-000)."""
    error_code: str = "SSN-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class SupervisorSnapshotNotFoundError(SupervisorSnapshotError):
    """Snapshot not found in registry or store (SSN-001)."""
    error_code = "SSN-001"

    def __init__(self, snapshot_id: str = "") -> None:
        detail = f": {snapshot_id!r}" if snapshot_id else ""
        super().__init__(
            f"Supervisor snapshot not found{detail}",
            code=self.error_code,
        )
        self.snapshot_id: str = snapshot_id


class SupervisorSnapshotValidationError(SupervisorSnapshotError):
    """Snapshot failed validation (SSN-002)."""
    error_code = "SSN-002"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Supervisor snapshot validation error: {message}",
            code=self.error_code,
        )


class SupervisorSnapshotBuildError(SupervisorSnapshotError):
    """Snapshot build failed (SSN-003)."""
    error_code = "SSN-003"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Supervisor snapshot build error: {message}",
            code=self.error_code,
        )


class SupervisorSnapshotRegistryError(SupervisorSnapshotError):
    """Registry operation failed (SSN-004)."""
    error_code = "SSN-004"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Supervisor snapshot registry error: {message}",
            code=self.error_code,
        )


class SupervisorSnapshotCapacityError(SupervisorSnapshotError):
    """Registry or store at capacity (SSN-005)."""
    error_code = "SSN-005"

    def __init__(self, limit: int = 0) -> None:
        super().__init__(
            f"Supervisor snapshot capacity exceeded (limit={limit})",
            code=self.error_code,
        )
        self.limit: int = limit


class SupervisorSnapshotStoreError(SupervisorSnapshotError):
    """Store operation failed (SSN-006)."""
    error_code = "SSN-006"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Supervisor snapshot store error: {message}",
            code=self.error_code,
        )


class SupervisorSnapshotCacheError(SupervisorSnapshotError):
    """Cache operation failed (SSN-007)."""
    error_code = "SSN-007"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Supervisor snapshot cache error: {message}",
            code=self.error_code,
        )


class SupervisorSnapshotBundleError(SupervisorSnapshotError):
    """Bundle operation failed (SSN-008)."""
    error_code = "SSN-008"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Supervisor snapshot bundle error: {message}",
            code=self.error_code,
        )
