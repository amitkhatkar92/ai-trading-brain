"""
constants.py — iios.market.snapshot
=====================================
Enumerations, identifiers, and defaults for the Market Snapshot subsystem.

C12 Market Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
SNAPSHOT_SYSTEM_ID:       str = "iios:market:snapshot"
BUILDER_SYSTEM_ID:        str = "iios:market:snapshot:builder"
REGISTRY_SYSTEM_ID:       str = "iios:market:snapshot:registry"
STORE_SYSTEM_ID:          str = "iios:market:snapshot:store"
CACHE_SYSTEM_ID:          str = "iios:market:snapshot:cache"
HISTORY_SYSTEM_ID:        str = "iios:market:snapshot:history"
FACTORY_SYSTEM_ID:        str = "iios:market:snapshot:factory"
VALIDATION_SYSTEM_ID:     str = "iios:market:snapshot:validation"
BUNDLE_SYSTEM_ID:         str = "iios:market:snapshot:bundle"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:         str = "1.0.0"
SCHEMA_VERSION:  str = "1.0"
MODEL_VERSION:   str = "1.0.0"

# ---------------------------------------------------------------------------
# Actor constants
# ---------------------------------------------------------------------------
ACTOR_SNAPSHOT:   str = "iios:market:snapshot"
ACTOR_BUILDER:    str = "iios:market:snapshot:builder"
ACTOR_SYSTEM:     str = "iios:system"
ACTOR_OPERATOR:   str = "operator"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_MAX_SNAPSHOTS:     int   = 10_000
DEFAULT_MAX_HISTORY:       int   = 1_000
DEFAULT_MAX_CACHE:         int   = 500
DEFAULT_MAX_BUNDLE:        int   = 1_000
DEFAULT_CACHE_TTL_S:       float = 300.0    # 5-minute cache TTL
DEFAULT_SNAPSHOT_TIMEOUT_S: float = 60.0

# Source component identifiers
SOURCE_LIFECYCLE:  str = "lifecycle"
SOURCE_ENGINE:     str = "engine"
SOURCE_POLICY:     str = "policy"
SOURCE_ANALYTICS:  str = "analytics"

# ---------------------------------------------------------------------------
# SnapshotStatus
# ---------------------------------------------------------------------------
class SnapshotStatus(str, Enum):
    """Lifecycle status of a market snapshot."""
    PENDING      = "pending"
    BUILDING     = "building"
    VALID        = "valid"
    INVALID      = "invalid"
    PUBLISHED    = "published"
    ARCHIVED     = "archived"
    EXPIRED      = "expired"


# ---------------------------------------------------------------------------
# SnapshotEventType — 10 domain events
# ---------------------------------------------------------------------------
class SnapshotEventType(str, Enum):
    """Domain events emitted by the snapshot subsystem."""
    SNAPSHOT_CREATED      = "snapshot_created"
    SNAPSHOT_BUILT        = "snapshot_built"
    SNAPSHOT_VALIDATED    = "snapshot_validated"
    SNAPSHOT_PUBLISHED    = "snapshot_published"
    SNAPSHOT_INVALIDATED  = "snapshot_invalidated"
    SNAPSHOT_ARCHIVED     = "snapshot_archived"
    SNAPSHOT_EXPIRED      = "snapshot_expired"
    SNAPSHOT_RETRIEVED    = "snapshot_retrieved"
    SNAPSHOT_UPDATED      = "snapshot_updated"
    SNAPSHOT_FAILED       = "snapshot_failed"


# ---------------------------------------------------------------------------
# SnapshotValidationCode
# ---------------------------------------------------------------------------
class SnapshotValidationCode(str, Enum):
    """Validation check identifiers."""
    IDENTIFIER_CONSISTENT  = "identifier_consistent"
    VERSION_CONSISTENT     = "version_consistent"
    ANALYTICS_CONSISTENT   = "analytics_consistent"
    FORECAST_CONSISTENT    = "forecast_consistent"
    SCORE_CONSISTENT       = "score_consistent"
    SNAPSHOT_COMPLETE      = "snapshot_complete"
    METADATA_INTEGRITY     = "metadata_integrity"


# ---------------------------------------------------------------------------
# HealthStatus
# ---------------------------------------------------------------------------
class HealthStatus(str, Enum):
    """Health status of a subsystem or pipeline."""
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"


# ---------------------------------------------------------------------------
# SnapshotIntegrity
# ---------------------------------------------------------------------------
class SnapshotIntegrity(str, Enum):
    """Snapshot data integrity classification."""
    COMPLETE   = "complete"
    PARTIAL    = "partial"
    MINIMAL    = "minimal"
    EMPTY      = "empty"


# ---------------------------------------------------------------------------
# Score bands for snapshot health
# ---------------------------------------------------------------------------
HEALTH_EXCELLENT:   float = 80.0
HEALTH_GOOD:        float = 60.0
HEALTH_FAIR:        float = 40.0
HEALTH_POOR:        float = 20.0

# Terminal snapshot statuses — cannot transition further
TERMINAL_STATUSES: FrozenSet[SnapshotStatus] = frozenset({
    SnapshotStatus.ARCHIVED,
    SnapshotStatus.EXPIRED,
})

# Published-ready statuses
PUBLISHABLE_STATUSES: FrozenSet[SnapshotStatus] = frozenset({
    SnapshotStatus.VALID,
    SnapshotStatus.PUBLISHED,
})
