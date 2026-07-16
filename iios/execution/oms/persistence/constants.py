"""iios/execution/oms/persistence/constants.py
==================================================
Constants, enumerations, and bounds for the IIOS
Order Persistence abstraction layer.

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

PERSISTENCE_SYSTEM_ID = "iios:execution:oms:persistence"
MANAGER_SYSTEM_ID     = "iios:execution:oms:persistence:manager"
REGISTRY_SYSTEM_ID    = "iios:execution:oms:persistence:registry"
FACTORY_SYSTEM_ID     = "iios:execution:oms:persistence:factory"
VALIDATOR_SYSTEM_ID   = "iios:execution:oms:persistence:validator"

VERSION        = "1.0.0"
SCHEMA_VERSION = "1.0.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_REPOSITORIES = 64
DEFAULT_MAX_HISTORY      = 5_000
DEFAULT_SAVE_TTL_SEC     = 30.0
DEFAULT_SEARCH_LIMIT     = 1_000

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_SYSTEM      = "iios:system"
ACTOR_PERSISTENCE = "iios:execution:oms:persistence"
ACTOR_MANAGER     = "iios:execution:oms:persistence:manager"


# ── Record domain types ───────────────────────────────────────────────────────

class RecordType(str, Enum):
    """Type of domain object being persisted."""
    ORDER      = "ORDER"
    LIFECYCLE  = "LIFECYCLE"
    QUEUE      = "QUEUE"
    ROUTING    = "ROUTING"
    EXECUTION  = "EXECUTION"
    SNAPSHOT   = "SNAPSHOT"
    AUDIT      = "AUDIT"


class RecordStatus(str, Enum):
    """Lifecycle status of a persisted record."""
    ACTIVE     = "ACTIVE"
    ARCHIVED   = "ARCHIVED"
    DELETED    = "DELETED"
    RECOVERING = "RECOVERING"
    CORRUPTED  = "CORRUPTED"


TERMINAL_RECORD_STATUSES = frozenset({
    RecordStatus.DELETED,
    RecordStatus.CORRUPTED,
})


class OperationType(str, Enum):
    """CRUD and recovery operations."""
    SAVE    = "SAVE"
    UPDATE  = "UPDATE"
    DELETE  = "DELETE"
    ARCHIVE = "ARCHIVE"
    RESTORE = "RESTORE"
    FIND    = "FIND"
    SEARCH  = "SEARCH"


class RepositoryHealth(str, Enum):
    HEALTHY     = "HEALTHY"
    DEGRADED    = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN     = "UNKNOWN"


class VersionType(str, Enum):
    """Type of version entry in version history."""
    RECORD    = "RECORD"
    SCHEMA    = "SCHEMA"
    SNAPSHOT  = "SNAPSHOT"
    MIGRATION = "MIGRATION"
    AUDIT     = "AUDIT"


class RecoveryState(str, Enum):
    PENDING     = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED   = "COMPLETED"
    FAILED      = "FAILED"
    PARTIAL     = "PARTIAL"


class PersistenceEventType(str, Enum):
    RECORD_SAVED          = "RECORD_SAVED"
    RECORD_UPDATED        = "RECORD_UPDATED"
    RECORD_ARCHIVED       = "RECORD_ARCHIVED"
    RECORD_RESTORED       = "RECORD_RESTORED"
    RECOVERY_STARTED      = "RECOVERY_STARTED"
    RECOVERY_COMPLETED    = "RECOVERY_COMPLETED"
    REPOSITORY_VALIDATED  = "REPOSITORY_VALIDATED"


class PersistenceValidationCode(str, Enum):
    MISSING_RECORD_ID        = "MISSING_RECORD_ID"
    DUPLICATE_RECORD         = "DUPLICATE_RECORD"
    RECORD_NOT_FOUND         = "RECORD_NOT_FOUND"
    VERSION_CONFLICT         = "VERSION_CONFLICT"
    SCHEMA_MISMATCH          = "SCHEMA_MISMATCH"
    RECOVERY_FAILED          = "RECOVERY_FAILED"
    CONTRACT_VIOLATION       = "CONTRACT_VIOLATION"
    REPOSITORY_UNAVAILABLE   = "REPOSITORY_UNAVAILABLE"
    INVALID_OPERATION        = "INVALID_OPERATION"
    SNAPSHOT_CORRUPTED       = "SNAPSHOT_CORRUPTED"
    INVALID_RECORD_TYPE      = "INVALID_RECORD_TYPE"
    REPOSITORY_NOT_FOUND     = "REPOSITORY_NOT_FOUND"
