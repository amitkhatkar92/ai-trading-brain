"""iios/execution/gateway/snapshot/__init__.py
==================================================
Public API for the IIOS Execution Gateway Snapshot module.

ExecutionGatewaySnapshot is the ONLY published representation
of the Execution Gateway subsystem.

Every downstream subsystem MUST consume ExecutionGatewaySnapshot
instead of internal Gateway Engine, Routing Framework, or
Broker Abstraction objects.

C6 Execution Intelligence — Phase 5, Module 5
"""
from __future__ import annotations

# ── Constants / enumerations ──────────────────────────────────────────────────
from .constants import (
    ACTOR_SNAPSHOT_BUILDER,
    ACTOR_SNAPSHOT_STORE,
    ACTOR_SNAPSHOT_SYSTEM,
    DEFAULT_MAX_BUNDLE_SIZE,
    DEFAULT_MAX_CACHE_SIZE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SNAPSHOTS,
    SCHEMA_VERSION,
    SNAPSHOT_BUILDER_SYSTEM_ID,
    SNAPSHOT_CACHE_SYSTEM_ID,
    SNAPSHOT_REGISTRY_SYSTEM_ID,
    SNAPSHOT_STORE_SYSTEM_ID,
    SNAPSHOT_SYSTEM_ID,
    SUCCESSFUL_DISPATCH_STATUSES,
    TERMINAL_GATEWAY_STATES,
    ACTIVE_GATEWAY_STATES,
    DispatchStatus,
    GatewayState,
    GatewayStatus,
    QueueStatus,
    SnapshotEventType,
    VERSION,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    DuplicateSnapshotError,
    GatewaySnapshotError,
    SnapshotBuildError,
    SnapshotNotFoundError,
    SnapshotStoreCapacityError,
    SnapshotStoreNotRunningError,
    SnapshotValidationError,
    SnapshotVersionError,
)

# ── Core snapshot ─────────────────────────────────────────────────────────────
from .execution_gateway_snapshot import ExecutionGatewaySnapshot

# ── Metadata ──────────────────────────────────────────────────────────────────
from .gateway_snapshot_metadata import (
    GatewaySnapshotMetadata,
    make_audit_metadata,
)

# ── Bundle ────────────────────────────────────────────────────────────────────
from .gateway_snapshot_bundle import (
    GatewaySnapshotBundle,
    make_bundle_from_snapshots,
)

# ── Builder ───────────────────────────────────────────────────────────────────
from .gateway_snapshot_builder import GatewaySnapshotBuilder

# ── Validation ────────────────────────────────────────────────────────────────
from .gateway_snapshot_validation import (
    GatewaySnapshotValidationResult,
    GatewaySnapshotValidator,
)

# ── Statistics ────────────────────────────────────────────────────────────────
from .gateway_snapshot_statistics import GatewaySnapshotStatistics

# ── Events ────────────────────────────────────────────────────────────────────
from .gateway_snapshot_events import (
    SnapshotEvent,
    make_snapshot_archived_event,
    make_snapshot_cached_event,
    make_snapshot_created_event,
    make_snapshot_published_event,
    make_snapshot_retrieved_event,
    make_snapshot_validated_event,
)

# ── History / cache / registry ────────────────────────────────────────────────
from .gateway_snapshot_history  import GatewaySnapshotHistory
from .gateway_snapshot_cache    import GatewaySnapshotCache
from .gateway_snapshot_registry import GatewaySnapshotRegistry

# ── Store (primary consumer API) ──────────────────────────────────────────────
from .gateway_snapshot_store   import GatewaySnapshotStore

# ── Factory ───────────────────────────────────────────────────────────────────
from .gateway_snapshot_factory import GatewaySnapshotFactory


__all__ = [
    # Constants
    "SNAPSHOT_SYSTEM_ID",
    "SNAPSHOT_BUILDER_SYSTEM_ID",
    "SNAPSHOT_STORE_SYSTEM_ID",
    "SNAPSHOT_REGISTRY_SYSTEM_ID",
    "SNAPSHOT_CACHE_SYSTEM_ID",
    "ACTOR_SNAPSHOT_BUILDER",
    "ACTOR_SNAPSHOT_STORE",
    "ACTOR_SNAPSHOT_SYSTEM",
    "DEFAULT_MAX_SNAPSHOTS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_CACHE_SIZE",
    "DEFAULT_MAX_BUNDLE_SIZE",
    "SCHEMA_VERSION",
    "VERSION",
    "SUCCESSFUL_DISPATCH_STATUSES",
    "TERMINAL_GATEWAY_STATES",
    "ACTIVE_GATEWAY_STATES",
    # Enums
    "DispatchStatus",
    "GatewayState",
    "GatewayStatus",
    "QueueStatus",
    "SnapshotEventType",
    # Exceptions
    "DuplicateSnapshotError",
    "GatewaySnapshotError",
    "SnapshotBuildError",
    "SnapshotNotFoundError",
    "SnapshotStoreCapacityError",
    "SnapshotStoreNotRunningError",
    "SnapshotValidationError",
    "SnapshotVersionError",
    # Core snapshot — THE published representation
    "ExecutionGatewaySnapshot",
    # Metadata / bundle
    "GatewaySnapshotMetadata",
    "make_audit_metadata",
    "GatewaySnapshotBundle",
    "make_bundle_from_snapshots",
    # Builder
    "GatewaySnapshotBuilder",
    # Validation
    "GatewaySnapshotValidationResult",
    "GatewaySnapshotValidator",
    # Statistics
    "GatewaySnapshotStatistics",
    # Events
    "SnapshotEvent",
    "make_snapshot_archived_event",
    "make_snapshot_cached_event",
    "make_snapshot_created_event",
    "make_snapshot_published_event",
    "make_snapshot_retrieved_event",
    "make_snapshot_validated_event",
    # Storage
    "GatewaySnapshotHistory",
    "GatewaySnapshotCache",
    "GatewaySnapshotRegistry",
    "GatewaySnapshotStore",
    # Factory
    "GatewaySnapshotFactory",
]
