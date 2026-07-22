"""
exceptions.py — iios.portfolio.snapshot
========================================
Exception hierarchy for the Portfolio Snapshot subsystem.

Error-code prefix: PS (Portfolio Snapshot)

C10 Portfolio Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class PortfolioSnapshotError(IIOSError):
    """Base error for the Portfolio Snapshot subsystem."""
    error_code: str = "PS-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class SnapshotBuildError(PortfolioSnapshotError):
    """Raised when building a snapshot fails due to invalid inputs."""
    error_code = "PS-001"

    def __init__(self, message: str, *, portfolio_id: str = "") -> None:
        self.portfolio_id = portfolio_id
        super().__init__(message, code=self.error_code)


class SnapshotNotFoundError(PortfolioSnapshotError):
    """Raised when a snapshot_id lookup returns no result."""
    error_code = "PS-002"

    def __init__(self, snapshot_id: str = "") -> None:
        self.snapshot_id = snapshot_id
        detail = f" (snapshot_id={snapshot_id!r})" if snapshot_id else ""
        super().__init__(f"Snapshot not found{detail}", code=self.error_code)


class SnapshotValidationError(PortfolioSnapshotError):
    """Raised when snapshot validation fails."""
    error_code = "PS-003"

    def __init__(self, message: str, *, failed_checks: tuple = ()) -> None:
        self.failed_checks = failed_checks
        super().__init__(message, code=self.error_code)


class SnapshotDuplicateError(PortfolioSnapshotError):
    """Raised when a snapshot with the same ID already exists in the store."""
    error_code = "PS-004"

    def __init__(self, snapshot_id: str = "") -> None:
        self.snapshot_id = snapshot_id
        super().__init__(
            f"Snapshot already exists (snapshot_id={snapshot_id!r})",
            code=self.error_code,
        )


class SnapshotStoreError(PortfolioSnapshotError):
    """Raised when the snapshot store encounters an error."""
    error_code = "PS-005"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.error_code)


class SnapshotCacheError(PortfolioSnapshotError):
    """Raised when the snapshot cache encounters an error."""
    error_code = "PS-006"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.error_code)


class SnapshotVersionError(PortfolioSnapshotError):
    """Raised when a requested snapshot version does not exist."""
    error_code = "PS-007"

    def __init__(self, message: str, *, version: int = 0) -> None:
        self.version = version
        super().__init__(message, code=self.error_code)


class SnapshotCapacityError(PortfolioSnapshotError):
    """Raised when the store or cache is at capacity."""
    error_code = "PS-008"

    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(
            f"Snapshot capacity exceeded (limit={limit})", code=self.error_code
        )


class SnapshotPublicationError(PortfolioSnapshotError):
    """Raised when publishing a snapshot fails."""
    error_code = "PS-009"

    def __init__(self, message: str, *, portfolio_id: str = "") -> None:
        self.portfolio_id = portfolio_id
        super().__init__(message, code=self.error_code)
