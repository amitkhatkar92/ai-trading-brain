"""iios/execution/risk/snapshot/constants.py
==================================================
Constants, enumerations, and bounds for the IIOS
Execution Risk Snapshot layer.

C6 Execution Intelligence — Phase 4, Module 5
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

SNAPSHOT_SYSTEM_ID  = "iios:execution:risk:snapshot"
BUILDER_SYSTEM_ID   = "iios:execution:risk:snapshot:builder"
REGISTRY_SYSTEM_ID  = "iios:execution:risk:snapshot:registry"
STORE_SYSTEM_ID     = "iios:execution:risk:snapshot:store"
CACHE_SYSTEM_ID     = "iios:execution:risk:snapshot:cache"
FACTORY_SYSTEM_ID   = "iios:execution:risk:snapshot:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:risk:snapshot:validator"

VERSION          = "1.0.0"
SNAPSHOT_VERSION = "1.0.0"   # schema version baked into every snapshot

# ── Defaults ─────────────────────────────────────────────────────────────────

DEFAULT_MAX_HISTORY    = 10_000
DEFAULT_MAX_CACHE_SIZE = 2_000
DEFAULT_MAX_STORE_SIZE = 100_000
DEFAULT_SEARCH_LIMIT   = 1_000

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_BUILDER  = "iios:execution:risk:snapshot:builder"
ACTOR_REGISTRY = "iios:execution:risk:snapshot:registry"
ACTOR_SYSTEM   = "iios:system"


# ── Snapshot lifecycle status ─────────────────────────────────────────────────

class SnapshotStatus(str, Enum):
    """
    Lifecycle status of a published ExecutionRiskSnapshot.

    CREATED    — built and validated, not yet published
    VALIDATED  — passed full validation suite
    PUBLISHED  — available to downstream systems
    ARCHIVED   — read-only historical record
    INVALID    — failed validation; must not be consumed
    """
    CREATED   = "created"
    VALIDATED = "validated"
    PUBLISHED = "published"
    ARCHIVED  = "archived"
    INVALID   = "invalid"


# ── Snapshot event types ──────────────────────────────────────────────────────

class SnapshotEventType(str, Enum):
    SNAPSHOT_CREATED   = "snapshot_created"
    SNAPSHOT_VALIDATED = "snapshot_validated"
    SNAPSHOT_PUBLISHED = "snapshot_published"
    SNAPSHOT_ARCHIVED  = "snapshot_archived"
    SNAPSHOT_RETRIEVED = "snapshot_retrieved"
    SNAPSHOT_CACHED    = "snapshot_cached"


# ── Derived helpers ───────────────────────────────────────────────────────────

PUBLISHABLE_STATUSES: frozenset = frozenset({
    SnapshotStatus.CREATED, SnapshotStatus.VALIDATED
})

TERMINAL_STATUSES: frozenset = frozenset({
    SnapshotStatus.ARCHIVED, SnapshotStatus.INVALID
})

VALID_LIFECYCLE_STATES_FOR_SNAPSHOT = frozenset({
    "PASSED", "WARNING", "BLOCKED", "OVERRIDDEN", "ARCHIVED",
})
