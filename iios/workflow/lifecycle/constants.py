"""
constants.py — iios.workflow.lifecycle
----------------------------------------
Constants, enums, and the valid-transition table for the
Workflow Lifecycle module.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 1
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Set


# ════════════════════════════════════════════════════════════════════════
# Enums
# ════════════════════════════════════════════════════════════════════════


class WorkflowLifecycleState(str, Enum):
    """14 lifecycle states for an enterprise workflow session."""
    CREATED      = "created"
    INITIALIZING = "initializing"
    VALIDATING   = "validating"
    READY        = "ready"
    SCHEDULED    = "scheduled"
    QUEUED       = "queued"
    RUNNING      = "running"
    WAITING      = "waiting"
    PAUSED       = "paused"
    RESUMING     = "resuming"
    COMPLETED    = "completed"
    FAILED       = "failed"
    CANCELLED    = "cancelled"
    ARCHIVED     = "archived"


class WorkflowEventType(str, Enum):
    """11 lifecycle event types."""
    WORKFLOW_CREATED     = "workflow_created"
    WORKFLOW_INITIALIZED = "workflow_initialized"
    WORKFLOW_VALIDATED   = "workflow_validated"
    WORKFLOW_SCHEDULED   = "workflow_scheduled"
    WORKFLOW_STARTED     = "workflow_started"
    WORKFLOW_PAUSED      = "workflow_paused"
    WORKFLOW_RESUMED     = "workflow_resumed"
    WORKFLOW_COMPLETED   = "workflow_completed"
    WORKFLOW_FAILED      = "workflow_failed"
    WORKFLOW_CANCELLED   = "workflow_cancelled"
    WORKFLOW_ARCHIVED    = "workflow_archived"


class WorkflowType(str, Enum):
    """Type of enterprise workflow."""
    SEQUENTIAL    = "sequential"
    PARALLEL      = "parallel"
    EVENT_DRIVEN  = "event_driven"
    SCHEDULED     = "scheduled"
    PIPELINE      = "pipeline"
    ORCHESTRATION = "orchestration"
    APPROVAL      = "approval"
    BATCH         = "batch"
    STREAMING     = "streaming"
    INTERNAL      = "internal"


class WorkflowPriority(str, Enum):
    """Execution priority of a workflow session."""
    LOW      = "low"
    NORMAL   = "normal"
    HIGH     = "high"
    CRITICAL = "critical"


class WorkflowValidationCode(str, Enum):
    """Validation check identifiers."""
    IDENTIFIER_CONSISTENCY = "identifier_consistency"
    LIFECYCLE_CONSISTENCY  = "lifecycle_consistency"
    TRANSITION_VALIDITY    = "transition_validity"
    TIMESTAMP_CONSISTENCY  = "timestamp_consistency"
    HISTORY_INTEGRITY      = "history_integrity"


# ════════════════════════════════════════════════════════════════════════
# State classification sets
# ════════════════════════════════════════════════════════════════════════

ACTIVE_STATES: Set[WorkflowLifecycleState] = {
    WorkflowLifecycleState.INITIALIZING,
    WorkflowLifecycleState.VALIDATING,
    WorkflowLifecycleState.READY,
    WorkflowLifecycleState.SCHEDULED,
    WorkflowLifecycleState.QUEUED,
    WorkflowLifecycleState.RUNNING,
    WorkflowLifecycleState.WAITING,
    WorkflowLifecycleState.PAUSED,
    WorkflowLifecycleState.RESUMING,
}

TERMINAL_STATES: Set[WorkflowLifecycleState] = {
    WorkflowLifecycleState.COMPLETED,
    WorkflowLifecycleState.FAILED,
    WorkflowLifecycleState.CANCELLED,
    WorkflowLifecycleState.ARCHIVED,
}

SUCCESS_STATES: Set[WorkflowLifecycleState] = {
    WorkflowLifecycleState.COMPLETED,
}

IMMUTABLE_STATES: Set[WorkflowLifecycleState] = {
    WorkflowLifecycleState.ARCHIVED,
}

# ════════════════════════════════════════════════════════════════════════
# Valid transition table (strict institutional state machine)
# ════════════════════════════════════════════════════════════════════════

VALID_TRANSITIONS: Dict[WorkflowLifecycleState, Set[WorkflowLifecycleState]] = {
    WorkflowLifecycleState.CREATED: {
        WorkflowLifecycleState.INITIALIZING,
        WorkflowLifecycleState.CANCELLED,
    },
    WorkflowLifecycleState.INITIALIZING: {
        WorkflowLifecycleState.VALIDATING,
        WorkflowLifecycleState.FAILED,
        WorkflowLifecycleState.CANCELLED,
    },
    WorkflowLifecycleState.VALIDATING: {
        WorkflowLifecycleState.READY,
        WorkflowLifecycleState.FAILED,
        WorkflowLifecycleState.CANCELLED,
    },
    WorkflowLifecycleState.READY: {
        WorkflowLifecycleState.SCHEDULED,
        WorkflowLifecycleState.QUEUED,
        WorkflowLifecycleState.RUNNING,
        WorkflowLifecycleState.CANCELLED,
    },
    WorkflowLifecycleState.SCHEDULED: {
        WorkflowLifecycleState.QUEUED,
        WorkflowLifecycleState.CANCELLED,
        WorkflowLifecycleState.FAILED,
    },
    WorkflowLifecycleState.QUEUED: {
        WorkflowLifecycleState.RUNNING,
        WorkflowLifecycleState.CANCELLED,
        WorkflowLifecycleState.FAILED,
    },
    WorkflowLifecycleState.RUNNING: {
        WorkflowLifecycleState.WAITING,
        WorkflowLifecycleState.PAUSED,
        WorkflowLifecycleState.COMPLETED,
        WorkflowLifecycleState.FAILED,
        WorkflowLifecycleState.CANCELLED,
    },
    WorkflowLifecycleState.WAITING: {
        WorkflowLifecycleState.RUNNING,
        WorkflowLifecycleState.PAUSED,
        WorkflowLifecycleState.COMPLETED,
        WorkflowLifecycleState.FAILED,
        WorkflowLifecycleState.CANCELLED,
    },
    WorkflowLifecycleState.PAUSED: {
        WorkflowLifecycleState.RESUMING,
        WorkflowLifecycleState.CANCELLED,
        WorkflowLifecycleState.FAILED,
    },
    WorkflowLifecycleState.RESUMING: {
        WorkflowLifecycleState.RUNNING,
        WorkflowLifecycleState.FAILED,
        WorkflowLifecycleState.CANCELLED,
    },
    WorkflowLifecycleState.COMPLETED: {
        WorkflowLifecycleState.ARCHIVED,
    },
    WorkflowLifecycleState.FAILED: {
        WorkflowLifecycleState.INITIALIZING,   # allow retry
        WorkflowLifecycleState.ARCHIVED,
    },
    WorkflowLifecycleState.CANCELLED: {
        WorkflowLifecycleState.ARCHIVED,
    },
    WorkflowLifecycleState.ARCHIVED: set(),    # terminal — no outgoing transitions
}

# ════════════════════════════════════════════════════════════════════════
# Actor / system identifier constants
# ════════════════════════════════════════════════════════════════════════

ACTOR_LIFECYCLE = "workflow-lifecycle"
ACTOR_SYSTEM    = "workflow-system"
ACTOR_OPERATOR  = "operator"

# ════════════════════════════════════════════════════════════════════════
# Size / capacity defaults
# ════════════════════════════════════════════════════════════════════════

DEFAULT_MAX_SESSIONS    = 10_000
DEFAULT_MAX_TRANSITIONS = 50_000
DEFAULT_MAX_HISTORY     = 50_000
DEFAULT_MAX_ARCHIVED    = 5_000

# ════════════════════════════════════════════════════════════════════════
# Version constants
# ════════════════════════════════════════════════════════════════════════

VERSION            = "1.0.0"
FRAMEWORK_VERSION  = "1.0.0"
BUILD_VERSION      = "c16-m1"
SCHEMA_VERSION     = "1"
DEFAULT_VERSION    = "1.0.0"

# ════════════════════════════════════════════════════════════════════════
# Lifecycle system identifiers
# ════════════════════════════════════════════════════════════════════════

LIFECYCLE_SYSTEM_ID = "workflow-lifecycle-system"
REGISTRY_SYSTEM_ID  = "workflow-registry-system"
