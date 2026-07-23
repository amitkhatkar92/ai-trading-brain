"""
exceptions.py — iios.risk.snapshot
======================================
Error hierarchy for the Risk Snapshot Framework.

Error codes use the RS- prefix (Risk Snapshot):
  RS-000  Base
  RS-001  Not found
  RS-002  Builder error
  RS-003  Validation error
  RS-004  Integrity error
  RS-005  Registry error
  RS-006  Store error
  RS-007  Cache error
  RS-008  Capacity exceeded
  RS-009  Serialization error

C11 Risk Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class RiskSnapshotError(IIOSError):
    """Base exception for all Risk Snapshot errors."""
    error_code: str = "RS-000"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class RiskSnapshotNotFoundError(RiskSnapshotError):
    """Raised when a requested snapshot cannot be located."""
    error_code = "RS-001"


class RiskSnapshotBuilderError(RiskSnapshotError):
    """Raised when snapshot construction fails."""
    error_code = "RS-002"


class RiskSnapshotValidationError(RiskSnapshotError):
    """Raised when snapshot validation fails."""
    error_code = "RS-003"


class RiskSnapshotIntegrityError(RiskSnapshotError):
    """Raised when snapshot integrity check fails."""
    error_code = "RS-004"


class RiskSnapshotRegistryError(RiskSnapshotError):
    """Raised on registry operation failures."""
    error_code = "RS-005"


class RiskSnapshotStoreError(RiskSnapshotError):
    """Raised on persistent store operation failures."""
    error_code = "RS-006"


class RiskSnapshotCacheError(RiskSnapshotError):
    """Raised on cache operation failures."""
    error_code = "RS-007"


class RiskSnapshotCapacityError(RiskSnapshotError):
    """Raised when snapshot storage capacity is exceeded."""
    error_code = "RS-008"


class RiskSnapshotSerializationError(RiskSnapshotError):
    """Raised when snapshot serialization or deserialization fails."""
    error_code = "RS-009"
