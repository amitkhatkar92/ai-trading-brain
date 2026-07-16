"""iios/execution/positions/snapshot/__init__.py
==================================================
Public API for the IIOS Position Snapshot module.

PositionSnapshot is the ONLY object published outside
the Position Management subsystem.

C6 Execution Intelligence — Phase 3, Module 5
"""
from __future__ import annotations

# ── Constants ─────────────────────────────────────────────────────────────────
from .constants import (
    ACTIVE_STATUSES,
    ACTOR_BUILDER,
    ACTOR_SNAPSHOT,
    ACTOR_STORE,
    ACTOR_SYSTEM,
    BUILDER_SYSTEM_ID,
    CACHE_SYSTEM_ID,
    DEFAULT_MAX_CACHE_ENTRIES,
    DEFAULT_MAX_EVENT_HISTORY,
    DEFAULT_MAX_STORE_POSITIONS,
    DEFAULT_MAX_VERSIONS_PER_POSITION,
    FACTORY_SYSTEM_ID,
    PUBLISHABLE_STATUSES,
    REGISTRY_SYSTEM_ID,
    SNAPSHOT_SYSTEM_ID,
    STORE_SYSTEM_ID,
    TERMINAL_STATUSES,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    SnapshotEventType,
    SnapshotOperationType,
    SnapshotStatus,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    DuplicateSnapshotError,
    PositionSnapshotError,
    PositionSnapshotNotRunningError,
    SnapshotBuildError,
    SnapshotCacheError,
    SnapshotCapacityError,
    SnapshotNotFoundError,
    SnapshotStoreError,
    SnapshotValidationError,
    SnapshotVersionError,
)

# ── Core value object ─────────────────────────────────────────────────────────
from .position_snapshot import PositionSnapshot

# ── Metadata ──────────────────────────────────────────────────────────────────
from .position_snapshot_metadata import SnapshotAuditMetadata, make_audit_metadata

# ── Validation ────────────────────────────────────────────────────────────────
from .position_snapshot_validation import SnapshotValidationResult, SnapshotValidator

# ── Events ────────────────────────────────────────────────────────────────────
from .position_snapshot_events import (
    SnapshotEvent,
    make_snapshot_archived_event,
    make_snapshot_cached_event,
    make_snapshot_created_event,
    make_snapshot_published_event,
    make_snapshot_retrieved_event,
    make_snapshot_validated_event,
)

# ── History ───────────────────────────────────────────────────────────────────
from .position_snapshot_history import SnapshotEventHistory, SnapshotVersionHistory

# ── Statistics ────────────────────────────────────────────────────────────────
from .position_snapshot_statistics import SnapshotStatistics

# ── Bundle ────────────────────────────────────────────────────────────────────
from .position_snapshot_bundle import SnapshotBundle, make_snapshot_bundle

# ── Builder ───────────────────────────────────────────────────────────────────
from .position_snapshot_builder import PositionSnapshotBuilder

# ── Factory ───────────────────────────────────────────────────────────────────
from .position_snapshot_factory import PositionSnapshotFactory

# ── Infrastructure ────────────────────────────────────────────────────────────
from .position_snapshot_registry import PositionSnapshotRegistry
from .position_snapshot_cache import PositionSnapshotCache

# ── Primary facade ────────────────────────────────────────────────────────────
from .position_snapshot_store import PositionSnapshotStore

__all__ = [
    # ── system IDs
    "SNAPSHOT_SYSTEM_ID",
    "STORE_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "CACHE_SYSTEM_ID",
    "BUILDER_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID",
    # ── actors
    "ACTOR_SNAPSHOT",
    "ACTOR_STORE",
    "ACTOR_BUILDER",
    "ACTOR_SYSTEM",
    # ── version
    "VERSION",
    # ── defaults
    "DEFAULT_MAX_STORE_POSITIONS",
    "DEFAULT_MAX_CACHE_ENTRIES",
    "DEFAULT_MAX_EVENT_HISTORY",
    "DEFAULT_MAX_VERSIONS_PER_POSITION",
    # ── status sets
    "PUBLISHABLE_STATUSES",
    "ACTIVE_STATUSES",
    "TERMINAL_STATUSES",
    # ── enums
    "SnapshotStatus",
    "SnapshotEventType",
    "SnapshotOperationType",
    # ── exceptions
    "PositionSnapshotError",
    "PositionSnapshotNotRunningError",
    "SnapshotNotFoundError",
    "DuplicateSnapshotError",
    "SnapshotValidationError",
    "SnapshotBuildError",
    "SnapshotCapacityError",
    "SnapshotStoreError",
    "SnapshotCacheError",
    "SnapshotVersionError",
    # ── core value object
    "PositionSnapshot",
    # ── metadata
    "SnapshotAuditMetadata",
    "make_audit_metadata",
    # ── validation
    "SnapshotValidationResult",
    "SnapshotValidator",
    # ── events
    "SnapshotEvent",
    "make_snapshot_created_event",
    "make_snapshot_validated_event",
    "make_snapshot_published_event",
    "make_snapshot_archived_event",
    "make_snapshot_retrieved_event",
    "make_snapshot_cached_event",
    # ── history
    "SnapshotEventHistory",
    "SnapshotVersionHistory",
    # ── statistics
    "SnapshotStatistics",
    # ── bundle
    "SnapshotBundle",
    "make_snapshot_bundle",
    # ── builder
    "PositionSnapshotBuilder",
    # ── factory
    "PositionSnapshotFactory",
    # ── infrastructure
    "PositionSnapshotRegistry",
    "PositionSnapshotCache",
    # ── primary facade
    "PositionSnapshotStore",
]
