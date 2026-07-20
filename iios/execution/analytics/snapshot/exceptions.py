"""
iios/execution/analytics/snapshot/exceptions.py
================================================
Typed exceptions for the Execution Analytics Snapshot package (C8 M5).

Error code prefix: EAS

C8 Execution Analytics & Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from typing import Tuple

from iios.common.errors.exceptions import IIOSError


class SnapshotError(IIOSError):
    """EAS-000 — Base class for all snapshot errors."""

    error_code = "EAS-000"

    def __init__(self, message: str = "Analytics snapshot error.") -> None:
        super().__init__(message, code=self.error_code)


class SnapshotValidationError(SnapshotError):
    """EAS-001 — Snapshot validation failed."""

    error_code = "EAS-001"

    def __init__(self, errors: Tuple[str, ...] = ()) -> None:
        summary = "; ".join(errors) if errors else "Snapshot validation failed."
        super(SnapshotError, self).__init__(summary, code=self.error_code)
        self.errors: Tuple[str, ...] = errors


class SnapshotNotFoundError(SnapshotError):
    """EAS-002 — Snapshot with the given ID was not found."""

    error_code = "EAS-002"

    def __init__(self, snapshot_id: str) -> None:
        super(SnapshotError, self).__init__(
            f"Snapshot not found: {snapshot_id!r}",
            code=self.error_code,
        )
        self.snapshot_id: str = snapshot_id


class SnapshotBuildError(SnapshotError):
    """EAS-003 — Snapshot could not be built from the provided sources."""

    error_code = "EAS-003"

    def __init__(self, reason: str) -> None:
        super(SnapshotError, self).__init__(
            f"Snapshot build failed: {reason}",
            code=self.error_code,
        )
        self.reason: str = reason


class SnapshotDuplicateError(SnapshotError):
    """EAS-004 — A snapshot with the same ID already exists."""

    error_code = "EAS-004"

    def __init__(self, snapshot_id: str) -> None:
        super(SnapshotError, self).__init__(
            f"Duplicate snapshot ID: {snapshot_id!r}",
            code=self.error_code,
        )
        self.snapshot_id: str = snapshot_id


class SnapshotStoreError(SnapshotError):
    """EAS-005 — Internal snapshot store error."""

    error_code = "EAS-005"

    def __init__(self, message: str = "Snapshot store error.") -> None:
        super(SnapshotError, self).__init__(message, code=self.error_code)


class SnapshotRegistryError(SnapshotError):
    """EAS-006 — Internal snapshot registry error."""

    error_code = "EAS-006"

    def __init__(self, message: str = "Snapshot registry error.") -> None:
        super(SnapshotError, self).__init__(message, code=self.error_code)


class SnapshotEngineNotRunningError(SnapshotError):
    """EAS-007 — Snapshot engine component is not running."""

    error_code = "EAS-007"

    def __init__(self) -> None:
        super(SnapshotError, self).__init__(
            "Snapshot engine component is not running. Call start() first.",
            code=self.error_code,
        )
