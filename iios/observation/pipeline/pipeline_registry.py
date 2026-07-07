"""
iios/observation/pipeline/pipeline_registry.py
==============================================
Registry for pipeline definitions.

A ``PipelineDefinition`` is an ordered list of ``StageDefinition`` objects.
The registry maps pipeline names → definitions and is thread-safe.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..models.observation    import Observation
from .pipeline_constants     import (
    DEFAULT_RETRY_COUNT, DEFAULT_RETRY_DELAY_MS, DEFAULT_STAGE_TIMEOUT_MS,
    FailurePolicy, RetryBackoff, StageMode,
)
from .pipeline_context       import PipelineContext, StageResult
from .pipeline_exceptions    import (
    PipelineAlreadyExistsError, PipelineConfigurationError, PipelineNotFoundError,
)

__all__ = [
    "StageHandler",
    "ConditionFn",
    "StageDefinition",
    "PipelineDefinition",
    "PipelineRegistry",
    "get_pipeline_registry",
    "reset_pipeline_registry",
]

_LOG  = logging.getLogger("iios.observation.pipeline.registry")
_lock = threading.Lock()
_registry: Optional["PipelineRegistry"] = None

# Type alias for stage handler callables
StageHandler = Callable[[Observation, PipelineContext], StageResult]
ConditionFn  = Callable[[Observation, PipelineContext], bool]


@dataclass
class StageDefinition:
    """Description and configuration of one pipeline stage."""
    name:           str
    handler:        StageHandler
    mode:           StageMode       = StageMode.SEQUENTIAL
    failure_policy: FailurePolicy   = FailurePolicy.FAIL_FAST
    timeout_ms:     float           = DEFAULT_STAGE_TIMEOUT_MS
    retry_count:    int             = 0
    retry_delay_ms: float           = DEFAULT_RETRY_DELAY_MS
    retry_backoff:  RetryBackoff    = RetryBackoff.FIXED
    condition:      Optional[ConditionFn] = None   # for CONDITIONAL mode
    description:    str             = ""
    tags:           list[str]       = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            raise PipelineConfigurationError("Stage name cannot be empty")
        if self.timeout_ms <= 0:
            raise PipelineConfigurationError(f"Stage {self.name!r}: timeout_ms must be > 0")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":           self.name,
            "mode":           self.mode.value,
            "failure_policy": self.failure_policy.value,
            "timeout_ms":     self.timeout_ms,
            "retry_count":    self.retry_count,
            "description":    self.description,
        }


@dataclass
class PipelineDefinition:
    """A named, ordered sequence of stages."""
    name:        str
    stages:      list[StageDefinition]
    description: str              = ""
    version:     str              = "1.0"
    tags:        list[str]        = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            raise PipelineConfigurationError("Pipeline name cannot be empty")
        if not self.stages:
            raise PipelineConfigurationError(f"Pipeline {self.name!r} has no stages")
        # Enforce unique stage names within a pipeline
        names = [s.name for s in self.stages]
        if len(names) != len(set(names)):
            dupes = {n for n in names if names.count(n) > 1}
            raise PipelineConfigurationError(
                f"Pipeline {self.name!r} has duplicate stage names: {dupes}"
            )

    def stage(self, name: str) -> Optional[StageDefinition]:
        for s in self.stages:
            if s.name == name:
                return s
        return None

    def stage_names(self) -> list[str]:
        return [s.name for s in self.stages]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":        self.name,
            "version":     self.version,
            "description": self.description,
            "stages":      [s.to_dict() for s in self.stages],
        }


class PipelineRegistry:
    """Thread-safe registry of pipeline definitions."""

    def __init__(self) -> None:
        self._pipelines: dict[str, PipelineDefinition] = {}
        self._lock       = threading.RLock()

    def register(self, pipeline: PipelineDefinition, overwrite: bool = False) -> None:
        with self._lock:
            if pipeline.name in self._pipelines and not overwrite:
                raise PipelineAlreadyExistsError(pipeline.name)
            self._pipelines[pipeline.name] = pipeline
            _LOG.debug("Registered pipeline %r (%d stages)", pipeline.name, len(pipeline.stages))

    def unregister(self, name: str) -> None:
        with self._lock:
            if name not in self._pipelines:
                raise PipelineNotFoundError(name)
            del self._pipelines[name]

    def get(self, name: str) -> PipelineDefinition:
        with self._lock:
            if name not in self._pipelines:
                raise PipelineNotFoundError(name)
            return self._pipelines[name]

    def get_or_none(self, name: str) -> Optional[PipelineDefinition]:
        with self._lock:
            return self._pipelines.get(name)

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._pipelines

    def all(self) -> list[PipelineDefinition]:
        with self._lock:
            return list(self._pipelines.values())

    def names(self) -> list[str]:
        with self._lock:
            return sorted(self._pipelines.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._pipelines)

    def clear(self) -> None:
        with self._lock:
            self._pipelines.clear()

    def __len__(self) -> int:
        return self.count()

    def __contains__(self, name: str) -> bool:
        return self.has(name)


def get_pipeline_registry() -> PipelineRegistry:
    global _registry
    if _registry is None:
        with _lock:
            if _registry is None:
                from .pipeline_engine import _register_builtin_pipelines
                _registry = PipelineRegistry()
                _register_builtin_pipelines(_registry)
    return _registry


def reset_pipeline_registry() -> None:
    global _registry
    with _lock:
        _registry = None
