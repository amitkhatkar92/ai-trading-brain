"""
constants.py — iios.integration.snapshot
-----------------------------------------
Enums, type definitions, and constants for the
Integration Snapshot module.

The snapshot is the immutable, versioned, canonical published
representation of Enterprise Integration & Connectivity.

C15 Enterprise Integration & Connectivity — Phase 1, Module 5
"""
from __future__ import annotations

from enum import Enum
from typing import List


# ════════════════════════════════════════════════════════════════════════
# Snapshot Status  (4)
# ════════════════════════════════════════════════════════════════════════


class SnapshotStatus(str, Enum):
    """Publication lifecycle status of an integration snapshot."""
    DRAFT     = "draft"
    PUBLISHED = "published"
    ARCHIVED  = "archived"
    EXPIRED   = "expired"


# ════════════════════════════════════════════════════════════════════════
# Snapshot Scope  (5)
# ════════════════════════════════════════════════════════════════════════


class SnapshotScope(str, Enum):
    """Operational scope captured by a snapshot."""
    COMPONENT   = "component"
    SUBSYSTEM   = "subsystem"
    ENTERPRISE  = "enterprise"
    GLOBAL      = "global"
    INTERNAL    = "internal"


# ════════════════════════════════════════════════════════════════════════
# Snapshot Integration Type  (9)
# ════════════════════════════════════════════════════════════════════════


class SnapshotIntegrationType(str, Enum):
    """Integration pattern captured by the snapshot."""
    REST_API      = "rest_api"
    MESSAGING     = "messaging"
    STREAMING     = "streaming"
    WEBSOCKET     = "websocket"
    DATABASE      = "database"
    FILE          = "file"
    EVENT_STREAM  = "event_stream"
    ENTERPRISE    = "enterprise"
    FULL          = "full"


# ════════════════════════════════════════════════════════════════════════
# Lifecycle State  (9 — mirrors lifecycle module values)
# ════════════════════════════════════════════════════════════════════════


class LifecycleState(str, Enum):
    """Lifecycle state recorded in the snapshot (mirror of lifecycle module)."""
    CREATED       = "created"
    INITIALIZING  = "initializing"
    ACTIVE        = "active"
    PAUSED        = "paused"
    RESUMING      = "resuming"
    COMPLETED     = "completed"
    FAILED        = "failed"
    ARCHIVED      = "archived"
    UNKNOWN       = "unknown"


# ════════════════════════════════════════════════════════════════════════
# Governance State  (6)
# ════════════════════════════════════════════════════════════════════════


class GovernanceState(str, Enum):
    """Governance evaluation state at the time of snapshot."""
    COMPLIANT     = "compliant"
    NON_COMPLIANT = "non_compliant"
    UNDER_REVIEW  = "under_review"
    EXEMPT        = "exempt"
    PENDING       = "pending"
    UNKNOWN       = "unknown"


# ════════════════════════════════════════════════════════════════════════
# Connectivity State  (5)
# ════════════════════════════════════════════════════════════════════════


class ConnectivityState(str, Enum):
    """Overall connectivity health at the time of snapshot."""
    CONNECTED    = "connected"
    DEGRADED     = "degraded"
    DISCONNECTED = "disconnected"
    PARTIAL      = "partial"
    UNKNOWN      = "unknown"


# ════════════════════════════════════════════════════════════════════════
# Snapshot Event Types  (10)
# ════════════════════════════════════════════════════════════════════════


class SnapshotEventType(str, Enum):
    """Event types emitted during snapshot lifecycle."""
    SNAPSHOT_CREATED       = "snapshot_created"
    SNAPSHOT_PUBLISHED     = "snapshot_published"
    SNAPSHOT_ARCHIVED      = "snapshot_archived"
    SNAPSHOT_RETRIEVED     = "snapshot_retrieved"
    SNAPSHOT_VALIDATED     = "snapshot_validated"
    SNAPSHOT_EXPIRED       = "snapshot_expired"
    SNAPSHOT_BUNDLE_CREATED= "snapshot_bundle_created"
    SNAPSHOT_CACHE_HIT     = "snapshot_cache_hit"
    SNAPSHOT_CACHE_MISS    = "snapshot_cache_miss"
    SNAPSHOT_VERSION_BUMPED= "snapshot_version_bumped"


# ════════════════════════════════════════════════════════════════════════
# Snapshot Validation Checks  (7)
# ════════════════════════════════════════════════════════════════════════


class SnapshotValidationCheck(str, Enum):
    """The 7 integrity checks performed by the snapshot validator."""
    IDENTIFIER_CONSISTENCY = "identifier_consistency"
    VERSION_CONSISTENCY    = "version_consistency"
    CONNECTOR_CONSISTENCY  = "connector_consistency"
    PROTOCOL_CONSISTENCY   = "protocol_consistency"
    SECURITY_CONSISTENCY   = "security_consistency"
    METADATA_INTEGRITY     = "metadata_integrity"
    SNAPSHOT_COMPLETENESS  = "snapshot_completeness"


# ════════════════════════════════════════════════════════════════════════
# Protocol Health  (4)
# ════════════════════════════════════════════════════════════════════════


class ProtocolHealth(str, Enum):
    """Health status of a single protocol within the snapshot."""
    HEALTHY     = "healthy"
    DEGRADED    = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN     = "unknown"


# ════════════════════════════════════════════════════════════════════════
# String constants
# ════════════════════════════════════════════════════════════════════════


SNAPSHOT_VERSION:     str = "1.0.0"
FRAMEWORK_VERSION:    str = "1.0.0"

SNAPSHOT_ID_PREFIX:   str = "snap-"
BUNDLE_ID_PREFIX:     str = "bndl-"
EVENT_ID_PREFIX:      str = "sevnt-"
ENTRY_ID_PREFIX:      str = "shist-"

# ════════════════════════════════════════════════════════════════════════
# Numeric constants
# ════════════════════════════════════════════════════════════════════════


DEFAULT_SNAPSHOT_TTL_SECONDS:    int   = 3_600      # 1 hour
DEFAULT_HISTORY_SIZE:            int   = 500
DEFAULT_CACHE_SIZE:              int   = 100
DEFAULT_CACHE_TTL_SECONDS:       float = 300.0      # 5 minutes
DEFAULT_MAX_BUNDLE_SIZE:         int   = 50
DEFAULT_STORE_MAX:               int   = 10_000

# ════════════════════════════════════════════════════════════════════════
# Ordered list of validation checks (for consistent reporting)
# ════════════════════════════════════════════════════════════════════════


VALIDATION_CHECK_ORDER: List[SnapshotValidationCheck] = [
    SnapshotValidationCheck.IDENTIFIER_CONSISTENCY,
    SnapshotValidationCheck.VERSION_CONSISTENCY,
    SnapshotValidationCheck.CONNECTOR_CONSISTENCY,
    SnapshotValidationCheck.PROTOCOL_CONSISTENCY,
    SnapshotValidationCheck.SECURITY_CONSISTENCY,
    SnapshotValidationCheck.METADATA_INTEGRITY,
    SnapshotValidationCheck.SNAPSHOT_COMPLETENESS,
]
