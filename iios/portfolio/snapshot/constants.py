"""
constants.py — iios.portfolio.snapshot
=======================================
Enumerations, state machine, identifiers, and numeric defaults for the
Institutional Portfolio Snapshot subsystem.

C10 Portfolio Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
SNAPSHOT_SYSTEM_ID: str = "iios:portfolio:snapshot"
VERSION:            str = "1.0.0"

ACTOR_BUILDER: str = "iios:portfolio:snapshot:builder"
ACTOR_STORE:   str = "iios:portfolio:snapshot:store"
ACTOR_ENGINE:  str = "iios:portfolio:snapshot:engine"

# ---------------------------------------------------------------------------
# Default capacity limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_STORE:           int = 10_000
DEFAULT_MAX_CACHE:           int = 500
DEFAULT_MAX_HISTORY_PER_PF:  int = 100    # snapshot versions per portfolio
DEFAULT_MAX_HISTORY_ENTRIES: int = 1_000  # total tracked snapshots in history


# ---------------------------------------------------------------------------
# SnapshotStatus — lifecycle of a published snapshot
# ---------------------------------------------------------------------------
class SnapshotStatus(str, Enum):
    """
    Publication lifecycle of a PortfolioSnapshot.

    Progression::
        DRAFT → VALIDATED → PUBLISHED → ARCHIVED
    """
    DRAFT      = "draft"
    VALIDATED  = "validated"
    PUBLISHED  = "published"
    ARCHIVED   = "archived"


# ---------------------------------------------------------------------------
# PortfolioHealth — operational health of the portfolio at snapshot time
# ---------------------------------------------------------------------------
class PortfolioHealth(str, Enum):
    HEALTHY  = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN  = "unknown"


# ---------------------------------------------------------------------------
# SnapshotEventType — six lifecycle events
# ---------------------------------------------------------------------------
class SnapshotEventType(str, Enum):
    SNAPSHOT_CREATED   = "snapshot_created"
    SNAPSHOT_VALIDATED = "snapshot_validated"
    SNAPSHOT_PUBLISHED = "snapshot_published"
    SNAPSHOT_ARCHIVED  = "snapshot_archived"
    SNAPSHOT_RETRIEVED = "snapshot_retrieved"
    SNAPSHOT_CACHED    = "snapshot_cached"


# ---------------------------------------------------------------------------
# SnapshotValidationCode — twelve validation checks
# ---------------------------------------------------------------------------
class SnapshotValidationCode(str, Enum):
    IDENTIFIER_CONSISTENCY      = "identifier_consistency"
    LIFECYCLE_CONSISTENCY       = "lifecycle_consistency"
    ALLOCATION_CONSISTENCY      = "allocation_consistency"
    EXPOSURE_CONSISTENCY        = "exposure_consistency"
    DIVERSIFICATION_CONSISTENCY = "diversification_consistency"
    OPTIMIZATION_CONSISTENCY    = "optimization_consistency"
    CONSTRAINT_CONSISTENCY      = "constraint_consistency"
    PORTFOLIO_CONSISTENCY       = "portfolio_consistency"
    SNAPSHOT_COMPLETENESS       = "snapshot_completeness"
    VERSION_COMPATIBILITY       = "version_compatibility"
    TIMESTAMP_CONSISTENCY       = "timestamp_consistency"
    AUDIT_CONSISTENCY           = "audit_consistency"


# ---------------------------------------------------------------------------
# Valid snapshot status transitions
# ---------------------------------------------------------------------------
VALID_SNAPSHOT_TRANSITIONS: Dict[SnapshotStatus, FrozenSet[SnapshotStatus]] = {
    SnapshotStatus.DRAFT:      frozenset({SnapshotStatus.VALIDATED, SnapshotStatus.ARCHIVED}),
    SnapshotStatus.VALIDATED:  frozenset({SnapshotStatus.PUBLISHED, SnapshotStatus.ARCHIVED}),
    SnapshotStatus.PUBLISHED:  frozenset({SnapshotStatus.ARCHIVED}),
    SnapshotStatus.ARCHIVED:   frozenset(),
}

PUBLISHED_STATUSES: FrozenSet[SnapshotStatus] = frozenset({
    SnapshotStatus.PUBLISHED,
    SnapshotStatus.VALIDATED,
})

TERMINAL_STATUSES: FrozenSet[SnapshotStatus] = frozenset({
    SnapshotStatus.ARCHIVED,
})
