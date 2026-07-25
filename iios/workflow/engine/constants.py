"""
constants.py — iios.workflow.engine
--------------------------------------
Enums, state definitions, and constants for the Workflow Engine.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Set


# ════════════════════════════════════════════════════════════════════════
# Engine States (11)
# ════════════════════════════════════════════════════════════════════════


class WorkflowEngineState(str, Enum):
    """11 operational states for the Workflow Engine."""
    IDLE         = "idle"
    INITIALIZING = "initializing"
    VALIDATING   = "validating"
    SCHEDULING   = "scheduling"
    QUEUING      = "queuing"
    DISPATCHING  = "dispatching"
    MONITORING   = "monitoring"
    PUBLISHING   = "publishing"
    COMPLETED    = "completed"
    FAILED       = "failed"
    STOPPED      = "stopped"


# ════════════════════════════════════════════════════════════════════════
# Engine Event Types (9)
# ════════════════════════════════════════════════════════════════════════


class WorkflowEngineEventType(str, Enum):
    """9 event types emitted by the Workflow Engine."""
    WORKFLOW_INITIALIZED       = "workflow_initialized"
    WORKFLOW_VALIDATED         = "workflow_validated"
    WORKFLOW_QUEUED            = "workflow_queued"
    WORKFLOW_DISPATCHED        = "workflow_dispatched"
    WORKFLOW_STARTED           = "workflow_started"
    WORKFLOW_COMPLETED         = "workflow_completed"
    WORKFLOW_FAILED            = "workflow_failed"
    WORKFLOW_CANCELLED         = "workflow_cancelled"
    WORKFLOW_SNAPSHOT_PUBLISHED = "workflow_snapshot_published"


# ════════════════════════════════════════════════════════════════════════
# Engine Operations (13)
# ════════════════════════════════════════════════════════════════════════


class WorkflowEngineOperation(str, Enum):
    """13 operations supported by the Workflow Engine."""
    INITIALIZE  = "initialize"
    VALIDATE    = "validate"
    SCHEDULE    = "schedule"
    QUEUE       = "queue"
    DISPATCH    = "dispatch"
    MONITOR     = "monitor"
    PUBLISH     = "publish"
    HEALTH      = "health"
    STATUS      = "status"
    STATISTICS  = "statistics"
    HISTORY     = "history"
    CANCEL      = "cancel"
    RETRY       = "retry"


# ════════════════════════════════════════════════════════════════════════
# Dispatch Mode
# ════════════════════════════════════════════════════════════════════════


class WorkflowDispatchMode(str, Enum):
    """How a workflow request is dispatched through the engine."""
    IMMEDIATE    = "immediate"
    SCHEDULED    = "scheduled"
    EVENT_DRIVEN = "event_driven"
    PRIORITY     = "priority"
    BATCH        = "batch"
    RETRY        = "retry"


# ════════════════════════════════════════════════════════════════════════
# Pipeline Stages (8)
# ════════════════════════════════════════════════════════════════════════


class WorkflowPipelineStage(str, Enum):
    """8 ordered pipeline stages for workflow execution coordination."""
    INITIALIZE  = "initialize"
    VALIDATE    = "validate"
    SCHEDULE    = "schedule"
    QUEUE       = "queue"
    DISPATCH    = "dispatch"
    GOVERN      = "govern"        # delegates to M3 Governance
    ORCHESTRATE = "orchestrate"   # delegates to M4 Orchestration
    PUBLISH     = "publish"


# ════════════════════════════════════════════════════════════════════════
# Validation Checks (6)
# ════════════════════════════════════════════════════════════════════════


class WorkflowEngineValidationCheck(str, Enum):
    """6 validation checks for WorkflowEngineRequest objects."""
    WORKFLOW_CONFIGURATION = "workflow_configuration"
    SESSION_INTEGRITY      = "session_integrity"
    QUEUE_CONSISTENCY      = "queue_consistency"
    PRIORITY_INTEGRITY     = "priority_integrity"
    LIFECYCLE_CONSISTENCY  = "lifecycle_consistency"
    INPUT_COMPLETENESS     = "input_completeness"


# ════════════════════════════════════════════════════════════════════════
# Response Status
# ════════════════════════════════════════════════════════════════════════


class WorkflowEngineResponseStatus(str, Enum):
    """Status values for WorkflowEngineResponse."""
    SUCCESS   = "success"
    FAILURE   = "failure"
    PARTIAL   = "partial"
    CANCELLED = "cancelled"


# ════════════════════════════════════════════════════════════════════════
# Priority levels
# ════════════════════════════════════════════════════════════════════════


class WorkflowQueuePriority(int, Enum):
    """Integer priority levels for the queue (lower = higher urgency)."""
    CRITICAL = 0
    HIGH     = 1
    NORMAL   = 2
    LOW      = 3


# ════════════════════════════════════════════════════════════════════════
# Ordered pipeline stage list
# ════════════════════════════════════════════════════════════════════════

PIPELINE_STAGE_ORDER: List[WorkflowPipelineStage] = [
    WorkflowPipelineStage.INITIALIZE,
    WorkflowPipelineStage.VALIDATE,
    WorkflowPipelineStage.SCHEDULE,
    WorkflowPipelineStage.QUEUE,
    WorkflowPipelineStage.DISPATCH,
    WorkflowPipelineStage.GOVERN,
    WorkflowPipelineStage.ORCHESTRATE,
    WorkflowPipelineStage.PUBLISH,
]

# ════════════════════════════════════════════════════════════════════════
# Actor constants
# ════════════════════════════════════════════════════════════════════════

ACTOR_ENGINE    = "workflow-engine"
ACTOR_SCHEDULER = "workflow-scheduler"
ACTOR_SYSTEM    = "workflow-system"
ACTOR_MONITOR   = "workflow-monitor"

# ════════════════════════════════════════════════════════════════════════
# Default capacity / sizing
# ════════════════════════════════════════════════════════════════════════

DEFAULT_QUEUE_SIZE       = 10_000
DEFAULT_MAX_HISTORY      = 50_000
DEFAULT_MAX_SESSIONS     = 10_000
DEFAULT_MAX_ACTIVE       = 1_000
DEFAULT_PRIORITY         = int(WorkflowQueuePriority.NORMAL)

# ════════════════════════════════════════════════════════════════════════
# Version / system identifiers
# ════════════════════════════════════════════════════════════════════════

VERSION            = "1.0.0"
FRAMEWORK_VERSION  = "1.0.0"
BUILD_VERSION      = "c16-m2"
SCHEMA_VERSION     = "1"
DEFAULT_ENGINE_ID  = "iios-workflow-engine"
ENGINE_SYSTEM_ID   = "workflow-engine-system"
MANAGER_SYSTEM_ID  = "workflow-manager-system"
DEFAULT_ENVIRONMENT = "production"
