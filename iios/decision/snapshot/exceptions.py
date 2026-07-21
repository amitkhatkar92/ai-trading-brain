"""
exceptions.py — iios.decision.snapshot
=========================================
Exception hierarchy for the Decision Snapshot subsystem.

Error codes: DS-000 through DS-009

C9 Decision Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class DecisionSnapshotError(IIOSError):
    """Base exception for all snapshot errors.  DS-000"""
    error_code = "DS-000"

    def __init__(self, message: str = "Decision snapshot error", **_kw: object) -> None:
        super().__init__(message, code=self.error_code)


class SnapshotNotFoundError(DecisionSnapshotError):
    """Raised when a snapshot is not found in the store or registry.  DS-001"""
    error_code = "DS-001"

    def __init__(self, snapshot_id: str = "") -> None:
        self.snapshot_id = snapshot_id
        super().__init__(f"Snapshot not found: {snapshot_id!r}")


class SnapshotBuildError(DecisionSnapshotError):
    """Raised when a snapshot cannot be built from the supplied inputs.  DS-002"""
    error_code = "DS-002"

    def __init__(self, message: str = "Snapshot build error") -> None:
        super().__init__(message)


class SnapshotValidationError(DecisionSnapshotError):
    """Raised when snapshot validation fails.  DS-003"""
    error_code = "DS-003"

    def __init__(
        self,
        message:       str           = "Snapshot validation failed",
        failed_checks: tuple[str, ...] = (),
    ) -> None:
        self.failed_checks = tuple(failed_checks)
        super().__init__(message)


class SnapshotRegistryError(DecisionSnapshotError):
    """Raised on registry capacity or consistency violations.  DS-004"""
    error_code = "DS-004"

    def __init__(self, message: str = "Snapshot registry error") -> None:
        super().__init__(message)


class SnapshotStoreError(DecisionSnapshotError):
    """Raised on store I/O or consistency failures.  DS-005"""
    error_code = "DS-005"

    def __init__(self, message: str = "Snapshot store error") -> None:
        super().__init__(message)


class SnapshotCacheError(DecisionSnapshotError):
    """Raised on cache operation failures.  DS-006"""
    error_code = "DS-006"

    def __init__(self, message: str = "Snapshot cache error") -> None:
        super().__init__(message)


class DuplicateSnapshotError(DecisionSnapshotError):
    """Raised when a snapshot with the same ID already exists.  DS-007"""
    error_code = "DS-007"

    def __init__(self, snapshot_id: str = "") -> None:
        self.snapshot_id = snapshot_id
        super().__init__(f"Duplicate snapshot ID: {snapshot_id!r}")


class SnapshotVersionError(DecisionSnapshotError):
    """Raised on snapshot version incompatibility or sequence violations.  DS-008"""
    error_code = "DS-008"

    def __init__(self, message: str = "Snapshot version error") -> None:
        super().__init__(message)


class SnapshotConfigurationError(DecisionSnapshotError):
    """Raised when snapshot subsystem configuration is invalid.  DS-009"""
    error_code = "DS-009"

    def __init__(self, message: str = "Snapshot configuration error") -> None:
        super().__init__(message)
