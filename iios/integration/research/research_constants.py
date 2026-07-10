"""iios/integration/research/research_constants.py

Constants and enumerations for the Quantitative Research Framework.
Error code prefix: QR
"""
from __future__ import annotations

from enum import Enum, IntEnum


# ── Project ────────────────────────────────────────────────────────────────────

class ResearchProjectStatus(str, Enum):
    DRAFT      = "draft"
    ACTIVE     = "active"
    PAUSED     = "paused"
    ARCHIVED   = "archived"
    COMPLETED  = "completed"
    CANCELLED  = "cancelled"


# ── Experiment ─────────────────────────────────────────────────────────────────

class ExperimentStatus(str, Enum):
    DRAFT       = "draft"
    CONFIGURED  = "configured"
    QUEUED      = "queued"
    RUNNING     = "running"
    PAUSED      = "paused"
    COMPLETED   = "completed"
    FAILED      = "failed"
    CANCELLED   = "cancelled"
    ARCHIVED    = "archived"


class ExperimentPriority(str, Enum):
    LOW      = "low"
    NORMAL   = "normal"
    HIGH     = "high"
    CRITICAL = "critical"


# ── Dataset ────────────────────────────────────────────────────────────────────

class ResearchDatasetStatus(str, Enum):
    PENDING    = "pending"
    VALIDATED  = "validated"
    ACTIVE     = "active"
    DEPRECATED = "deprecated"
    ARCHIVED   = "archived"


class DatasetSourceType(str, Enum):
    HISTORICAL = "historical"
    SYNTHETIC  = "synthetic"
    EXTERNAL   = "external"
    DERIVED    = "derived"
    UPLOADED   = "uploaded"
    CUSTOM     = "custom"


# ── Session ────────────────────────────────────────────────────────────────────

class ResearchSessionStatus(str, Enum):
    IDLE       = "idle"
    ACTIVE     = "active"
    PAUSED     = "paused"
    COMPLETED  = "completed"
    FAILED     = "failed"
    ABORTED    = "aborted"


# ── Workflow ───────────────────────────────────────────────────────────────────

class WorkflowStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    PAUSED    = "paused"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


# ── Checkpoint ─────────────────────────────────────────────────────────────────

class CheckpointStatus(str, Enum):
    NONE      = "none"
    SAVED     = "saved"
    RESTORED  = "restored"
    INVALID   = "invalid"


# ── Events ─────────────────────────────────────────────────────────────────────

class ResearchEventType(str, Enum):
    PROJECT_CREATED      = "project_created"
    PROJECT_ARCHIVED     = "project_archived"
    PROJECT_COMPLETED    = "project_completed"
    PROJECT_CANCELLED    = "project_cancelled"
    EXPERIMENT_CREATED   = "experiment_created"
    EXPERIMENT_STARTED   = "experiment_started"
    EXPERIMENT_PAUSED    = "experiment_paused"
    EXPERIMENT_RESUMED   = "experiment_resumed"
    EXPERIMENT_COMPLETED = "experiment_completed"
    EXPERIMENT_FAILED    = "experiment_failed"
    EXPERIMENT_CANCELLED = "experiment_cancelled"
    EXPERIMENT_ARCHIVED  = "experiment_archived"
    DATASET_REGISTERED   = "dataset_registered"
    DATASET_DEPRECATED   = "dataset_deprecated"
    SESSION_STARTED      = "session_started"
    SESSION_ENDED        = "session_ended"
    CHECKPOINT_SAVED     = "checkpoint_saved"
    RESULT_RECORDED      = "result_recorded"


# ── Engine ─────────────────────────────────────────────────────────────────────

class ResearchEngineStatus(str, Enum):
    STOPPED      = "stopped"
    INITIALIZING = "initializing"
    RUNNING      = "running"
    STOPPING     = "stopping"
    ERROR        = "error"


# ── Module metadata ────────────────────────────────────────────────────────────

RESEARCH_ENGINE_VERSION    = "1.0.0"
RESEARCH_ENGINE_SYSTEM_ID  = "iios:integration:research:engine"
RESEARCH_ERROR_PREFIX      = "QR"

# ── Capacity / defaults ────────────────────────────────────────────────────────

DEFAULT_MAX_PROJECTS          = 10_000
DEFAULT_MAX_EXPERIMENTS       = 100_000
DEFAULT_MAX_DATASETS          = 50_000
DEFAULT_MAX_SESSIONS          = 100_000
DEFAULT_MAX_RESULTS           = 100_000
DEFAULT_MAX_HISTORY_ENTRIES   = 1_000_000

DEFAULT_EXPERIMENT_TIMEOUT_SEC   = 3_600.0   # 1 hour
DEFAULT_CHECKPOINT_INTERVAL_SEC  = 300.0     # 5 minutes
DEFAULT_CACHE_TTL_SEC            = 3_600
DEFAULT_PARALLEL_EXPERIMENTS     = 8
DEFAULT_EXPERIMENT_VERSION       = "1.0.0"
