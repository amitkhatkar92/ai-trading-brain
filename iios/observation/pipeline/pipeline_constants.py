"""
iios/observation/pipeline/pipeline_constants.py
===============================================
Enumerations and constants for the Pipeline Engine.
"""
from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    "StageMode", "ExecutionMode", "PipelineState", "StagePriority",
    "CheckpointPolicy", "RetryBackoff", "FailurePolicy", "SchedulerType",
    # Stage name constants
    "STAGE_COLLECT", "STAGE_DEDUPLICATE", "STAGE_NORMALIZE",
    "STAGE_VALIDATE", "STAGE_QUALITY", "STAGE_CLASSIFY",
    "STAGE_ONTOLOGY_MAP", "STAGE_SEMANTIC_ENRICH", "STAGE_CONTEXT_ENRICH",
    "STAGE_KNOWLEDGE_TRANSFORM", "STAGE_KNOWLEDGE_LINK",
    "STAGE_PERSIST", "STAGE_CACHE_UPDATE", "STAGE_PUBLISH_EVENTS",
    "STAGE_COLLECT_METRICS", "STAGE_AUDIT_LOG", "STAGE_COMPLETE",
    # Pipeline name constants
    "PIPELINE_STANDARD", "PIPELINE_FAST", "PIPELINE_VALIDATION_ONLY",
    # Numeric constants
    "DEFAULT_STAGE_TIMEOUT_MS", "DEFAULT_RETRY_COUNT", "DEFAULT_RETRY_DELAY_MS",
    "MAX_PIPELINE_HISTORY", "MAX_STAGE_TIMEOUT_MS",
    "DEFAULT_BATCH_SIZE", "DEFAULT_BATCH_TIMEOUT_S",
    "PIPELINE_NAMESPACE",
]


class StageMode(str, Enum):
    """How a pipeline stage should be executed."""
    SEQUENTIAL  = "sequential"   # run in order, wait for completion
    PARALLEL    = "parallel"     # run concurrently with sibling stages
    CONDITIONAL = "conditional"  # run only if a condition function returns True
    OPTIONAL    = "optional"     # skip silently on failure


class ExecutionMode(str, Enum):
    """Execution mode for the pipeline."""
    SYNC      = "sync"       # blocking, caller waits for result
    BATCH     = "batch"      # accumulate observations, process in bulk
    STREAMING = "streaming"  # process observations as they arrive
    PRIORITY  = "priority"   # process by priority order


class PipelineState(str, Enum):
    """Current lifecycle state of a pipeline run."""
    IDLE       = "idle"
    RUNNING    = "running"
    PAUSED     = "paused"
    COMPLETED  = "completed"
    FAILED     = "failed"
    ABORTED    = "aborted"
    RETRYING   = "retrying"


class StagePriority(int, Enum):
    """Execution priority weight for pipeline stages."""
    MINIMAL  = 0
    LOW      = 10
    NORMAL   = 20
    HIGH     = 30
    CRITICAL = 40


class CheckpointPolicy(str, Enum):
    """When to write execution checkpoints."""
    NONE        = "none"
    ON_FAILURE  = "on_failure"
    ALWAYS      = "always"
    PER_STAGE   = "per_stage"


class RetryBackoff(str, Enum):
    """Backoff strategy between stage retries."""
    NONE        = "none"
    FIXED       = "fixed"
    LINEAR      = "linear"
    EXPONENTIAL = "exponential"


class FailurePolicy(str, Enum):
    """What to do when a stage fails."""
    FAIL_FAST   = "fail_fast"   # abort pipeline immediately
    CONTINUE    = "continue"    # skip stage, continue pipeline
    QUARANTINE  = "quarantine"  # quarantine obs, abort pipeline
    ROLLBACK    = "rollback"    # undo previous stages (best-effort)
    DEAD_LETTER = "dead_letter" # send to dead-letter queue


class SchedulerType(str, Enum):
    """Type of pipeline scheduler."""
    BATCH    = "batch"
    PRIORITY = "priority"
    STREAM   = "stream"
    ROUND_ROBIN = "round_robin"


# ── Standard stage names (17 stages) ──────────────────────────────────────────

STAGE_COLLECT             : Final[str] = "collect"
STAGE_DEDUPLICATE         : Final[str] = "deduplicate"
STAGE_NORMALIZE           : Final[str] = "normalize"
STAGE_VALIDATE            : Final[str] = "validate"
STAGE_QUALITY             : Final[str] = "quality_assess"
STAGE_CLASSIFY            : Final[str] = "classify"
STAGE_ONTOLOGY_MAP        : Final[str] = "ontology_map"
STAGE_SEMANTIC_ENRICH     : Final[str] = "semantic_enrich"
STAGE_CONTEXT_ENRICH      : Final[str] = "context_enrich"
STAGE_KNOWLEDGE_TRANSFORM : Final[str] = "knowledge_transform"
STAGE_KNOWLEDGE_LINK      : Final[str] = "knowledge_link"
STAGE_PERSIST             : Final[str] = "persist"
STAGE_CACHE_UPDATE        : Final[str] = "cache_update"
STAGE_PUBLISH_EVENTS      : Final[str] = "publish_events"
STAGE_COLLECT_METRICS     : Final[str] = "collect_metrics"
STAGE_AUDIT_LOG           : Final[str] = "audit_log"
STAGE_COMPLETE            : Final[str] = "complete"

STANDARD_STAGE_ORDER: Final[list[str]] = [
    STAGE_COLLECT, STAGE_DEDUPLICATE, STAGE_NORMALIZE,
    STAGE_VALIDATE, STAGE_QUALITY, STAGE_CLASSIFY,
    STAGE_ONTOLOGY_MAP, STAGE_SEMANTIC_ENRICH, STAGE_CONTEXT_ENRICH,
    STAGE_KNOWLEDGE_TRANSFORM, STAGE_KNOWLEDGE_LINK,
    STAGE_PERSIST, STAGE_CACHE_UPDATE, STAGE_PUBLISH_EVENTS,
    STAGE_COLLECT_METRICS, STAGE_AUDIT_LOG, STAGE_COMPLETE,
]

# ── Built-in pipeline names ───────────────────────────────────────────────────

PIPELINE_STANDARD         : Final[str] = "standard"
PIPELINE_FAST             : Final[str] = "fast"          # skip non-critical stages
PIPELINE_VALIDATION_ONLY  : Final[str] = "validation_only"

# ── Numeric constants ─────────────────────────────────────────────────────────

DEFAULT_STAGE_TIMEOUT_MS  : Final[float] = 5_000.0
MAX_STAGE_TIMEOUT_MS      : Final[float] = 60_000.0
DEFAULT_RETRY_COUNT       : Final[int]   = 2
DEFAULT_RETRY_DELAY_MS    : Final[float] = 100.0
MAX_PIPELINE_HISTORY      : Final[int]   = 1_000
DEFAULT_BATCH_SIZE        : Final[int]   = 50
DEFAULT_BATCH_TIMEOUT_S   : Final[float] = 5.0

PIPELINE_NAMESPACE: Final[str] = "iios.pipeline"
