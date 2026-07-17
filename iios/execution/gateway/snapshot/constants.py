"""iios/execution/gateway/snapshot/constants.py
==================================================
Constants, enumerations, and defaults for the
Execution Gateway Snapshot module.

C6 Execution Intelligence — Phase 5, Module 5
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

SNAPSHOT_SYSTEM_ID          = "iios:execution:gateway:snapshot"
SNAPSHOT_BUILDER_SYSTEM_ID  = "iios:execution:gateway:snapshot:builder"
SNAPSHOT_STORE_SYSTEM_ID    = "iios:execution:gateway:snapshot:store"
SNAPSHOT_REGISTRY_SYSTEM_ID = "iios:execution:gateway:snapshot:registry"
SNAPSHOT_CACHE_SYSTEM_ID    = "iios:execution:gateway:snapshot:cache"

VERSION        = "1.0.0"
SCHEMA_VERSION = "1.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_SNAPSHOTS  = 10_000
DEFAULT_MAX_HISTORY    = 5_000
DEFAULT_MAX_CACHE_SIZE = 500
DEFAULT_MAX_BUNDLE_SIZE = 1_000

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_SNAPSHOT_STORE   = "iios:execution:gateway:snapshot:store"
ACTOR_SNAPSHOT_BUILDER = "iios:execution:gateway:snapshot:builder"
ACTOR_SNAPSHOT_SYSTEM  = "iios:system"


# ── Gateway state ─────────────────────────────────────────────────────────────

class GatewayState(str, Enum):
    """High-level processing state of the Execution Gateway."""
    INITIALIZING = "INITIALIZING"
    READY        = "READY"
    PROCESSING   = "PROCESSING"
    ROUTING      = "ROUTING"
    DISPATCHING  = "DISPATCHING"
    MONITORING   = "MONITORING"
    COMPLETED    = "COMPLETED"
    FAILED       = "FAILED"
    RECOVERING   = "RECOVERING"
    UNKNOWN      = "UNKNOWN"


# ── Gateway status ────────────────────────────────────────────────────────────

class GatewayStatus(str, Enum):
    """Operational health status of the gateway."""
    HEALTHY  = "HEALTHY"
    DEGRADED = "DEGRADED"
    ERROR    = "ERROR"
    OFFLINE  = "OFFLINE"
    UNKNOWN  = "UNKNOWN"


# ── Dispatch status ───────────────────────────────────────────────────────────

class DispatchStatus(str, Enum):
    """Status of the order dispatch to the selected broker."""
    PENDING      = "PENDING"
    QUEUED       = "QUEUED"
    DISPATCHING  = "DISPATCHING"
    DISPATCHED   = "DISPATCHED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FAILED       = "FAILED"
    RETRYING     = "RETRYING"
    COMPLETED    = "COMPLETED"
    CANCELLED    = "CANCELLED"


# ── Queue status ──────────────────────────────────────────────────────────────

class QueueStatus(str, Enum):
    """State of the gateway dispatch queue at snapshot time."""
    EMPTY      = "EMPTY"
    QUEUED     = "QUEUED"
    PROCESSING = "PROCESSING"
    FULL       = "FULL"
    BLOCKED    = "BLOCKED"
    FLUSHING   = "FLUSHING"


# ── Snapshot event type ───────────────────────────────────────────────────────

class SnapshotEventType(str, Enum):
    """Event types emitted by the Snapshot module."""
    SNAPSHOT_CREATED   = "SNAPSHOT_CREATED"
    SNAPSHOT_VALIDATED = "SNAPSHOT_VALIDATED"
    SNAPSHOT_PUBLISHED = "SNAPSHOT_PUBLISHED"
    SNAPSHOT_ARCHIVED  = "SNAPSHOT_ARCHIVED"
    SNAPSHOT_RETRIEVED = "SNAPSHOT_RETRIEVED"
    SNAPSHOT_CACHED    = "SNAPSHOT_CACHED"


# ── Convenience sets ──────────────────────────────────────────────────────────

TERMINAL_GATEWAY_STATES: frozenset[GatewayState] = frozenset({
    GatewayState.COMPLETED,
    GatewayState.FAILED,
})

ACTIVE_GATEWAY_STATES: frozenset[GatewayState] = frozenset({
    GatewayState.INITIALIZING,
    GatewayState.READY,
    GatewayState.PROCESSING,
    GatewayState.ROUTING,
    GatewayState.DISPATCHING,
    GatewayState.MONITORING,
    GatewayState.RECOVERING,
})

SUCCESSFUL_DISPATCH_STATUSES: frozenset[DispatchStatus] = frozenset({
    DispatchStatus.DISPATCHED,
    DispatchStatus.ACKNOWLEDGED,
    DispatchStatus.COMPLETED,
})
