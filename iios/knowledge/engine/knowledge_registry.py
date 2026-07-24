"""
knowledge_registry.py — iios.knowledge.engine
-----------------------------------------------
Thread-safe pipeline registry for the Knowledge Engine.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import (
    DEFAULT_MAX_ARCHIVED_PIPELINES,
    DEFAULT_MAX_PIPELINES,
    KnowledgeWorkflowType,
    PipelineStatus,
)
from .exceptions import KnowledgeCapacityError, KnowledgePipelineError
from .knowledge_pipeline import KnowledgePipeline


class KnowledgeEngineRegistry:
    """
    Thread-safe registry of :class:`KnowledgePipeline` objects.

    Active pipelines and archived pipelines are stored in separate buckets.
    """

    def __init__(
        self,
        max_pipelines: int = DEFAULT_MAX_PIPELINES,
        max_archived:  int = DEFAULT_MAX_ARCHIVED_PIPELINES,
    ) -> None:
        self._max_pipelines = max(1, max_pipelines)
        self._max_archived  = max(1, max_archived)
        self._active:   Dict[str, KnowledgePipeline] = {}
        self._archived: Dict[str, KnowledgePipeline] = {}
        self._lock      = threading.Lock()

    def register(self, pipeline: KnowledgePipeline) -> None:
        with self._lock:
            if pipeline.pipeline_id in self._active:
                raise KnowledgePipelineError(
                    f"Pipeline already registered: {pipeline.pipeline_id!r}",
                    pipeline_id=pipeline.pipeline_id,
                )
            if len(self._active) >= self._max_pipelines:
                raise KnowledgeCapacityError(
                    f"Active pipeline limit reached: {self._max_pipelines}",
                    limit=self._max_pipelines,
                )
            self._active[pipeline.pipeline_id] = pipeline

    def close(self, pipeline: KnowledgePipeline) -> None:
        """Move a terminal pipeline from active to archive."""
        with self._lock:
            self._active.pop(pipeline.pipeline_id, None)
            if len(self._archived) < self._max_archived:
                self._archived[pipeline.pipeline_id] = pipeline

    def get(self, pipeline_id: str) -> Optional[KnowledgePipeline]:
        with self._lock:
            return self._active.get(pipeline_id) or self._archived.get(pipeline_id)

    def all_active(self) -> List[KnowledgePipeline]:
        with self._lock:
            return list(self._active.values())

    def all_archived(self) -> List[KnowledgePipeline]:
        with self._lock:
            return list(self._archived.values())

    def by_status(self, status: PipelineStatus) -> List[KnowledgePipeline]:
        with self._lock:
            bucket = self._archived if status in (
                PipelineStatus.COMPLETED, PipelineStatus.FAILED, PipelineStatus.CANCELLED
            ) else self._active
            return [p for p in bucket.values() if p.status == status]

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    def archived_count(self) -> int:
        with self._lock:
            return len(self._archived)

    def total_count(self) -> int:
        with self._lock:
            return len(self._active) + len(self._archived)

    def clear(self) -> None:
        with self._lock:
            self._active.clear()
            self._archived.clear()
