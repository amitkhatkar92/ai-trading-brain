"""
constants.py — iios.workflow.snapshot
---------------------------------------
All enumerations and constants for the Workflow Snapshot module.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 5
"""
from __future__ import annotations

from enum import Enum

# ── Versioning ────────────────────────────────────────────────────────────────
VERSION            = "1.0.0"
BUILD_VERSION      = "c16-m5"
SNAPSHOT_VERSION   = "1.0"
FRAMEWORK_VERSION  = "c16-1.0"

# ── ID Prefixes ───────────────────────────────────────────────────────────────
PREFIX_SNAPSHOT  = "wsnap-"
PREFIX_BUNDLE    = "wbndl-"
PREFIX_EVENT     = "wsevt-"
PREFIX_META      = "wsmeta-"

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_MAX_HISTORY    = 50_000
DEFAULT_MAX_REGISTRY   = 10_000
DEFAULT_CACHE_SIZE     = 1_000
DEFAULT_MAX_SNAPSHOTS  = 10_000

# ── Actor labels ──────────────────────────────────────────────────────────────
ACTOR_BUILDER    = "WorkflowSnapshotBuilder"
ACTOR_REGISTRY   = "WorkflowSnapshotRegistry"
ACTOR_STORE      = "WorkflowSnapshotStore"
ACTOR_VALIDATOR  = "WorkflowSnapshotValidation"


# ── Enums ─────────────────────────────────────────────────────────────────────

class SnapshotStatus(str, Enum):
    """Publication status of a snapshot."""
    PENDING    = "pending"
    VALID      = "valid"
    INVALID    = "invalid"
    PUBLISHED  = "published"
    SUPERSEDED = "superseded"
    ARCHIVED   = "archived"


class SnapshotEventType(str, Enum):
    """Domain events emitted by snapshot components."""
    SNAPSHOT_CREATED     = "snapshot_created"
    SNAPSHOT_VALIDATED   = "snapshot_validated"
    SNAPSHOT_PUBLISHED   = "snapshot_published"
    SNAPSHOT_SUPERSEDED  = "snapshot_superseded"
    SNAPSHOT_ARCHIVED    = "snapshot_archived"
    SNAPSHOT_INVALID     = "snapshot_invalid"
    BUNDLE_CREATED       = "bundle_created"
    REGISTRY_CLEARED     = "registry_cleared"


class WorkflowHealthStatus(str, Enum):
    """Aggregated health indicator for a workflow snapshot."""
    HEALTHY    = "healthy"
    DEGRADED   = "degraded"
    FAILED     = "failed"
    UNKNOWN    = "unknown"


class GovernanceDecision(str, Enum):
    """Governance outcome captured in snapshot."""
    APPROVED                  = "approved"
    APPROVED_WITH_CONDITIONS  = "approved_with_conditions"
    REJECTED                  = "rejected"
    BLOCKED                   = "blocked"
    ESCALATED                 = "escalated"
    REQUIRES_MANUAL_APPROVAL  = "requires_manual_approval"
    REQUIRES_EXECUTIVE_APPROVAL = "requires_executive_approval"
    EMERGENCY_STOPPED         = "emergency_stopped"
    PENDING                   = "pending"
    NOT_EVALUATED             = "not_evaluated"


class ExecutionStatus(str, Enum):
    """Execution outcome captured in snapshot."""
    PENDING      = "pending"
    RUNNING      = "running"
    COMPLETED    = "completed"
    FAILED       = "failed"
    CANCELLED    = "cancelled"
    TIMED_OUT    = "timed_out"
    COMPENSATING = "compensating"
    RECOVERING   = "recovering"


class LifecycleState(str, Enum):
    """Workflow lifecycle state captured in snapshot."""
    DRAFT      = "draft"
    SUBMITTED  = "submitted"
    APPROVED   = "approved"
    ACTIVE     = "active"
    COMPLETED  = "completed"
    ARCHIVED   = "archived"
    FAILED     = "failed"
    CANCELLED  = "cancelled"


class SnapshotCategory(str, Enum):
    """Snapshot classification."""
    WORKFLOW      = "workflow"
    STEP          = "step"
    GOVERNANCE    = "governance"
    ORCHESTRATION = "orchestration"
    SYSTEM        = "system"
    AUDIT         = "audit"
