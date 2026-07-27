"""
execution_pipeline.py -- iios.ai.foundation.pipeline
======================================================
:class:`ExecutionPipeline` -- orchestrates the 6 standard pipeline stages.

The pipeline is the sole code path through which AI requests become
provider calls.  It is stateless between runs; a new :class:`PipelineContext`
is created for every request.

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .pipeline_stage    import PipelineStage
from .pipeline_context  import PipelineContext
from .stages            import (
    ValidationStage,
    PolicyEvaluationStage,
    ProviderSelectionStage,
    ExecutionStage,
    ResultValidationStage,
    ResponseStage,
)
from ..request.request_models import AIExecutionRequest, AIExecutionResult, AIResponse
from ..exceptions             import AIPipelineError

_log = get_logger(__name__)


class ExecutionPipeline:
    """
    Stateless 6-stage AI execution pipeline.

    Stages (in order)::

        ValidationStage
        PolicyEvaluationStage
        ProviderSelectionStage
        ExecutionStage
        ResultValidationStage
        ResponseStage

    Additional stages can be inserted via :meth:`add_stage`.

    Parameters
    ----------
    provider_registry : Optional :class:`AIProviderRegistry` for automatic
                        provider routing in Stage 3.

    Usage::

        pipeline = ExecutionPipeline(provider_registry=registry)
        result   = pipeline.run(execution_request)
    """

    def __init__(self, provider_registry: Optional[Any] = None) -> None:
        self._provider_registry = provider_registry
        self._stages: List[PipelineStage] = self._build_default_stages()

    # ── Pipeline execution ────────────────────────────────────────────────────

    def run(self, execution_request: AIExecutionRequest) -> AIExecutionResult:
        """
        Execute the full pipeline for ``execution_request``.

        Returns
        -------
        AIExecutionResult
            Always returns a result -- errors are captured in the response.
        """
        ctx = PipelineContext(
            execution_request = execution_request,
            pipeline_id       = str(uuid.uuid4()),
        )

        # Inject shared resources into context data
        if self._provider_registry:
            ctx.set("provider_registry", self._provider_registry)

        _log.debug(
            f"ExecutionPipeline: start "
            f"pipeline_id={ctx.pipeline_id!r} "
            f"request_id={ctx.request_id!r}"
        )

        for stage in self._stages:
            stage.execute(ctx)
            if ctx.is_aborted:
                _log.warning(
                    f"ExecutionPipeline: aborted at stage='{stage.name}' "
                    f"reason={ctx.abort_reason!r}"
                )
                break

        result = self._finalise(ctx)
        _log.debug(
            f"ExecutionPipeline: done "
            f"pipeline_id={ctx.pipeline_id!r} "
            f"succeeded={result.succeeded} "
            f"latency={result.total_latency_ms:.1f}ms"
        )
        return result

    # ── Stage management ──────────────────────────────────────────────────────

    def add_stage(self, stage: PipelineStage, *, index: Optional[int] = None) -> None:
        """
        Add a custom stage to the pipeline.

        Parameters
        ----------
        stage : Stage to add.
        index : Insertion position (appended if ``None``).
        """
        if index is None:
            self._stages.append(stage)
        else:
            self._stages.insert(index, stage)

    def stage_names(self) -> List[str]:
        return [s.name for s in self._stages]

    # ── Internals ──────────────────────────────────────────────────────────────

    def _build_default_stages(self) -> List[PipelineStage]:
        return [
            ValidationStage(),
            PolicyEvaluationStage(),
            ProviderSelectionStage(),
            ExecutionStage(),
            ResultValidationStage(),
            ResponseStage(),
        ]

    def _finalise(self, ctx: PipelineContext) -> AIExecutionResult:
        """Build :class:`AIExecutionResult` from the completed context."""
        if ctx.response is not None:
            response = ctx.response
        else:
            # Pipeline aborted before ResponseStage
            response = AIResponse.failure(
                request_id  = ctx.request_id,
                session_id  = ctx.session_id,
                error       = ctx.abort_reason or "Pipeline aborted without response.",
                latency_ms  = ctx.elapsed_ms,
                provider_id = ctx.provider_id,
                model_id    = ctx.model_id,
            )

        return AIExecutionResult(
            response          = response,
            pipeline_id       = ctx.pipeline_id,
            stages_completed  = len(ctx.stage_records),
            stages_total      = len(self._stages),
            policy_decisions  = tuple(ctx.policy_decisions),
            provider_selected = ctx.provider_id,
            total_latency_ms  = ctx.elapsed_ms,
        )
