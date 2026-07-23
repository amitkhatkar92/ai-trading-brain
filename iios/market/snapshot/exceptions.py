"""
exceptions.py — iios.market.snapshot
======================================
Exception hierarchy for the Market Snapshot subsystem.

Error-code prefix: MS (Market Snapshot).

C12 Market Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class MarketSnapshotError(IIOSError):
    """Base exception for the Market Snapshot subsystem (MS-000)."""
    error_code: str = "MS-000"

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        super().__init__(message or "Market snapshot error", code=code or self.error_code)


class MarketSnapshotNotFoundError(MarketSnapshotError):
    """Snapshot not found in registry or store (MS-001)."""
    error_code = "MS-001"

    def __init__(self, snapshot_id: str = "") -> None:
        self.snapshot_id = snapshot_id
        super().__init__(
            f"Market snapshot not found: {snapshot_id!r}",
            code=self.error_code,
        )


class MarketSnapshotValidationError(MarketSnapshotError):
    """Snapshot fails structural validation (MS-002)."""
    error_code = "MS-002"

    def __init__(
        self,
        message: str = "",
        *,
        snapshot_id: str = "",
        failed_checks: tuple = (),
    ) -> None:
        self.snapshot_id   = snapshot_id
        self.failed_checks = failed_checks
        detail = f" (snapshot_id={snapshot_id!r})" if snapshot_id else ""
        super().__init__(
            f"Snapshot validation failed{detail}: {message}",
            code=self.error_code,
        )


class MarketSnapshotBuilderError(MarketSnapshotError):
    """Error during snapshot construction (MS-003)."""
    error_code = "MS-003"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or "Snapshot builder error", code=self.error_code)


class MarketSnapshotRegistryError(MarketSnapshotError):
    """Registry operation failed (MS-004)."""
    error_code = "MS-004"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or "Snapshot registry error", code=self.error_code)


class MarketSnapshotStoreError(MarketSnapshotError):
    """Store operation failed (MS-005)."""
    error_code = "MS-005"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or "Snapshot store error", code=self.error_code)


class MarketSnapshotCapacityError(MarketSnapshotError):
    """Registry or store at maximum capacity (MS-006)."""
    error_code = "MS-006"

    def __init__(self, limit: int = 0) -> None:
        self.limit = limit
        super().__init__(
            f"Snapshot capacity exceeded (limit={limit})",
            code=self.error_code,
        )


class MarketSnapshotPublishError(MarketSnapshotError):
    """Snapshot cannot be published in current state (MS-007)."""
    error_code = "MS-007"

    def __init__(self, snapshot_id: str = "", status: str = "") -> None:
        self.snapshot_id = snapshot_id
        super().__init__(
            f"Cannot publish snapshot {snapshot_id!r} in status {status!r}",
            code=self.error_code,
        )


class MarketSnapshotSerializationError(MarketSnapshotError):
    """Snapshot serialization or deserialization failed (MS-008)."""
    error_code = "MS-008"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or "Snapshot serialization error", code=self.error_code)


class MarketSnapshotBundleError(MarketSnapshotError):
    """Bundle operation failed (MS-009)."""
    error_code = "MS-009"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or "Snapshot bundle error", code=self.error_code)
