"""
iios/execution/recovery/snapshot/exceptions.py
===============================================
Exception hierarchy for the Execution Recovery Snapshot (C7 M5).

Error codes: RS-000 … RS-009

C7 Execution Recovery & Resilience — Phase 1, Module 5
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class RecoverySnapshotError(IIOSError):
    """RS-000: Base exception for all Snapshot errors."""

    error_code = "RS-000"

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=self.error_code, **kwargs)


class SnapshotNotRunningError(RecoverySnapshotError):
    """RS-001: Component method called before start() / after stop()."""

    error_code = "RS-001"

    def __init__(self, message: str = "Snapshot component is not running"):
        super().__init__(message)


class SnapshotValidationError(RecoverySnapshotError):
    """RS-002: Snapshot failed structural or consistency validation."""

    error_code = "RS-002"

    def __init__(self, message: str, *, errors: tuple = ()):
        super().__init__(message)
        self.errors: tuple = errors


class SnapshotBuildError(RecoverySnapshotError):
    """RS-003: Builder could not construct a valid snapshot."""

    error_code = "RS-003"

    def __init__(self, message: str, *, reason: str = ""):
        super().__init__(message)
        self.reason: str = reason


class SnapshotNotFoundError(RecoverySnapshotError):
    """RS-004: No snapshot with the given ID exists in the store."""

    error_code = "RS-004"

    def __init__(self, snapshot_id: str):
        super().__init__(f"Snapshot not found: {snapshot_id!r}")
        self.snapshot_id: str = snapshot_id


class SnapshotDuplicateError(RecoverySnapshotError):
    """RS-005: A snapshot with the same ID was already registered."""

    error_code = "RS-005"

    def __init__(self, snapshot_id: str):
        super().__init__(f"Snapshot already exists: {snapshot_id!r}")
        self.snapshot_id: str = snapshot_id


class SnapshotStoreError(RecoverySnapshotError):
    """RS-006: Store operation failed (capacity exceeded, I/O error, etc.)."""

    error_code = "RS-006"


class SnapshotCacheError(RecoverySnapshotError):
    """RS-007: Cache operation failed."""

    error_code = "RS-007"


class SnapshotRegistryError(RecoverySnapshotError):
    """RS-008: Registry operation failed (duplicate, not found, etc.)."""

    error_code = "RS-008"


class SnapshotVersionError(RecoverySnapshotError):
    """RS-009: Snapshot schema or framework version is incompatible."""

    error_code = "RS-009"

    def __init__(self, version: str, message: str = ""):
        msg = message or f"Incompatible snapshot version: {version!r}"
        super().__init__(msg)
        self.version: str = version
