"""iios/investment/strategy/migration/migration_status.py
Status enumerations for the Strategy Migration Framework.
"""
from __future__ import annotations

from enum import Enum


class MigrationStatus(str, Enum):
    """Full lifecycle state of a single strategy migration."""
    NOT_STARTED      = "not_started"
    DISCOVERY        = "discovery"
    VALIDATION       = "validation"
    PREPARATION      = "preparation"
    MIGRATING        = "migrating"
    VERIFICATION     = "verification"
    APPROVAL_PENDING = "approval_pending"
    COMPLETED        = "completed"
    FAILED           = "failed"
    ROLLED_BACK      = "rolled_back"
    ARCHIVED         = "archived"

    @property
    def is_terminal(self) -> bool:
        return self in (
            MigrationStatus.COMPLETED,
            MigrationStatus.FAILED,
            MigrationStatus.ROLLED_BACK,
            MigrationStatus.ARCHIVED,
        )

    @property
    def is_active(self) -> bool:
        return self in (
            MigrationStatus.DISCOVERY,
            MigrationStatus.VALIDATION,
            MigrationStatus.PREPARATION,
            MigrationStatus.MIGRATING,
            MigrationStatus.VERIFICATION,
            MigrationStatus.APPROVAL_PENDING,
        )

    @property
    def can_rollback(self) -> bool:
        return self in (
            MigrationStatus.MIGRATING,
            MigrationStatus.VERIFICATION,
            MigrationStatus.APPROVAL_PENDING,
            MigrationStatus.COMPLETED,
            MigrationStatus.FAILED,
        )


class MigrationPhase(str, Enum):
    """Ordered phases in a migration workflow."""
    DISCOVERY   = "discovery"
    VALIDATION  = "validation"
    PREPARATION = "preparation"
    MIGRATION   = "migration"
    VERIFICATION = "verification"
    APPROVAL    = "approval"
    ROLLBACK    = "rollback"
    ARCHIVE     = "archive"

    @property
    def order(self) -> int:
        _ORDER = {
            "discovery":    1,
            "validation":   2,
            "preparation":  3,
            "migration":    4,
            "verification": 5,
            "approval":     6,
            "rollback":     7,
            "archive":      8,
        }
        return _ORDER[self.value]


class CompatibilityLevel(str, Enum):
    """How compatible a legacy strategy is with the IIOS framework."""
    FULL              = "full"              # direct registration
    PARTIAL           = "partial"           # minor gaps filled by adapter
    REQUIRES_ADAPTER  = "requires_adapter"  # needs full adapter wrapping
    INCOMPATIBLE      = "incompatible"      # cannot migrate without redesign
    UNKNOWN           = "unknown"

    @property
    def is_migratable(self) -> bool:
        return self in (CompatibilityLevel.FULL,
                        CompatibilityLevel.PARTIAL,
                        CompatibilityLevel.REQUIRES_ADAPTER)


class MigrationRisk(str, Enum):
    """Risk level of a migration operation."""
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class RollbackReason(str, Enum):
    """Why a rollback was initiated."""
    VALIDATION_FAILURE   = "validation_failure"
    BEHAVIOR_DIVERGENCE  = "behavior_divergence"
    MANUAL_REQUEST       = "manual_request"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    DEPENDENCY_MISSING   = "dependency_missing"
    TIMEOUT              = "timeout"
    UNKNOWN              = "unknown"
