"""iios/observation/pipeline/__init__.py"""
from __future__ import annotations

# ── Baseline (keep — imported by observation_engine.py) ───────────────────────
from .observation_pipeline import (
    PipelineResult,
    ObservationPipeline,
    get_observation_pipeline,
    reset_observation_pipeline,
)

# ── Pipeline Engine ────────────────────────────────────────────────────────────
from .pipeline_constants import (
    CheckpointPolicy, ExecutionMode, FailurePolicy, PipelineState,
    RetryBackoff, SchedulerType, StageMode, StagePriority,
    PIPELINE_FAST, PIPELINE_STANDARD, PIPELINE_VALIDATION_ONLY,
    STAGE_COLLECT, STAGE_VALIDATE, STAGE_CLASSIFY, STAGE_SEMANTIC_ENRICH,
    STAGE_COMPLETE, STAGE_PERSIST, STAGE_PUBLISH_EVENTS,
)
from .pipeline_exceptions import (
    PipelineError, StageError, PipelineNotFoundError,
    PipelineAlreadyExistsError, StageExecutionError, StageTimeoutError,
    PipelineConfigurationError, CheckpointError, PipelineTimeoutError,
    PipelineAbortedError, PipelineNotInitializedError, DeadLetterError,
    SchedulerError,
)
from .pipeline_context import (
    Checkpoint, StageResult, PipelineContext,
    get_pipeline_context, reset_pipeline_context, pipeline_execution,
)
from .pipeline_registry import (
    StageHandler, ConditionFn, StageDefinition, PipelineDefinition,
    PipelineRegistry, get_pipeline_registry, reset_pipeline_registry,
)
from .pipeline_builder import PipelineBuilder
from .pipeline_executor import PipelineExecutionResult, PipelineExecutor
from .pipeline_metrics import (
    MetricsSnapshot, PipelineMetrics,
    get_pipeline_metrics, reset_pipeline_metrics,
)
from .pipeline_monitor import (
    StageHealthReport, PipelineHealthReport, PipelineMonitor,
    get_pipeline_monitor, reset_pipeline_monitor,
)
from .pipeline_engine import (
    PipelineEngine, get_pipeline_engine, reset_pipeline_engine,
)
from .pipeline_manager import (
    DeadLetterEntry, PipelineManager,
    get_pipeline_manager, reset_pipeline_manager,
)
from .pipeline_scheduler import (
    ScheduledItem, BatchScheduler, PriorityScheduler,
    PipelineScheduler, get_pipeline_scheduler, reset_pipeline_scheduler,
)

__all__ = [
    # Baseline
    "PipelineResult", "ObservationPipeline",
    "get_observation_pipeline", "reset_observation_pipeline",
    # Constants
    "CheckpointPolicy", "ExecutionMode", "FailurePolicy", "PipelineState",
    "RetryBackoff", "SchedulerType", "StageMode", "StagePriority",
    "PIPELINE_FAST", "PIPELINE_STANDARD", "PIPELINE_VALIDATION_ONLY",
    "STAGE_COLLECT", "STAGE_VALIDATE", "STAGE_CLASSIFY",
    "STAGE_SEMANTIC_ENRICH", "STAGE_COMPLETE", "STAGE_PERSIST",
    "STAGE_PUBLISH_EVENTS",
    # Exceptions
    "PipelineError", "StageError", "PipelineNotFoundError",
    "PipelineAlreadyExistsError", "StageExecutionError", "StageTimeoutError",
    "PipelineConfigurationError", "CheckpointError", "PipelineTimeoutError",
    "PipelineAbortedError", "PipelineNotInitializedError", "DeadLetterError",
    "SchedulerError",
    # Context
    "Checkpoint", "StageResult", "PipelineContext",
    "get_pipeline_context", "reset_pipeline_context", "pipeline_execution",
    # Registry
    "StageHandler", "ConditionFn", "StageDefinition", "PipelineDefinition",
    "PipelineRegistry", "get_pipeline_registry", "reset_pipeline_registry",
    # Builder
    "PipelineBuilder",
    # Executor
    "PipelineExecutionResult", "PipelineExecutor",
    # Metrics
    "MetricsSnapshot", "PipelineMetrics",
    "get_pipeline_metrics", "reset_pipeline_metrics",
    # Monitor
    "StageHealthReport", "PipelineHealthReport", "PipelineMonitor",
    "get_pipeline_monitor", "reset_pipeline_monitor",
    # Engine
    "PipelineEngine", "get_pipeline_engine", "reset_pipeline_engine",
    # Manager
    "DeadLetterEntry", "PipelineManager",
    "get_pipeline_manager", "reset_pipeline_manager",
    # Scheduler
    "ScheduledItem", "BatchScheduler", "PriorityScheduler",
    "PipelineScheduler", "get_pipeline_scheduler", "reset_pipeline_scheduler",
]

