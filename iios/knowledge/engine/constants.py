"""
constants.py — iios.knowledge.engine
=======================================
Enumerations, state machine, identifiers, and defaults for the
Institutional Knowledge Engine subsystem.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
ENGINE_SYSTEM_ID:     str = "iios:knowledge:engine"
SCHEDULER_SYSTEM_ID:  str = "iios:knowledge:engine:scheduler"
DISPATCHER_SYSTEM_ID: str = "iios:knowledge:engine:dispatcher"
REGISTRY_SYSTEM_ID:   str = "iios:knowledge:engine:registry"
FACTORY_SYSTEM_ID:    str = "iios:knowledge:engine:factory"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Actor constants
# ---------------------------------------------------------------------------
ACTOR_ENGINE:     str = "iios:knowledge:engine"
ACTOR_SCHEDULER:  str = "iios:knowledge:engine:scheduler"
ACTOR_DISPATCHER: str = "iios:knowledge:engine:dispatcher"
ACTOR_OPERATOR:   str = "operator"
ACTOR_SYSTEM:     str = "iios:system"

# ---------------------------------------------------------------------------
# Default limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_CONCURRENT_SESSIONS: int   = 200
DEFAULT_MAX_PIPELINES:           int   = 5_000
DEFAULT_MAX_HISTORY:             int   = 1_000
DEFAULT_MAX_SCHEDULER_QUEUE:     int   = 10_000
DEFAULT_MAX_ARCHIVED_PIPELINES:  int   = 10_000

# ---------------------------------------------------------------------------
# Timeout defaults (seconds)
# ---------------------------------------------------------------------------
DEFAULT_COLLECT_TIMEOUT_S:  float = 30.0
DEFAULT_DISPATCH_TIMEOUT_S: float = 60.0
DEFAULT_PUBLISH_TIMEOUT_S:  float = 30.0


# ---------------------------------------------------------------------------
# EngineState — knowledge engine processing states (11)
# ---------------------------------------------------------------------------
class EngineState(str, Enum):
    """
    States of a knowledge engine processing cycle.

    Lifecycle progression (happy path)::

        IDLE → INITIALIZING → COLLECTING → VALIDATING → CLASSIFYING
             → DISPATCHING → PROCESSING → PUBLISHING → COMPLETED → IDLE

    Failure::

        any active state → FAILED → IDLE

    Stop::

        any state → STOPPED (terminal)
    """
    IDLE         = "idle"
    INITIALIZING = "initializing"
    COLLECTING   = "collecting"
    VALIDATING   = "validating"
    CLASSIFYING  = "classifying"
    DISPATCHING  = "dispatching"
    PROCESSING   = "processing"
    PUBLISHING   = "publishing"
    COMPLETED    = "completed"
    FAILED       = "failed"
    STOPPED      = "stopped"


# ---------------------------------------------------------------------------
# KnowledgeWorkflowType
# ---------------------------------------------------------------------------
class KnowledgeWorkflowType(str, Enum):
    """Supported knowledge engine workflow classifications."""
    KNOWLEDGE_CAPTURE        = "knowledge_capture"
    KNOWLEDGE_AGGREGATION    = "knowledge_aggregation"
    KNOWLEDGE_CLASSIFICATION = "knowledge_classification"
    ENTERPRISE_EVENT_COLLECTION = "enterprise_event_collection"
    KNOWLEDGE_PUBLICATION    = "knowledge_publication"
    METADATA_COLLECTION      = "metadata_collection"
    OPERATIONAL_TRACKING     = "operational_knowledge_tracking"
    SCHEDULED_COLLECTION     = "scheduled_knowledge_collection"
    BATCH_COLLECTION         = "batch_collection"
    PRIORITY_COLLECTION      = "priority_collection"


# ---------------------------------------------------------------------------
# KnowledgeSource — enterprise data sources
# ---------------------------------------------------------------------------
class KnowledgeSource(str, Enum):
    """Enterprise subsystem sources of knowledge artifacts."""
    EXECUTION_INTELLIGENCE  = "execution_intelligence"
    EXECUTION_RECOVERY      = "execution_recovery"
    EXECUTION_ANALYTICS     = "execution_analytics"
    DECISION_INTELLIGENCE   = "decision_intelligence"
    PORTFOLIO_INTELLIGENCE  = "portfolio_intelligence"
    RISK_INTELLIGENCE       = "risk_intelligence"
    MARKET_INTELLIGENCE     = "market_intelligence"
    AI_SUPERVISOR           = "ai_supervisor"
    INFRASTRUCTURE          = "infrastructure"
    ENTERPRISE              = "enterprise"
    UNKNOWN                 = "unknown"


# ---------------------------------------------------------------------------
# SchedulerPriority
# ---------------------------------------------------------------------------
class SchedulerPriority(IntEnum):
    """Scheduling priority levels for knowledge collection requests."""
    CRITICAL  = 0
    HIGH      = 1
    NORMAL    = 2
    LOW       = 3
    BATCH     = 4


# ---------------------------------------------------------------------------
# SchedulerMode
# ---------------------------------------------------------------------------
class SchedulerMode(str, Enum):
    """Knowledge scheduler operating modes."""
    CONTINUOUS   = "continuous"
    SCHEDULED    = "scheduled"
    EVENT_DRIVEN = "event_driven"
    PRIORITY     = "priority"
    BATCH        = "batch"


# ---------------------------------------------------------------------------
# PipelineStatus
# ---------------------------------------------------------------------------
class PipelineStatus(str, Enum):
    """Status of a knowledge workflow pipeline."""
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# ResponseStatus
# ---------------------------------------------------------------------------
class ResponseStatus(str, Enum):
    """Overall status of a KnowledgeResponse."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"


# ---------------------------------------------------------------------------
# KnowledgeValidationCode
# ---------------------------------------------------------------------------
class KnowledgeValidationCode(str, Enum):
    """Validation check identifiers for the KnowledgeEngineValidator."""
    KNOWLEDGE_INTEGRITY  = "KNOWLEDGE_INTEGRITY"
    ARTIFACT_CONSISTENCY = "ARTIFACT_CONSISTENCY"
    METADATA_CONSISTENCY = "METADATA_CONSISTENCY"
    LIFECYCLE_CONSISTENCY = "LIFECYCLE_CONSISTENCY"
    INPUT_COMPLETENESS   = "INPUT_COMPLETENESS"
    SOURCE_AVAILABILITY  = "SOURCE_AVAILABILITY"


# ---------------------------------------------------------------------------
# KnowledgeEventType — 9 engine-level events
# ---------------------------------------------------------------------------
class KnowledgeEventType(str, Enum):
    """Domain events emitted by the Knowledge Engine."""
    KNOWLEDGE_INITIALIZED         = "knowledge_engine.initialized"
    KNOWLEDGE_COLLECTION_STARTED  = "knowledge_engine.collection_started"
    KNOWLEDGE_COLLECTED           = "knowledge_engine.collected"
    KNOWLEDGE_VALIDATED           = "knowledge_engine.validated"
    KNOWLEDGE_CLASSIFIED          = "knowledge_engine.classified"
    KNOWLEDGE_DISPATCHED          = "knowledge_engine.dispatched"
    KNOWLEDGE_PUBLISHED           = "knowledge_engine.published"
    KNOWLEDGE_COMPLETED           = "knowledge_engine.completed"
    KNOWLEDGE_FAILED              = "knowledge_engine.failed"
