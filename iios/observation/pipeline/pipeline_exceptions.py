"""
iios/observation/pipeline/pipeline_exceptions.py
================================================
Exception hierarchy for the Pipeline Engine.
"""
from __future__ import annotations

from ..observation_exceptions import ObservationError

__all__ = [
    "PipelineError",
    "StageError",
    "PipelineNotFoundError",
    "PipelineAlreadyExistsError",
    "StageExecutionError",
    "StageTimeoutError",
    "PipelineConfigurationError",
    "CheckpointError",
    "PipelineTimeoutError",
    "PipelineAbortedError",
    "PipelineNotInitializedError",
    "DeadLetterError",
    "SchedulerError",
]


class PipelineError(ObservationError):
    """Base for all pipeline engine errors."""
    def __init__(self, message: str, code: str = "PIP-000") -> None:
        super().__init__(message, code=code)


class StageError(PipelineError):
    """A pipeline stage encountered an error."""
    def __init__(self, message: str, stage: str = "", code: str = "PIP-010") -> None:
        super().__init__(message, code=code)
        self.stage = stage


class PipelineNotFoundError(PipelineError):
    """Named pipeline not found in registry."""
    def __init__(self, name: str, code: str = "PIP-020") -> None:
        super().__init__(f"Pipeline {name!r} not found", code=code)
        self.name = name


class PipelineAlreadyExistsError(PipelineError):
    """Pipeline with this name already registered."""
    def __init__(self, name: str, code: str = "PIP-030") -> None:
        super().__init__(f"Pipeline {name!r} already registered", code=code)
        self.name = name


class StageExecutionError(StageError):
    """Stage execution failed (non-timeout)."""
    def __init__(self, message: str, stage: str = "", code: str = "PIP-040") -> None:
        super().__init__(message, stage=stage, code=code)


class StageTimeoutError(StageError):
    """Stage exceeded its time budget."""
    def __init__(self, stage: str, timeout_ms: float = 0.0, code: str = "PIP-050") -> None:
        super().__init__(
            f"Stage {stage!r} timed out after {timeout_ms:.0f}ms",
            stage=stage, code=code,
        )
        self.timeout_ms = timeout_ms


class PipelineConfigurationError(PipelineError):
    """Pipeline definition is invalid or misconfigured."""
    def __init__(self, message: str, code: str = "PIP-060") -> None:
        super().__init__(message, code=code)


class CheckpointError(PipelineError):
    """Failed to write or restore a pipeline checkpoint."""
    def __init__(self, message: str, code: str = "PIP-070") -> None:
        super().__init__(message, code=code)


class PipelineTimeoutError(PipelineError):
    """Entire pipeline exceeded its total time budget."""
    def __init__(self, pipeline: str, timeout_ms: float = 0.0, code: str = "PIP-080") -> None:
        super().__init__(
            f"Pipeline {pipeline!r} timed out after {timeout_ms:.0f}ms",
            code=code,
        )
        self.timeout_ms = timeout_ms


class PipelineAbortedError(PipelineError):
    """Pipeline was externally aborted."""
    def __init__(self, pipeline: str, reason: str = "", code: str = "PIP-090") -> None:
        super().__init__(f"Pipeline {pipeline!r} aborted: {reason}", code=code)
        self.reason = reason


class PipelineNotInitializedError(PipelineError):
    """Pipeline engine used before initialisation."""
    def __init__(self, code: str = "PIP-100") -> None:
        super().__init__("Pipeline engine not initialised", code=code)


class DeadLetterError(PipelineError):
    """Observation sent to dead-letter queue after exhausting retries."""
    def __init__(self, obs_id: str, stage: str = "", code: str = "PIP-110") -> None:
        super().__init__(
            f"Observation {obs_id!r} sent to dead-letter from stage {stage!r}",
            code=code,
        )
        self.obs_id = obs_id
        self.stage  = stage


class SchedulerError(PipelineError):
    """Pipeline scheduler encountered an error."""
    def __init__(self, message: str, code: str = "PIP-120") -> None:
        super().__init__(message, code=code)
