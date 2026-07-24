"""
exceptions.py — iios.integration.snapshot
------------------------------------------
Exception hierarchy for the Integration Snapshot module.

Error code prefix: ISS

C15 Enterprise Integration & Connectivity — Phase 1, Module 5
"""
from __future__ import annotations

from typing import Optional

from iios.common.errors.exceptions import IIOSError


class IntegrationSnapshotError(IIOSError):
    """ISS-000 — Base exception for all Integration Snapshot errors."""
    error_code = "ISS-000"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class SnapshotNotFoundError(IntegrationSnapshotError):
    """ISS-001 — Snapshot not found in registry or store."""
    error_code = "ISS-001"

    def __init__(
        self,
        snapshot_id: str,
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(
            f"Snapshot not found: {snapshot_id!r}",
            code=code,
        )
        self.snapshot_id = snapshot_id


class SnapshotBuildError(IntegrationSnapshotError):
    """ISS-002 — Snapshot construction failed due to missing or invalid fields."""
    error_code = "ISS-002"

    def __init__(
        self,
        message: str = "Snapshot build failed",
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)


class SnapshotValidationError(IntegrationSnapshotError):
    """ISS-003 — Snapshot failed one or more integrity validation checks."""
    error_code = "ISS-003"

    def __init__(
        self,
        message: str = "Snapshot validation failed",
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)


class SnapshotRegistryError(IntegrationSnapshotError):
    """ISS-004 — Registry operation failed (duplicate key, capacity, etc.)."""
    error_code = "ISS-004"

    def __init__(
        self,
        message: str = "Snapshot registry error",
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)


class SnapshotStoreError(IntegrationSnapshotError):
    """ISS-005 — Persistent store operation failed."""
    error_code = "ISS-005"

    def __init__(
        self,
        message: str = "Snapshot store error",
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)


class SnapshotCacheError(IntegrationSnapshotError):
    """ISS-006 — Cache operation failed."""
    error_code = "ISS-006"

    def __init__(
        self,
        message: str = "Snapshot cache error",
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)


class SnapshotExpiredError(IntegrationSnapshotError):
    """ISS-007 — Snapshot has exceeded its TTL and is no longer valid."""
    error_code = "ISS-007"

    def __init__(
        self,
        snapshot_id: str,
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(
            f"Snapshot has expired: {snapshot_id!r}",
            code=code,
        )
        self.snapshot_id = snapshot_id


class SnapshotSerializationError(IntegrationSnapshotError):
    """ISS-008 — Snapshot serialization or deserialization failed."""
    error_code = "ISS-008"

    def __init__(
        self,
        message: str = "Snapshot serialization error",
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)


class SnapshotVersionError(IntegrationSnapshotError):
    """ISS-009 — Snapshot version conflict or inconsistency detected."""
    error_code = "ISS-009"

    def __init__(
        self,
        message: str = "Snapshot version error",
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)


class SnapshotBundleError(IntegrationSnapshotError):
    """ISS-010 — Bundle operation failed (capacity, duplicate, etc.)."""
    error_code = "ISS-010"

    def __init__(
        self,
        message: str = "Snapshot bundle error",
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)
