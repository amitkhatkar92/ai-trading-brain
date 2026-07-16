"""iios/execution/snapshot/__init__.py
==================================================
Public API for the IIOS Execution Snapshot package.

C6 Execution Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

# ── Constants ─────────────────────────────────────────────────────────────────
from iios.execution.snapshot.constants import (
    SNAPSHOT_SYSTEM_ID,
    BUILDER_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    VALIDATOR_SYSTEM_ID,
    STORE_SYSTEM_ID,
    CACHE_SYSTEM_ID,
    VERSION,
    ACTOR_SYSTEM,
    ACTOR_BUILDER,
    ACTOR_FACTORY,
    ACTOR_REGISTRY,
    ACTOR_STORE,
    ACTOR_USER,
    DEFAULT_MAX_SNAPSHOTS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_BUNDLE_SIZE,
    DEFAULT_CACHE_SIZE,
    SnapshotLifecycle,
    SnapshotTrigger,
    SnapshotFormat,
    SnapshotValidationCode,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from iios.execution.snapshot.exceptions import (
    ExecutionSnapshotError,
    SnapshotBuildError,
    SnapshotValidationError,
    SnapshotNotFoundError,
    DuplicateSnapshotError,
    SnapshotCapacityError,
    SnapshotStoreNotRunning,
    SnapshotIncompleteError,
    SnapshotInconsistencyError,
    SnapshotSerializationError,
    SnapshotHistoryError,
    SnapshotVersionError,
)

# ── Core snapshot ─────────────────────────────────────────────────────────────
from iios.execution.snapshot.execution_snapshot import ExecutionSnapshot

# ── Metadata ──────────────────────────────────────────────────────────────────
from iios.execution.snapshot.execution_snapshot_metadata import SnapshotAuditMetadata

# ── Bundle ────────────────────────────────────────────────────────────────────
from iios.execution.snapshot.execution_snapshot_bundle import ExecutionSnapshotBundle

# ── Events ────────────────────────────────────────────────────────────────────
from iios.execution.snapshot.execution_snapshot_events import (
    SnapshotEventType,
    SnapshotEvent,
    make_snapshot_event,
)

# ── Validation ────────────────────────────────────────────────────────────────
from iios.execution.snapshot.execution_snapshot_validator import (
    ExecutionSnapshotValidator,
    SnapshotValidationResult,
)

# ── Builder ───────────────────────────────────────────────────────────────────
from iios.execution.snapshot.execution_snapshot_builder import ExecutionSnapshotBuilder

# ── Factory ───────────────────────────────────────────────────────────────────
from iios.execution.snapshot.execution_snapshot_factory import ExecutionSnapshotFactory

# ── Registry ─────────────────────────────────────────────────────────────────
from iios.execution.snapshot.execution_snapshot_registry import (
    SnapshotRecord,
    ExecutionSnapshotRegistry,
)

# ── History ───────────────────────────────────────────────────────────────────
from iios.execution.snapshot.execution_snapshot_history import (
    SnapshotRevision,
    ExecutionSnapshotHistory,
    make_snapshot_revision,
)

# ── Statistics ────────────────────────────────────────────────────────────────
from iios.execution.snapshot.execution_snapshot_statistics import (
    SnapshotBuildStats,
    ExecutionSnapshotStats,
)

# ── Store (primary entry point) ───────────────────────────────────────────────
from iios.execution.snapshot.execution_snapshot_store import ExecutionSnapshotStore

# ── Cache ─────────────────────────────────────────────────────────────────────
from iios.execution.snapshot.execution_snapshot_cache import ExecutionSnapshotCache

__all__ = [
    # System IDs
    "SNAPSHOT_SYSTEM_ID",
    "BUILDER_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID",
    "STORE_SYSTEM_ID",
    "CACHE_SYSTEM_ID",
    "VERSION",
    # Actors
    "ACTOR_SYSTEM",
    "ACTOR_BUILDER",
    "ACTOR_FACTORY",
    "ACTOR_REGISTRY",
    "ACTOR_STORE",
    "ACTOR_USER",
    # Capacity
    "DEFAULT_MAX_SNAPSHOTS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_BUNDLE_SIZE",
    "DEFAULT_CACHE_SIZE",
    # Enums
    "SnapshotLifecycle",
    "SnapshotTrigger",
    "SnapshotFormat",
    "SnapshotValidationCode",
    # Exceptions
    "ExecutionSnapshotError",
    "SnapshotBuildError",
    "SnapshotValidationError",
    "SnapshotNotFoundError",
    "DuplicateSnapshotError",
    "SnapshotCapacityError",
    "SnapshotStoreNotRunning",
    "SnapshotIncompleteError",
    "SnapshotInconsistencyError",
    "SnapshotSerializationError",
    "SnapshotHistoryError",
    "SnapshotVersionError",
    # Core
    "ExecutionSnapshot",
    # Metadata
    "SnapshotAuditMetadata",
    # Bundle
    "ExecutionSnapshotBundle",
    # Events
    "SnapshotEventType",
    "SnapshotEvent",
    "make_snapshot_event",
    # Validation
    "ExecutionSnapshotValidator",
    "SnapshotValidationResult",
    # Builder
    "ExecutionSnapshotBuilder",
    # Factory
    "ExecutionSnapshotFactory",
    # Registry
    "SnapshotRecord",
    "ExecutionSnapshotRegistry",
    # History
    "SnapshotRevision",
    "ExecutionSnapshotHistory",
    "make_snapshot_revision",
    # Statistics
    "SnapshotBuildStats",
    "ExecutionSnapshotStats",
    # Store
    "ExecutionSnapshotStore",
    # Cache
    "ExecutionSnapshotCache",
]
