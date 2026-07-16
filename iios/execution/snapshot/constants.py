"""iios/execution/snapshot/constants.py
==================================================
Constants, enumerations, and bounds for the
IIOS Execution Snapshot package.

C6 Execution Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

SNAPSHOT_SYSTEM_ID   = "iios:execution:snapshot"
BUILDER_SYSTEM_ID    = "iios:execution:snapshot:builder"
FACTORY_SYSTEM_ID    = "iios:execution:snapshot:factory"
REGISTRY_SYSTEM_ID   = "iios:execution:snapshot:registry"
VALIDATOR_SYSTEM_ID  = "iios:execution:snapshot:validator"
STORE_SYSTEM_ID      = "iios:execution:snapshot:store"
CACHE_SYSTEM_ID      = "iios:execution:snapshot:cache"

VERSION = "1.0.0"

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_SYSTEM    = "iios:system"
ACTOR_BUILDER   = "iios:execution:snapshot:builder"
ACTOR_FACTORY   = "iios:execution:snapshot:factory"
ACTOR_REGISTRY  = "iios:execution:snapshot:registry"
ACTOR_STORE     = "iios:execution:snapshot:store"
ACTOR_USER      = "iios:user"

# ── Capacity defaults ─────────────────────────────────────────────────────────

DEFAULT_MAX_SNAPSHOTS      = 1_000_000
DEFAULT_MAX_HISTORY        = 200          # revisions per execution
DEFAULT_MAX_BUNDLE_SIZE    = 1_000
DEFAULT_CACHE_SIZE         = 10_000

# ── Enumerations ──────────────────────────────────────────────────────────────


class SnapshotLifecycle(str, Enum):
    """Lifecycle status of a published snapshot."""
    CREATED   = "CREATED"
    VALIDATED = "VALIDATED"
    PUBLISHED = "PUBLISHED"
    STORED    = "STORED"
    ARCHIVED  = "ARCHIVED"


class SnapshotTrigger(str, Enum):
    """What caused this snapshot to be taken."""
    STATE_TRANSITION   = "STATE_TRANSITION"   # engine state changed
    TERMINAL           = "TERMINAL"           # execution reached terminal state
    PERIODIC           = "PERIODIC"           # scheduled / heartbeat snapshot
    MANUAL             = "MANUAL"             # operator-triggered
    ERROR              = "ERROR"              # captured on failure
    RECOVERY           = "RECOVERY"           # captured during recovery
    PUBLICATION        = "PUBLICATION"        # final publication snapshot


class SnapshotFormat(str, Enum):
    """Serialisation format for snapshot storage."""
    JSON    = "JSON"
    MSGPACK = "MSGPACK"
    PROTO   = "PROTO"


class SnapshotValidationCode(str, Enum):
    """Machine-readable validation failure codes."""
    MISSING_SNAPSHOT_ID  = "MISSING_SNAPSHOT_ID"
    MISSING_EXECUTION_ID = "MISSING_EXECUTION_ID"
    MISSING_ORDER_ID     = "MISSING_ORDER_ID"
    MISSING_WORKFLOW_ID  = "MISSING_WORKFLOW_ID"
    MISSING_TIMESTAMP    = "MISSING_TIMESTAMP"
    INCONSISTENT_IDS     = "INCONSISTENT_IDS"
    INVALID_STATE        = "INVALID_STATE"
    INVALID_VERSION      = "INVALID_VERSION"
    INCOMPLETE_SNAPSHOT  = "INCOMPLETE_SNAPSHOT"
    DUPLICATE_SNAPSHOT   = "DUPLICATE_SNAPSHOT"
    REGISTRY_CAPACITY    = "REGISTRY_CAPACITY"
    LIFECYCLE_INVALID    = "LIFECYCLE_INVALID"
    RESULT_MISMATCH      = "RESULT_MISMATCH"
