"""iios/integration/pipeline/pipeline_engine.py

Stores named pipelines and runs them on demand.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from iios.integration.integration_exceptions import PipelineNotFoundError
from iios.integration.core.data_record import DataRequest
from iios.integration.core.integration_result import IntegrationResult
from iios.integration.pipeline.pipeline_builder import Pipeline, PipelineBuilder
from iios.integration.pipeline.pipeline_context import PipelineContext
from iios.integration.pipeline.pipeline_executor import PipelineExecutor

logger = logging.getLogger(__name__)


class PipelineEngine:
    """
    Registry of named Pipelines and execution coordinator.

    A default pipeline (extract→validate→normalize→cache→publish)
    is built on construction and used if no named pipeline is requested.
    """

    def __init__(self) -> None:
        self._pipelines: dict[str, Pipeline] = {}
        self._executor   = PipelineExecutor()
        self._lock        = threading.RLock()
        self._default     = self._build_default()
        self._run_count   = 0

    # ── Pipeline registry ─────────────────────────────────────────────────────

    def register(self, pipeline: Pipeline) -> None:
        with self._lock:
            self._pipelines[pipeline.pipeline_id] = pipeline
        logger.debug("PipelineEngine: registered '%s'", pipeline.pipeline_id)

    def unregister(self, pipeline_id: str) -> None:
        with self._lock:
            self._pipelines.pop(pipeline_id, None)

    def get(self, pipeline_id: str) -> Pipeline:
        with self._lock:
            p = self._pipelines.get(pipeline_id)
        if p is None:
            raise PipelineNotFoundError(f"Pipeline '{pipeline_id}' not found")
        return p

    def has(self, pipeline_id: str) -> bool:
        with self._lock:
            return pipeline_id in self._pipelines

    def all_pipelines(self) -> list[Pipeline]:
        with self._lock:
            return list(self._pipelines.values())

    # ── Execution ─────────────────────────────────────────────────────────────

    async def run(
        self,
        context: PipelineContext,
        pipeline_id: str | None = None,
    ) -> IntegrationResult:
        pipeline = self._default
        if pipeline_id:
            pipeline = self.get(pipeline_id)
        with self._lock:
            self._run_count += 1
        return await self._executor.execute(pipeline, context)

    async def run_many(
        self,
        contexts: list[PipelineContext],
        pipeline_id: str | None = None,
    ) -> list[IntegrationResult]:
        tasks = [self.run(ctx, pipeline_id) for ctx in contexts]
        return list(await asyncio.gather(*tasks, return_exceptions=False))

    # ── Default pipeline ──────────────────────────────────────────────────────

    @staticmethod
    def _build_default() -> Pipeline:
        return (
            PipelineBuilder("default")
            .extract()
            .validate()
            .normalize()
            .cache()
            .publish()
            .build()
        )

    @property
    def default_pipeline(self) -> Pipeline:
        return self._default

    def set_default(self, pipeline: Pipeline) -> None:
        self._default = pipeline

    # ── Stats ─────────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "registered_pipelines": len(self._pipelines),
                "total_runs":           self._run_count,
                "pipeline_ids":         list(self._pipelines.keys()),
            }
