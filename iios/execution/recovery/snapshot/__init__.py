"""
iios/execution/recovery/snapshot/__init__.py
============================================
Public surface of the Execution Recovery Snapshot (C7 M5).

Primary published type: ExecutionRecoverySnapshot

This is the ONLY object exposed outside the Recovery subsystem.
All downstream consumers MUST import from this package.

C7 Execution Recovery & Resilience — Phase 1, Module 5
"""
from __future__ import annotations

# ── Constants ─────────────────────────────────────────────────────────────────
from .constants import (
    ACTOR_BUILDER,
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    BUILDER_ID,
    CACHE_ID,
    DEFAULT_CACHE_SIZE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SNAPSHOTS,
    FACTORY_ID,
    HISTORY_ID,
    LIFECYCLE_TERMINAL_STATES,
    LIFECYCLE_VALID_STATES,
    REGISTRY_ID,
    SCHEMA_VERSION,
    STORE_ID,
    SYSTEM_ID,
    VERSION,
    RecoveryResult,
    SnapshotEventType,
    SnapshotHealth,
    SnapshotStatus,
    VerificationOutcome,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    RecoverySnapshotError,
    SnapshotBuildError,
    SnapshotCacheError,
    SnapshotDuplicateError,
    SnapshotNotFoundError,
    SnapshotNotRunningError,
    SnapshotRegistryError,
    SnapshotStoreError,
    SnapshotValidationError,
    SnapshotVersionError,
)

# ── PRIMARY published type ─────────────────────────────────────────────────────
from .execution_recovery_snapshot import (
    ExecutionRecoverySnapshot,
    make_execution_recovery_snapshot,
)

# ── Supporting types ──────────────────────────────────────────────────────────
from .recovery_snapshot_metadata import AuditMetadata, make_audit_metadata
from .recovery_snapshot_validation import (
    RecoverySnapshotValidator,
    SnapshotValidationResult,
)
from .recovery_snapshot_events import (
    SnapshotEvent,
    make_snapshot_archived,
    make_snapshot_cached,
    make_snapshot_created,
    make_snapshot_published,
    make_snapshot_retrieved,
    make_snapshot_validated,
)
from .recovery_snapshot_statistics import RecoverySnapshotStatistics
from .recovery_snapshot_history import RecoverySnapshotHistory
from .recovery_snapshot_bundle import RecoverySnapshotBundle, make_snapshot_bundle

# ── Components ────────────────────────────────────────────────────────────────
from .recovery_snapshot_factory import RecoverySnapshotFactory
from .recovery_snapshot_registry import RecoverySnapshotRegistry
from .recovery_snapshot_cache import RecoverySnapshotCache
from .recovery_snapshot_store import RecoverySnapshotStore
from .recovery_snapshot_builder import RecoverySnapshotBuilder

__all__ = [
    # Constants
    "SYSTEM_ID", "BUILDER_ID", "FACTORY_ID", "STORE_ID",
    "CACHE_ID", "REGISTRY_ID", "HISTORY_ID",
    "VERSION", "SCHEMA_VERSION",
    "DEFAULT_MAX_SNAPSHOTS", "DEFAULT_MAX_HISTORY", "DEFAULT_CACHE_SIZE",
    "ACTOR_BUILDER", "ACTOR_SYSTEM", "ACTOR_OPERATOR",
    "LIFECYCLE_TERMINAL_STATES", "LIFECYCLE_VALID_STATES",
    # Enums
    "SnapshotStatus", "RecoveryResult", "VerificationOutcome",
    "SnapshotHealth", "SnapshotEventType",
    # Exceptions
    "RecoverySnapshotError", "SnapshotNotRunningError", "SnapshotValidationError",
    "SnapshotBuildError", "SnapshotNotFoundError", "SnapshotDuplicateError",
    "SnapshotStoreError", "SnapshotCacheError", "SnapshotRegistryError",
    "SnapshotVersionError",
    # PRIMARY type
    "ExecutionRecoverySnapshot", "make_execution_recovery_snapshot",
    # Supporting types
    "AuditMetadata", "make_audit_metadata",
    "SnapshotValidationResult", "RecoverySnapshotValidator",
    "SnapshotEvent",
    "make_snapshot_created", "make_snapshot_validated", "make_snapshot_published",
    "make_snapshot_archived", "make_snapshot_retrieved", "make_snapshot_cached",
    "RecoverySnapshotStatistics",
    "RecoverySnapshotHistory",
    "RecoverySnapshotBundle", "make_snapshot_bundle",
    # Components
    "RecoverySnapshotFactory",
    "RecoverySnapshotRegistry",
    "RecoverySnapshotCache",
    "RecoverySnapshotStore",
    "RecoverySnapshotBuilder",
]
