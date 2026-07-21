"""
constants.py — iios.decision.snapshot
=======================================
Enumerations, identifiers, and configuration constants for the
Decision Snapshot subsystem.

DecisionSnapshot is the ONLY published representation of the
Decision Intelligence subsystem.

C9 Decision Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from enum import Enum

# ── Identity ─────────────────────────────────────────────────────────────────

SNAPSHOT_SYSTEM_ID = "iios:decision:snapshot"
VERSION            = "1.0.0"
SCHEMA_VERSION     = "1.0"

# ── Actors ───────────────────────────────────────────────────────────────────

ACTOR_BUILDER    = "iios:snapshot:builder"
ACTOR_FACTORY    = "iios:snapshot:factory"
ACTOR_REGISTRY   = "iios:snapshot:registry"
ACTOR_STORE      = "iios:snapshot:store"
ACTOR_CACHE      = "iios:snapshot:cache"
ACTOR_SYSTEM     = "iios:snapshot:system"
ACTOR_OPERATOR   = "iios:snapshot:operator"
ACTOR_PUBLISHER  = "iios:snapshot:publisher"

# ── Source module labels ──────────────────────────────────────────────────────

SOURCE_M1 = "iios:decision:lifecycle"
SOURCE_M2 = "iios:decision:engine"
SOURCE_M3 = "iios:decision:policies"
SOURCE_M4 = "iios:decision:optimization"

# ── Capacity defaults ─────────────────────────────────────────────────────────

DEFAULT_MAX_SNAPSHOTS     = 10_000
DEFAULT_MAX_VERSIONS      = 100      # per decision_id
DEFAULT_MAX_HISTORY       = 5_000
DEFAULT_CACHE_SIZE        = 1_000
DEFAULT_MAX_BUNDLE_SIZE   = 500
EMA_ALPHA                 = 0.1
THROUGHPUT_WINDOW_S       = 60.0

# ── SnapshotStatus ────────────────────────────────────────────────────────────

class SnapshotStatus(str, Enum):
    """Lifecycle state of a :class:`DecisionSnapshot`."""
    PENDING   = "pending"
    VALID     = "valid"
    INVALID   = "invalid"
    PUBLISHED = "published"
    ARCHIVED  = "archived"


# ── DecisionStatus (combined policy + outcome) ────────────────────────────────

class DecisionStatus(str, Enum):
    """Combined decision status derived from policy + optimization results."""
    APPROVED             = "approved"
    APPROVED_CONDITIONAL = "approved_conditional"
    REJECTED             = "rejected"
    BLOCKED              = "blocked"
    ESCALATED            = "escalated"
    DEFERRED             = "deferred"
    MANUAL_REVIEW        = "manual_review"
    PENDING              = "pending"
    FAILED               = "failed"


# ── DecisionHealth ────────────────────────────────────────────────────────────

class DecisionHealth(str, Enum):
    """Overall health assessment of a decision run."""
    HEALTHY  = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN  = "unknown"


# ── DecisionOutcome ───────────────────────────────────────────────────────────

class DecisionOutcome(str, Enum):
    """Final outcome of the decision workflow."""
    SUCCESS   = "success"
    FAILURE   = "failure"
    PARTIAL   = "partial"
    TIMEOUT   = "timeout"
    CANCELLED = "cancelled"
    SKIPPED   = "skipped"
    UNKNOWN   = "unknown"


# ── SnapshotEventType (6) ─────────────────────────────────────────────────────

class SnapshotEventType(str, Enum):
    SNAPSHOT_CREATED   = "snapshot_created"
    SNAPSHOT_VALIDATED = "snapshot_validated"
    SNAPSHOT_PUBLISHED = "snapshot_published"
    SNAPSHOT_ARCHIVED  = "snapshot_archived"
    SNAPSHOT_RETRIEVED = "snapshot_retrieved"
    SNAPSHOT_CACHED    = "snapshot_cached"


# ── SnapshotValidationCode (9) ────────────────────────────────────────────────

class SnapshotValidationCode(str, Enum):
    IDENTIFIER_CONSISTENCY   = "identifier_consistency"
    LIFECYCLE_CONSISTENCY    = "lifecycle_consistency"
    POLICY_CONSISTENCY       = "policy_consistency"
    OPTIMIZATION_CONSISTENCY = "optimization_consistency"
    DECISION_CONSISTENCY     = "decision_consistency"
    SNAPSHOT_COMPLETENESS    = "snapshot_completeness"
    VERSION_COMPATIBILITY    = "version_compatibility"
    TIMESTAMP_CONSISTENCY    = "timestamp_consistency"
    AUDIT_CONSISTENCY        = "audit_consistency"


# ── Query field names (for store / registry) ──────────────────────────────────

QUERY_BY_SNAPSHOT_ID = "snapshot_id"
QUERY_BY_SESSION_ID  = "session_id"
QUERY_BY_DECISION_ID = "decision_id"
QUERY_BY_WORKFLOW_ID = "workflow_id"
QUERY_BY_PORTFOLIO_ID= "portfolio_id"
QUERY_BY_STRATEGY_ID = "strategy_id"
QUERY_BY_STATUS      = "decision_status"
QUERY_BY_TYPE        = "decision_type"
QUERY_BY_PRIORITY    = "decision_priority"
QUERY_BY_TIMESTAMP   = "created_at"
