"""iios/execution/positions/snapshot/constants.py
==================================================
Constants, enumerations, and bounds for the IIOS
Position Snapshot — the canonical published representation
of a trading position.

PositionSnapshot is the ONLY object published outside
the Position Management subsystem.

C6 Execution Intelligence — Phase 3, Module 5
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

SNAPSHOT_SYSTEM_ID  = "iios:execution:positions:snapshot"
STORE_SYSTEM_ID     = "iios:execution:positions:snapshot:store"
REGISTRY_SYSTEM_ID  = "iios:execution:positions:snapshot:registry"
CACHE_SYSTEM_ID     = "iios:execution:positions:snapshot:cache"
BUILDER_SYSTEM_ID   = "iios:execution:positions:snapshot:builder"
FACTORY_SYSTEM_ID   = "iios:execution:positions:snapshot:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:positions:snapshot:validator"

VERSION = "1.0.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_VERSIONS_PER_POSITION = 100   # max snapshot versions kept per position
DEFAULT_MAX_STORE_POSITIONS       = 10_000
DEFAULT_MAX_CACHE_ENTRIES         = 10_000
DEFAULT_MAX_EVENT_HISTORY         = 5_000
DEFAULT_MAX_BUNDLE_SIZE           = 1_000

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_SNAPSHOT = "iios:execution:positions:snapshot"
ACTOR_STORE    = "iios:execution:positions:snapshot:store"
ACTOR_BUILDER  = "iios:execution:positions:snapshot:builder"
ACTOR_SYSTEM   = "iios:system"


# ── Snapshot status ───────────────────────────────────────────────────────────

class SnapshotStatus(str, Enum):
    """
    Lifecycle status of a single ``PositionSnapshot``.

    DRAFT       — built but not yet validated
    VALID       — passed all validation checks
    PUBLISHED   — made available to downstream consumers
    ARCHIVED    — no longer active; kept for historical reference
    INVALID     — failed validation; must not be consumed
    """
    DRAFT     = "DRAFT"
    VALID     = "VALID"
    PUBLISHED = "PUBLISHED"
    ARCHIVED  = "ARCHIVED"
    INVALID   = "INVALID"


# ── Snapshot event types ──────────────────────────────────────────────────────

class SnapshotEventType(str, Enum):
    """Domain events emitted by the Position Snapshot subsystem."""
    SNAPSHOT_CREATED   = "SNAPSHOT_CREATED"
    SNAPSHOT_VALIDATED = "SNAPSHOT_VALIDATED"
    SNAPSHOT_PUBLISHED = "SNAPSHOT_PUBLISHED"
    SNAPSHOT_ARCHIVED  = "SNAPSHOT_ARCHIVED"
    SNAPSHOT_RETRIEVED = "SNAPSHOT_RETRIEVED"
    SNAPSHOT_CACHED    = "SNAPSHOT_CACHED"


# ── Snapshot operation types ──────────────────────────────────────────────────

class SnapshotOperationType(str, Enum):
    """Types of operations performed by the snapshot subsystem."""
    CREATE   = "CREATE"
    VALIDATE = "VALIDATE"
    PUBLISH  = "PUBLISH"
    ARCHIVE  = "ARCHIVE"
    RETRIEVE = "RETRIEVE"
    CACHE    = "CACHE"


# ── Publishable statuses ──────────────────────────────────────────────────────

PUBLISHABLE_STATUSES = frozenset({
    SnapshotStatus.VALID,
    SnapshotStatus.PUBLISHED,
})

ACTIVE_STATUSES = frozenset({
    SnapshotStatus.VALID,
    SnapshotStatus.PUBLISHED,
})

TERMINAL_STATUSES = frozenset({
    SnapshotStatus.ARCHIVED,
    SnapshotStatus.INVALID,
})
