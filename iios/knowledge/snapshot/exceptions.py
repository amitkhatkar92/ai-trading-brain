"""
exceptions.py — iios.knowledge.snapshot
-----------------------------------------
Typed exception hierarchy for the Knowledge Snapshot system.

Error code prefix: KSN (Knowledge Snapshot)

C14 Enterprise Knowledge Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class KnowledgeSnapshotError(IIOSError):
    """Base for all Knowledge Snapshot errors."""
    error_code = "KSN-000"

    def __init__(self, message: str = "", code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class SnapshotBuildError(KnowledgeSnapshotError):
    """Raised when snapshot construction fails."""
    error_code = "KSN-001"


class SnapshotValidationError(KnowledgeSnapshotError):
    """Raised when snapshot validation fails."""
    error_code = "KSN-002"

    def __init__(
        self,
        message:      str           = "",
        failed_checks: list[str]   = None,
        code:          str | None  = None,
    ) -> None:
        super().__init__(message, code=code)
        self.failed_checks = list(failed_checks or [])


class SnapshotNotFoundError(KnowledgeSnapshotError):
    """Raised when a requested snapshot does not exist."""
    error_code = "KSN-003"

    def __init__(
        self,
        snapshot_id: str = "",
        code:        str | None = None,
    ) -> None:
        msg = f"Snapshot not found: {snapshot_id!r}" if snapshot_id else "Snapshot not found"
        super().__init__(msg, code=code)
        self.snapshot_id = snapshot_id


class SnapshotVersionError(KnowledgeSnapshotError):
    """Raised when snapshot versioning is inconsistent."""
    error_code = "KSN-004"


class SnapshotSerializationError(KnowledgeSnapshotError):
    """Raised when snapshot serialization or deserialization fails."""
    error_code = "KSN-005"


class SnapshotStoreError(KnowledgeSnapshotError):
    """Raised when snapshot store operations fail."""
    error_code = "KSN-006"


class SnapshotCapacityError(KnowledgeSnapshotError):
    """Raised when snapshot store or cache capacity is exceeded."""
    error_code = "KSN-007"

    def __init__(
        self,
        message: str      = "",
        limit:   int      = 0,
        code:    str | None = None,
    ) -> None:
        super().__init__(message or f"Capacity limit reached: {limit}", code=code)
        self.limit = limit


class SnapshotIntegrityError(KnowledgeSnapshotError):
    """Raised when snapshot integrity check fails (e.g., hash mismatch)."""
    error_code = "KSN-008"
