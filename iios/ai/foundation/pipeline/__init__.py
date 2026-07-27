"""
iios.ai.foundation.pipeline
============================
A1 AI Foundation -- Execution Pipeline.

    from iios.ai.foundation.pipeline import ExecutionPipeline

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

from .pipeline_stage    import PipelineStage
from .pipeline_context  import PipelineContext, StageRecord
from .execution_pipeline import ExecutionPipeline
from .stages             import (
    ValidationStage,
    PolicyEvaluationStage,
    ProviderSelectionStage,
    ExecutionStage,
    ResultValidationStage,
    ResponseStage,
)

__all__ = [
    "PipelineStage",
    "PipelineContext",
    "StageRecord",
    "ExecutionPipeline",
    "ValidationStage",
    "PolicyEvaluationStage",
    "ProviderSelectionStage",
    "ExecutionStage",
    "ResultValidationStage",
    "ResponseStage",
]
