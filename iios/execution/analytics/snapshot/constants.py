"""
iios/execution/analytics/snapshot/constants.py
===============================================
Constants, enumerations, and identifiers for the Execution Analytics
Snapshot package (C8 M5).

C8 Execution Analytics & Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from enum import Enum
from typing import Dict

# ── Re-export upstream enums so callers import ONLY from snapshot ─────────────
from iios.execution.analytics.lifecycle import AnalyticsScope, AnalyticsMode


# ── Snapshot lifecycle states ─────────────────────────────────────────────────

class SnapshotLifecycleState(str, Enum):
    BUILDING   = "building"
    VALIDATING = "validating"
    READY      = "ready"
    PUBLISHED  = "published"
    ARCHIVED   = "archived"
    INVALID    = "invalid"


# ── Analytics status ──────────────────────────────────────────────────────────

class AnalyticsStatus(str, Enum):
    PENDING   = "pending"
    ACTIVE    = "active"
    COMPLETED = "completed"
    FAILED    = "failed"
    ARCHIVED  = "archived"


# ── Analytics health ──────────────────────────────────────────────────────────

class AnalyticsHealth(str, Enum):
    HEALTHY  = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN  = "unknown"

HEALTH_THRESHOLDS: Dict[str, float] = {
    AnalyticsHealth.HEALTHY:  0.80,
    AnalyticsHealth.DEGRADED: 0.50,
    AnalyticsHealth.CRITICAL: 0.20,
}


def health_from_score(score: float) -> AnalyticsHealth:
    """Convert a [0, 1] operational health score to AnalyticsHealth."""
    if score >= HEALTH_THRESHOLDS[AnalyticsHealth.HEALTHY]:
        return AnalyticsHealth.HEALTHY
    if score >= HEALTH_THRESHOLDS[AnalyticsHealth.DEGRADED]:
        return AnalyticsHealth.DEGRADED
    if score >= HEALTH_THRESHOLDS[AnalyticsHealth.CRITICAL]:
        return AnalyticsHealth.CRITICAL
    return AnalyticsHealth.CRITICAL


# ── Snapshot event types ──────────────────────────────────────────────────────

class SnapshotEventType(str, Enum):
    SNAPSHOT_CREATED   = "snapshot_created"
    SNAPSHOT_VALIDATED = "snapshot_validated"
    SNAPSHOT_PUBLISHED = "snapshot_published"
    SNAPSHOT_ARCHIVED  = "snapshot_archived"
    SNAPSHOT_RETRIEVED = "snapshot_retrieved"
    SNAPSHOT_CACHED    = "snapshot_cached"


# ── System IDs ────────────────────────────────────────────────────────────────

SNAPSHOT_ENGINE_ID   = "iios.execution.analytics.snapshot.engine"
BUILDER_SYSTEM_ID    = "iios.execution.analytics.snapshot.builder"
STORE_SYSTEM_ID      = "iios.execution.analytics.snapshot.store"
REGISTRY_SYSTEM_ID   = "iios.execution.analytics.snapshot.registry"
CACHE_SYSTEM_ID      = "iios.execution.analytics.snapshot.cache"
FACTORY_SYSTEM_ID    = "iios.execution.analytics.snapshot.factory"
HISTORY_SYSTEM_ID    = "iios.execution.analytics.snapshot.history"

# ── Actor identifiers ─────────────────────────────────────────────────────────

ACTOR_BUILDER  = "analytics.snapshot.builder"
ACTOR_STORE    = "analytics.snapshot.store"
ACTOR_FACTORY  = "analytics.snapshot.factory"
ACTOR_SYSTEM   = "analytics.snapshot.system"
ACTOR_OPERATOR = "analytics.snapshot.operator"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_SNAPSHOTS    = 10_000
DEFAULT_MAX_HISTORY      = 2_000
DEFAULT_CACHE_SIZE       = 500
DEFAULT_SNAPSHOT_TTL     = 3_600.0   # seconds — 1 hour

SNAPSHOT_FRAMEWORK_VERSION = "1.0.0"
SNAPSHOT_SCHEMA_VERSION    = "1.0"
