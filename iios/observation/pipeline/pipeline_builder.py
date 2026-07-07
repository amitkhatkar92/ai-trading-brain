"""
iios/observation/pipeline/pipeline_builder.py
=============================================
Fluent builder API for constructing ``PipelineDefinition`` objects.

Usage::

    pipeline = (
        PipelineBuilder("my_pipeline")
        .description("Custom data pipeline")
        .add_stage("collect", my_collect_handler)
        .add_stage("validate", my_validate_handler, failure_policy=FailurePolicy.FAIL_FAST)
        .add_stage("enrich", my_enrich_handler, mode=StageMode.OPTIONAL)
        .build()
    )
"""
from __future__ import annotations

from typing import Any, Optional

from .pipeline_constants     import (
    DEFAULT_RETRY_DELAY_MS, DEFAULT_STAGE_TIMEOUT_MS,
    FailurePolicy, RetryBackoff, StageMode,
)
from .pipeline_exceptions    import PipelineConfigurationError
from .pipeline_registry      import (
    ConditionFn, PipelineDefinition, StageDefinition, StageHandler,
)

__all__ = ["PipelineBuilder"]


class PipelineBuilder:
    """Fluent builder for ``PipelineDefinition`` objects."""

    def __init__(self, name: str) -> None:
        if not name:
            raise PipelineConfigurationError("Pipeline name cannot be empty")
        self._name:        str                   = name
        self._description: str                   = ""
        self._version:     str                   = "1.0"
        self._tags:        list[str]             = []
        self._stages:      list[StageDefinition] = []

    def description(self, text: str) -> "PipelineBuilder":
        self._description = text
        return self

    def version(self, v: str) -> "PipelineBuilder":
        self._version = v
        return self

    def tag(self, *tags: str) -> "PipelineBuilder":
        self._tags.extend(tags)
        return self

    def add_stage(
        self,
        name:           str,
        handler:        StageHandler,
        *,
        mode:           StageMode    = StageMode.SEQUENTIAL,
        failure_policy: FailurePolicy = FailurePolicy.FAIL_FAST,
        timeout_ms:     float        = DEFAULT_STAGE_TIMEOUT_MS,
        retry_count:    int          = 0,
        retry_delay_ms: float        = DEFAULT_RETRY_DELAY_MS,
        retry_backoff:  RetryBackoff = RetryBackoff.FIXED,
        condition:      Optional[ConditionFn] = None,
        description:    str          = "",
        tags:           Optional[list[str]] = None,
    ) -> "PipelineBuilder":
        """Append a stage to the pipeline definition."""
        self._stages.append(StageDefinition(
            name           = name,
            handler        = handler,
            mode           = mode,
            failure_policy = failure_policy,
            timeout_ms     = timeout_ms,
            retry_count    = retry_count,
            retry_delay_ms = retry_delay_ms,
            retry_backoff  = retry_backoff,
            condition      = condition,
            description    = description,
            tags           = list(tags or []),
        ))
        return self

    def add_optional_stage(
        self,
        name:    str,
        handler: StageHandler,
        **kwargs: Any,
    ) -> "PipelineBuilder":
        """Convenience: add a stage that continues the pipeline on failure."""
        return self.add_stage(
            name,
            handler,
            mode           = kwargs.pop("mode", StageMode.OPTIONAL),
            failure_policy = kwargs.pop("failure_policy", FailurePolicy.CONTINUE),
            **kwargs,
        )

    def add_conditional_stage(
        self,
        name:      str,
        handler:   StageHandler,
        condition: ConditionFn,
        **kwargs:  Any,
    ) -> "PipelineBuilder":
        """Convenience: add a stage that only runs when condition returns True."""
        return self.add_stage(
            name,
            handler,
            mode           = kwargs.pop("mode", StageMode.CONDITIONAL),
            condition      = condition,
            failure_policy = kwargs.pop("failure_policy", FailurePolicy.CONTINUE),
            **kwargs,
        )

    def build(self) -> PipelineDefinition:
        """Finalise and return the ``PipelineDefinition``."""
        if not self._stages:
            raise PipelineConfigurationError(
                f"Pipeline {self._name!r} must have at least one stage"
            )
        return PipelineDefinition(
            name        = self._name,
            stages      = list(self._stages),
            description = self._description,
            version     = self._version,
            tags        = list(self._tags),
        )
