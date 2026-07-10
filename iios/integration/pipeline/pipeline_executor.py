"""iios/integration/pipeline/pipeline_executor.py

Runs a Pipeline against a PipelineContext.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from iios.integration.integration_constants import PipelineStageStatus, PipelineStatus
from iios.integration.integration_exceptions import PipelineExecutionError
from iios.integration.core.integration_result import IntegrationResult
from iios.integration.pipeline.pipeline_builder import Pipeline
from iios.integration.pipeline.pipeline_context import PipelineContext
from iios.integration.pipeline.pipeline_stage import PipelineStageResult

logger = logging.getLogger(__name__)


class PipelineExecutor:
    """
    Runs a Pipeline stage-by-stage, collecting results and handling failures.

    Strategy: if a required stage (EXTRACT, VALIDATE) fails → abort.
    Optional stages (ENRICH, PUBLISH) failures are logged as warnings.
    """

    ABORT_ON_FAILURE: set[str] = {
        "extract",
        "validate",
        "normalize",
    }

    async def execute(
        self, pipeline: Pipeline, context: PipelineContext
    ) -> IntegrationResult:
        result = IntegrationResult(
            pipeline_id=context.pipeline_id,
            request_id=context.request.request_id,
            provider_id=context.request.provider_id,
            status=PipelineStatus.RUNNING,
            started_at=time.time(),
        )
        result.records_in = len(context.records)
        stage_results: list[PipelineStageResult] = []

        for stage in pipeline.stages:
            try:
                sr = await stage.process(context)
                stage_results.append(sr)
                logger.debug(
                    "Pipeline '%s' stage '%s': %d→%d records (%.1fms)",
                    pipeline.pipeline_id,
                    stage.name,
                    sr.records_in,
                    sr.records_out,
                    sr.latency_ms,
                )
                if sr.status == PipelineStageStatus.FAILED:
                    if stage.stage_type.value in self.ABORT_ON_FAILURE:
                        result.status   = PipelineStatus.FAILED
                        result.error    = f"Stage '{stage.name}' failed: {sr.errors}"
                        result.completed_at = time.time()
                        result.stage_results = [s.to_dict() for s in stage_results]
                        return result
                    else:
                        logger.warning(
                            "Pipeline '%s' optional stage '%s' failed (continuing): %s",
                            pipeline.pipeline_id, stage.name, sr.errors,
                        )
            except Exception as exc:
                sr = PipelineStageResult(
                    stage_type=stage.stage_type,
                    status=PipelineStageStatus.FAILED,
                    errors=[str(exc)],
                )
                stage_results.append(sr)
                if stage.stage_type.value in self.ABORT_ON_FAILURE:
                    result.status      = PipelineStatus.FAILED
                    result.error       = f"Stage '{stage.name}' raised: {exc}"
                    result.completed_at = time.time()
                    result.stage_results = [s.to_dict() for s in stage_results]
                    return result

        result.status       = PipelineStatus.COMPLETED
        result.records      = list(context.records)
        result.records_out  = len(context.records)
        result.records_dropped = max(0, result.records_in - result.records_out)
        result.completed_at = time.time()
        result.stage_results = [s.to_dict() for s in stage_results]
        return result
