"""
iios.ai.foundation.runtime
===========================
A1 AI Foundation -- Execution Runtime.

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

from .execution_context  import ExecutionContext, RuntimeStageRecord
from .execution_pipeline import (
    ExecutionPipeline, RuntimePipelineStage,
    RequestStage, ValidationStage, PolicyEvaluationStage,
    ProviderResolutionStage, ExecutionStage,
    ResponseValidationStage, MetricsStage, ResponseStage,
)
from .execution_runtime  import ExecutionRuntime, ExecutionCoordinator

__all__ = [
    "ExecutionContext", "RuntimeStageRecord",
    "ExecutionPipeline", "RuntimePipelineStage",
    "RequestStage", "ValidationStage", "PolicyEvaluationStage",
    "ProviderResolutionStage", "ExecutionStage",
    "ResponseValidationStage", "MetricsStage", "ResponseStage",
    "ExecutionRuntime", "ExecutionCoordinator",
]
