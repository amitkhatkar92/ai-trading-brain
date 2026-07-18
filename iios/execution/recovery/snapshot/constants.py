"""
iios/execution/recovery/snapshot/constants.py
=============================================
Constants and enumerations for the Execution Recovery Snapshot (C7 M5).

C7 Execution Recovery & Resilience — Phase 1, Module 5
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

SYSTEM_ID   = "iios:execution:recovery:snapshot"
BUILDER_ID  = "iios:execution:recovery:snapshot:builder"
FACTORY_ID  = "iios:execution:recovery:snapshot:factory"
STORE_ID    = "iios:execution:recovery:snapshot:store"
CACHE_ID    = "iios:execution:recovery:snapshot:cache"
REGISTRY_ID = "iios:execution:recovery:snapshot:registry"
HISTORY_ID  = "iios:execution:recovery:snapshot:history"

# ── Versioning ────────────────────────────────────────────────────────────────

VERSION        = "1.0.0"
SCHEMA_VERSION = "1.0"

# ── Default limits ────────────────────────────────────────────────────────────

DEFAULT_MAX_SNAPSHOTS  = 10_000
DEFAULT_MAX_HISTORY    = 2_000
DEFAULT_CACHE_SIZE     = 1_000

# ── Actor identifiers ─────────────────────────────────────────────────────────

ACTOR_BUILDER  = "iios:execution:recovery:snapshot:builder"
ACTOR_SYSTEM   = "iios:system"
ACTOR_OPERATOR = "operator"

# ── Snapshot lifecycle status ─────────────────────────────────────────────────

class SnapshotStatus(str, Enum):
    """Lifecycle status of a published snapshot."""

    CREATED   = "created"
    VALIDATED = "validated"
    PUBLISHED = "published"
    ARCHIVED  = "archived"
    INVALID   = "invalid"


# ── Recovery result ───────────────────────────────────────────────────────────

class RecoveryResult(str, Enum):
    """High-level result of the recovery workflow."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    ABORTED = "aborted"
    UNKNOWN = "unknown"


# ── Verification outcome ──────────────────────────────────────────────────────

class VerificationOutcome(str, Enum):
    """Outcome of post-recovery verification."""

    PASSED  = "passed"
    FAILED  = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"
    UNKNOWN = "unknown"


# ── Snapshot health ───────────────────────────────────────────────────────────

class SnapshotHealth(str, Enum):
    """Assessed health of the recovered subsystem captured in snapshot."""

    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"


# ── Snapshot event types ──────────────────────────────────────────────────────

class SnapshotEventType(str, Enum):
    """All event types emitted by the Snapshot subsystem."""

    SNAPSHOT_CREATED   = "snapshot_created"
    SNAPSHOT_VALIDATED = "snapshot_validated"
    SNAPSHOT_PUBLISHED = "snapshot_published"
    SNAPSHOT_ARCHIVED  = "snapshot_archived"
    SNAPSHOT_RETRIEVED = "snapshot_retrieved"
    SNAPSHOT_CACHED    = "snapshot_cached"


# ── Lifecycle state values (mirrors M1 RecoveryState) ────────────────────────
# Stored as string values in the snapshot — avoids hard M1 import.

LIFECYCLE_TERMINAL_STATES = frozenset({
    "completed", "failed", "aborted", "archived",
})

LIFECYCLE_ACTIVE_STATES = frozenset({
    "created", "initializing", "detecting", "assessing",
    "ready", "recovering", "verifying",
})

LIFECYCLE_VALID_STATES = LIFECYCLE_ACTIVE_STATES | LIFECYCLE_TERMINAL_STATES
